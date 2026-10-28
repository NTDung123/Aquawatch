"""Diagnostic inference on approved validation images and exploratory library frames.

This script never reads test images, trains a model, selects a confidence threshold,
changes deployment settings, or interprets a person detection as drowning.
"""
import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".work"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".work" / "matplotlib"))
os.environ.setdefault("YOLO_AUTOINSTALL", "false")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = lambda v: max(0, v[2] - v[0]) * max(0, v[3] - v[1])
    return intersection / max(1e-9, area(a) + area(b) - intersection)


def nms(predictions, threshold=.7):
    retained = []
    for prediction in sorted(predictions, key=lambda p: p["confidence"], reverse=True):
        if all(iou(prediction["box"], other["box"]) <= threshold for other in retained):
            retained.append(prediction)
    return retained


def metric(items, threshold, class_id=None, size_bin=None):
    tp = fp = fn = wrong_class = 0
    bins = {"small": (0, 32), "medium": (32, 96), "large": (96, float("inf"))}
    for item in items:
        truth = [t for t in item["truth"] if class_id is None or t["class_id"] == class_id]
        if size_bin:
            low, high = bins[size_bin]
            truth = [t for t in truth if low <= math.sqrt((t["box"][2] - t["box"][0]) * (t["box"][3] - t["box"][1])) * 640 < high]
        used = set()
        for p in sorted(item["predictions"], key=lambda p: p["confidence"], reverse=True):
            if p["confidence"] < threshold or (class_id is not None and p["class_id"] != class_id):
                continue
            options = [(iou(p["box"], t["box"]), j) for j, t in enumerate(truth) if j not in used]
            if options and max(options)[0] >= .5:
                j = max(options)[1]
                used.add(j)
                tp += 1
                wrong_class += p["class_id"] != truth[j]["class_id"]
            elif not size_bin:
                fp += 1
        fn += len(truth) - len(used)
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    return {"tp": tp, "fp": fp if not size_bin else None, "fn": fn,
            "precision": precision if not size_bin else None, "recall": recall,
            "wrong_class_among_spatial_matches": wrong_class if class_id is None else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/curated/surface_v3")
    parser.add_argument("--model", type=Path, default=ROOT / "data/training/surface_v3_coco60/weights/best.pt")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--video-step", type=float, default=2)
    parser.add_argument("--skip-videos", action="store_true")
    parser.add_argument("--stretch-only", action="store_true", help="Isolate anisotropic 640x640 resize; validation remains the same 137 images")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a new probe_ output directory to preserve evidence")
    if not output.name.startswith("probe_") or output.parent != (ROOT / "data/evaluation").resolve():
        parser.error("Output must be data/evaluation/probe_*")
    dataset = args.dataset.resolve()
    audit = json.loads((dataset / "audit.json").read_text(encoding="utf-8"))
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    if not audit.get("build_completed") or audit.get("errors"):
        parser.error("Dataset audit must be complete and free of errors")
    entries = [e for e in manifest if e["split"] == "val"]
    if len(entries) != 137:
        parser.error("This bounded probe expects the same 137-image approved validation split")
    for entry in entries:
        if entry.get("review_status") != "approved" or entry.get("viewpoint") != "above_water":
            parser.error("Only approved above-water validation entries are allowed")
        image = (dataset / entry["curated_image"]).resolve()
        label = dataset / "labels/val" / image.with_suffix(".txt").name
        if not image.is_relative_to(dataset / "images/val") or not label.resolve().is_relative_to(dataset / "labels/val"):
            parser.error("Unexpected validation path")
        if sha256(image) != entry["image_sha256"] or sha256(label) != entry["label_sha256"]:
            parser.error("Validation bytes changed after review")
    import cv2
    import numpy as np
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(2)
    model = YOLO(str(args.model))
    if model.names != {0: "drowning", 1: "swimming"}:
        parser.error("Expected canonical 2-class detector")
    output.mkdir(parents=True)
    report = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
              "model": str(args.model.resolve()), "model_sha256": sha256(args.model),
              "dataset": str(dataset), "manifest_sha256": sha256(dataset / "manifest.json"),
              "validation_images": len(entries), "validation_groups": sorted(set(e["source_group"] for e in entries)),
              "fixed_primary_threshold": .4, "diagnostic_thresholds": [.05, .15, .4],
              "nms_iou": .7, "matching_iou": .5, "device": args.device,
              "modes": ["stretch640"] if args.stretch_only else ["full640", "full960", "tile640", "full_tile640"],
              "stretch_geometry": "cv2.resize original frame to 640x640; predicted coordinates normalized in square map back independently to original x/y; no threshold chosen using videos",
              "tile_geometry": "2x2, each tile 60% of original width and height, 33.3% overlap of adjacent tile width; map boxes back before class-agnostic NMS",
              "limitations": ["No test image bytes or locked-test results read.", "No confidence selection or deployment promotion.",
                              "Validation labels are weak visual source labels; these metrics are not clinical accuracy.",
                              "Library frames are exploratory diagnostics; no per-frame event ground truth is claimed.",
                              "Size bins use square-root box area mapped to a canonical 640x640 image, not true sensor resolution.",
                              "Timing includes input preprocessing, model inference, CPU box copies, and merged NMS, excluding image/video decoding."]}

    def save():
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def predict(frame, imgsz, offset=(0, 0), full_shape=None):
        h, w = full_shape or frame.shape[:2]
        x0, y0 = offset
        result = model.predict(frame, conf=.05, imgsz=imgsz, device=args.device,
                               agnostic_nms=True, iou=.7, max_det=300, verbose=False)[0]
        found = []
        for box in result.boxes:
            xyxy = box.xyxy[0].cpu().tolist()
            coordinates = [max(0., min(1., (v + (x0 if j % 2 == 0 else y0)) / (w if j % 2 == 0 else h))) for j, v in enumerate(xyxy)]
            area = (coordinates[2] - coordinates[0]) * (coordinates[3] - coordinates[1])
            if .00002 <= area <= .85:
                found.append({"box": coordinates, "class_id": int(box.cls.item()), "confidence": float(box.conf.item())})
        return found

    def sync():
        if args.device != "cpu" and torch.cuda.is_available():
            torch.cuda.synchronize()

    def infer_modes(frame):
        h, w = frame.shape[:2]
        result, times = {}, {}
        if args.stretch_only:
            sync(); begin = time.perf_counter()
            result["stretch640"] = predict(cv2.resize(frame, (640, 640)), 640)
            sync(); times["stretch640"] = (time.perf_counter() - begin) * 1000
            return result, times
        for mode, imgsz in (("full640", 640), ("full960", 960)):
            sync(); begin = time.perf_counter()
            result[mode] = predict(frame, imgsz)
            sync(); times[mode] = (time.perf_counter() - begin) * 1000
        sync(); begin = time.perf_counter()
        tw, th = math.ceil(w * .6), math.ceil(h * .6)
        tiled = []
        for y in (0, h - th):
            for x in (0, w - tw):
                tiled.extend(predict(frame[y:y + th, x:x + tw], 640, (x, y), (h, w)))
        result["tile640"] = nms(tiled)
        sync(); times["tile640"] = (time.perf_counter() - begin) * 1000
        begin = time.perf_counter()
        result["full_tile640"] = nms(result["full640"] + result["tile640"])
        times["full_tile640"] = times["full640"] + times["tile640"] + (time.perf_counter() - begin) * 1000
        return result, times

    def write_overlay(frame, predictions, destination):
        tiles = []
        for mode in report["modes"]:
            view = frame.copy()
            h, w = view.shape[:2]
            for prediction in predictions[mode]:
                if prediction["confidence"] < .4:
                    continue
                x1, y1, x2, y2 = [int(v * (w if j % 2 == 0 else h)) for j, v in enumerate(prediction["box"])]
                color = (0, 0, 255) if prediction["class_id"] == 0 else (0, 210, 0)
                cv2.rectangle(view, (x1, y1), (x2, y2), color, 2)
                cv2.putText(view, f"{model.names[prediction['class_id']]} {prediction['confidence']:.2f}", (x1, max(15, y1)), cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1)
            view = cv2.resize(view, (640, 360))
            cv2.rectangle(view, (0, 0), (250, 26), (0, 0, 0), -1)
            cv2.putText(view, mode + " conf=0.40", (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
            tiles.append(view)
        combined = tiles[0] if len(tiles) == 1 else np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
        cv2.imwrite(str(destination), combined)

    save()
    try:
        warmup = np.zeros((640, 640, 3), dtype=np.uint8)
        infer_modes(warmup)
        items = {mode: [] for mode in report["modes"]}
        timing = {mode: [] for mode in report["modes"]}
        began = time.perf_counter()
        for index, entry in enumerate(entries):
            path = dataset / entry["curated_image"]
            label = dataset / "labels/val" / path.with_suffix(".txt").name
            frame = cv2.imread(str(path))
            if frame is None:
                raise ValueError(f"Cannot decode {path}")
            truth = []
            for line in label.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    c, x, y, width, height = map(float, line.split())
                    truth.append({"class_id": int(c), "box": [x - width / 2, y - height / 2, x + width / 2, y + height / 2]})
            predictions, times = infer_modes(frame)
            for mode in items:
                items[mode].append({"image": str(path), "source_group": entry["source_group"], "width": frame.shape[1], "height": frame.shape[0], "truth": truth, "predictions": predictions[mode]})
                timing[mode].append(times[mode])
            if (index + 1) % 25 == 0:
                print(f"Validation {index + 1}/{len(entries)}", flush=True)
        validation = {}
        for mode in items:
            validation[mode] = {"timing_ms": {"mean": float(np.mean(timing[mode])), "p95": float(np.percentile(timing[mode], 95))},
                                "thresholds": {str(t): {"drowning": metric(items[mode], t, 0), "swimming": metric(items[mode], t, 1),
                                                          "class_agnostic_objects": metric(items[mode], t),
                                                          "object_recall_by_size": {s: metric(items[mode], t, size_bin=s) for s in ("small", "medium", "large")}} for t in (.05, .15, .4)},
                                "groups_at_conf_0.4": {g: {"drowning": metric([v for v in items[mode] if v["source_group"] == g], .4, 0), "swimming": metric([v for v in items[mode] if v["source_group"] == g], .4, 1)} for g in report["validation_groups"]}}
        report.update(validation=validation, validation_wall_seconds=time.perf_counter() - began,
                      validation_dimensions=sorted(set((e["width"], e["height"]) for e in entries)),
                      validation_aspect_warning="Square exported validation images cannot measure the distortion mismatch between raw widescreen video and stretch-trained source images.")
        (output / "validation_predictions.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        save()
        print(json.dumps({"validation_at_conf_0.4": {mode: {"timing_ms": v["timing_ms"], "drowning": v["thresholds"]["0.4"]["drowning"], "swimming": v["thresholds"]["0.4"]["swimming"]} for mode, v in validation.items()}}), flush=True)
        video_records = []
        if not args.skip_videos:
            library = json.loads((ROOT / "data/video_library.json").read_text(encoding="utf-8"))
            selected = {"pool_staged_active_18s", "pool_staged_passive_9s", "pool_staged_assist_18s", "pool_normal_lane_35s", "pool_normal_edge_32s", "beach_usbp_rescue_full"}
            for video in library["videos"]:
                if video["id"] not in selected:
                    continue
                if video.get("above_water") is not True:
                    raise ValueError("Unapproved video viewpoint")
                capture = cv2.VideoCapture(video["path"])
                frames = []
                for timestamp in np.arange(0, video["duration"], args.video_step):
                    capture.set(cv2.CAP_PROP_POS_MSEC, float(timestamp) * 1000)
                    ok, frame = capture.read()
                    if not ok:
                        raise ValueError(f"Decode failed for {video['id']} at {timestamp}")
                    predictions, times = infer_modes(frame)
                    frames.append({"time": float(timestamp), "predictions": predictions, "timing_ms": times})
                    if len(frames) <= 3:
                        write_overlay(frame, predictions, output / f"{video['id']}_{timestamp:.1f}s.jpg")
                capture.release()
                summary = {}
                for mode in report["modes"]:
                    summary[mode] = {"mean_ms": float(np.mean([v["timing_ms"][mode] for v in frames])),
                                     "thresholds": {str(t): {"drowning_boxes": sum(p["class_id"] == 0 and p["confidence"] >= t for f in frames for p in f["predictions"][mode]),
                                                               "swimming_boxes": sum(p["class_id"] == 1 and p["confidence"] >= t for f in frames for p in f["predictions"][mode]),
                                                               "frames_with_drowning": sum(any(p["class_id"] == 0 and p["confidence"] >= t for p in f["predictions"][mode]) for f in frames),
                                                               "frames_with_any_detection": sum(any(p["confidence"] >= t for p in f["predictions"][mode]) for f in frames)} for t in (.05, .15, .4)}}
                video_records.append({"id": video["id"], "sha256": video["sha256"], "scenario": video["scenario"], "camera_support": video["camera_support"], "samples": len(frames), "step_seconds": args.video_step, "summary": summary, "frames": frames})
                (output / "video_predictions.json").write_text(json.dumps(video_records, ensure_ascii=False), encoding="utf-8")
                print(f"Video {video['id']}: {len(frames)} exploratory frames", flush=True)
            report["videos"] = [{k: v for k, v in item.items() if k != "frames"} for item in video_records]
        report.update(status="completed", finished_utc=datetime.now(timezone.utc).isoformat())
        save()
        print(f"Probe completed: {output / 'report.json'}", flush=True)
    except Exception as error:
        report.update(status="failed", error=str(error), finished_utc=datetime.now(timezone.utc).isoformat())
        save()
        raise


if __name__ == "__main__":
    main()
