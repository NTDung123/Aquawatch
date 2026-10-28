"""Choose a deployment confidence using ONLY the reviewed validation images."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".work"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".work" / "matplotlib"))


def overlap(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = lambda c: max(0, c[2] - c[0]) * max(0, c[3] - c[1])
    return intersection / max(1e-9, area(a) + area(b) - intersection)


def score(items, threshold, class_id):
    tp = fp = fn = 0
    for item in items:
        truth = [v for v in item["truth"] if v["class_id"] == class_id]
        used = set()
        for prediction in sorted(item["predictions"], key=lambda d: d["confidence"], reverse=True):
            if prediction["class_id"] != class_id or prediction["confidence"] < threshold:
                continue
            options = [(overlap(prediction["box"], target["box"]), index) for index, target in enumerate(truth) if index not in used]
            if options and max(options)[0] >= .5:
                used.add(max(options)[1])
                tp += 1
            else:
                fp += 1
        fn += len(truth) - len(used)
    precision, recall = tp / max(1, tp + fp), tp / max(1, tp + fn)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / max(1e-9, precision + recall),
            "f2": 5 * precision * recall / max(1e-9, 4 * precision + recall)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-recall", type=float, default=.8)
    args = parser.parse_args()
    if not 0 < args.target_recall <= 1:
        parser.error("Target recall must be in (0, 1]")
    if args.output.exists():
        parser.error("Preserve prior calibration; choose a new output file")
    audit = json.loads((args.dataset / "audit.json").read_text(encoding="utf-8"))
    if not audit.get("build_completed") or audit.get("errors"):
        parser.error("Dataset audit must pass first")
    manifest = json.loads((args.dataset / "manifest.json").read_text(encoding="utf-8"))
    import torch
    from ultralytics import YOLO
    model = YOLO(str(args.model))
    if model.names != {0: "drowning", 1: "swimming"}:
        parser.error("Wrong model taxonomy")
    items = []
    for entry in manifest:
        if entry["split"] != "val":
            continue
        path = args.dataset / entry["curated_image"]
        label = args.dataset / "labels" / "val" / path.with_suffix(".txt").name
        for file, key in ((path, "image_sha256"), (label, "label_sha256")):
            if hashlib.sha256(file.read_bytes()).hexdigest() != entry[key]:
                parser.error("Validation bytes changed after audit")
        truth = []
        for line in label.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            class_id, x, y, width, height = map(float, line.split())
            truth.append({"class_id": int(class_id), "box": [x - width / 2, y - height / 2, x + width / 2, y + height / 2]})
        result = model.predict(str(path), conf=.05, imgsz=640, agnostic_nms=True,
                               device="0" if torch.cuda.is_available() else "cpu", verbose=False)[0]
        predictions = []
        for box in result.boxes:
            coordinates = box.xyxyn[0].cpu().tolist()
            area = (coordinates[2] - coordinates[0]) * (coordinates[3] - coordinates[1])
            if .00002 <= area <= .85:
                predictions.append({"class_id": int(box.cls.item()), "confidence": float(box.conf.item()), "box": coordinates})
        items.append({"image": str(path), "truth": truth, "predictions": predictions})
    if not any(t["class_id"] == 0 for item in items for t in item["truth"]):
        parser.error("Validation must contain drowning labels to calibrate a risk threshold")
    curve = [{"confidence": value / 100, "drowning": score(items, value / 100, 0),
              "swimming": score(items, value / 100, 1)} for value in range(15, 81, 5)]
    eligible = [p for p in curve if p["drowning"]["recall"] >= args.target_recall]
    chosen = max(eligible or curve, key=lambda p: (p["drowning"]["f2"], p["drowning"]["recall"], p["confidence"]))
    record = {"model": str(args.model.resolve()), "model_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
              "split": "val", "images": len(items), "matching_iou": .5, "imgsz": 640, "agnostic_nms": True,
              "curve": curve, "selected_confidence": chosen["confidence"], "selected_metrics": chosen,
              "target_recall": args.target_recall,
              "selection_rule": "Among thresholds meeting target validation drowning recall choose best F2, weighting recall more than precision; if none meets target, choose best F2 and disclose the unmet target.",
              "target_recall_met": bool(eligible),
              "limitations": ["Weak source image annotations, not medically verified drowning.",
                              "Confidence calibration does not validate temporal alarms or CCTV safety.",
                              "No test images or library videos were used to choose this confidence."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"confidence": chosen["confidence"], "metrics": chosen, "target_recall_met": bool(eligible)}))


if __name__ == "__main__":
    main()
