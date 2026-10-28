"""Compare two detector checkpoints on the same audited image split."""

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".work" / "ultralytics"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".work" / "matplotlib"))


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--split", choices=["val", "test"], default="val")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    dataset, output = args.dataset.resolve(), args.output.resolve()
    if output.exists():
        parser.error("Output exists; choose a new versioned evaluation directory")
    audit = json.loads((dataset / "audit.json").read_text(encoding="utf-8"))
    configuration = json.loads((dataset / "data.yaml").read_text(encoding="utf-8"))
    if not audit.get("build_completed") or not audit.get("split_counts", {}).get(args.split, 0):
        parser.error("Requested split is absent or has not passed data audit")
    if Path(configuration.get("path", "")).resolve() != dataset or configuration.get("names") != ["drowning", "swimming"]:
        parser.error("Audited dataset must use canonical classes and matching root")
    if configuration.get(args.split) != "images/" + args.split:
        parser.error("Dataset split path differs from the audited layout")
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest:
        if entry["split"] != args.split:
            continue
        image = (dataset / entry["curated_image"]).resolve()
        label = dataset / "labels" / entry["split"] / image.with_suffix(".txt").name
        if not image.is_relative_to(dataset) or not label.resolve().is_relative_to(dataset):
            parser.error("Manifest file escapes the audited dataset")
        if sha256(image) != entry["image_sha256"] or sha256(label) != entry["label_sha256"]:
            parser.error("Evaluation data changed after audit")
    lock = dataset / "test_evaluation_lock.json"
    if args.split == "test" and lock.exists():
        parser.error(f"Locked test split already evaluated. Preserve the result in {lock}; do not tune on this split")
    import torch
    from ultralytics import YOLO
    from runtime_threads import configure_image_cache_threads

    configure_image_cache_threads()

    device = ("0" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    record = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
              "dataset": str(dataset), "audit_sha256": sha256(dataset / "audit.json"),
              "manifest_sha256": sha256(dataset / "manifest.json"), "split": args.split,
              "images": audit["split_counts"][args.split],
              "source_groups": [group for group, split in audit["group_split"].items() if split == args.split],
              "configuration": {"imgsz": args.imgsz, "batch": args.batch, "device": device,
                                "conf": 0.001, "iou": 0.7, "max_det": 300, "half": False},
              "models": {},
              "limitations": ["These are image object-detection metrics against source weak annotations.",
                              "They do not measure event recall, alert delay, or real drowning accuracy.",
                              "This scene split is held out from fine-tuning only; independence from community pretraining is unverified.",
                              "Few scene groups and imbalanced classes limit statistical confidence."]}
    output.mkdir(parents=True)

    def save():
        (output / "comparison.json").write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    save()
    try:
        for role, path in (("baseline", args.baseline.resolve()), ("candidate", args.candidate.resolve())):
            model = YOLO(str(path))
            if model.names != {0: "drowning", 1: "swimming"}:
                raise ValueError(f"{role} class names are not canonical: {model.names}")
            started = time.perf_counter()
            result = model.val(data=str(dataset / "data.yaml"), split=args.split, imgsz=args.imgsz, batch=args.batch,
                               device=device, workers=0, project=str(output), name=role, exist_ok=True,
                               conf=0.001, iou=0.7, max_det=300, half=False, plots=True, verbose=False)
            per_class = []
            for index, class_id in enumerate(result.box.ap_class_index):
                precision, recall, ap50, ap = result.box.class_result(index)
                per_class.append({"class_id": int(class_id), "name": model.names[int(class_id)],
                                  "precision": float(precision), "recall": float(recall),
                                  "mAP50": float(ap50), "mAP50_95": float(ap)})
            record["models"][role] = {"path": str(path), "sha256": sha256(path),
                                      "class_names": model.names, "metrics": result.results_dict,
                                      "per_class": per_class, "speed_ms_per_image": result.speed,
                                      "evaluation_seconds": time.perf_counter() - started}
            save()
        record.update(status="completed", finished_utc=datetime.now(timezone.utc).isoformat())
        save()
        if args.split == "test":
            lock.write_text(json.dumps({"comparison": str(output / "comparison.json"),
                                        "comparison_sha256": sha256(output / "comparison.json"),
                                        "evaluated_utc": record["finished_utc"]}, indent=2), encoding="utf-8")
        print(json.dumps({"status": record["status"], "comparison": str(output / "comparison.json")}))
    except Exception as error:
        record.update(status="failed", error=str(error), finished_utc=datetime.now(timezone.utc).isoformat())
        save()
        raise


if __name__ == "__main__":
    main()
