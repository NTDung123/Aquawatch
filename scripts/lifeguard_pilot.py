#!/usr/bin/env python3
"""Research-only, provenance-honest Lifeguard -> AquaWatch pilot.

DO NOT treat output as a licensed/verified dataset. This program NEVER changes
review_status to approved or fabricates a license. It builds a separate,
explicitly unverified research experiment, without modifying surface_v4 or
AquaWatch's deployed checkpoint.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CLASS_NAMES = ["drowning", "swimming"]


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_path(root, part):
    root = root.resolve()
    path = (root / part).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes dataset root: {part}")
    return path


def load_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_yolo(path):
    boxes = 0
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        p = line.split()
        if len(p) != 5 or p[0] not in ("0", "1"):
            raise ValueError(f"{path}:{line_no}: not a canonical YOLO label")
        values = [float(x) for x in p[1:]]
        x, y, w, h = values
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in values) or min(w, h) <= 0:
            raise ValueError(f"{path}:{line_no}: invalid bbox")
        if x-w/2 < -0.01 or y-h/2 < -0.01 or x+w/2 > 1.01 or y+h/2 > 1.01:
            raise ValueError(f"{path}:{line_no}: bbox exceeds frame")
        boxes += 1
    return boxes


def dhash(path):
    from PIL import Image
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        small = im.convert("L").resize((9, 8))
        pix = list(small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata())
    val = 0
    for y in range(8):
        for x in range(8):
            val = (val << 1) | (pix[y * 9 + x] > pix[y * 9 + x + 1])
    return val


def prepare(args):
    base, source, review, output = (p.resolve() for p in (args.base, args.source, args.review, args.output))
    if output.exists():
        raise ValueError(f"Output already exists (not overwriting): {output}")
    if output.is_relative_to(base) or output.is_relative_to(source):
        raise ValueError("Output must be separate from existing dataset/source")
    if not base.is_dir() or not source.is_dir() or not review.is_file():
        raise ValueError("Missing base dataset, imported Lifeguard source, or triage CSV")

    audit = json.loads((base / "audit.json").read_text(encoding="utf-8"))
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    config = json.loads((base / "data.yaml").read_text(encoding="utf-8"))
    if audit.get("build_completed") is not True or audit.get("errors") or audit.get("classes") != CLASS_NAMES:
        raise ValueError("Base dataset is not audited as drowning=0, swimming=1")
    if config.get("names") != CLASS_NAMES:
        raise ValueError("Base data.yaml class mapping differs from expected mapping")

    rows = load_rows(review)
    required = {"image", "label", "source_group", "split", "source_url", "pilot_select", "visual_triage"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Missing columns: {sorted(required - set(rows[0] if rows else {}))}")
    selected = [r for r in rows if r["pilot_select"] == "yes"]
    if not selected:
        raise ValueError("No pilot samples selected in CSV")
    if any(r["visual_triage"] != "visual_candidate" or r["split"] != "train" for r in selected):
        raise ValueError("Pilot selection must be visual_candidate and train-only")

    # Prevalidate inputs before touching output.
    holdout_groups = {r.get("source_group", "") for r in manifest if r["split"] in ("val", "test")}
    base_records = []
    for i, r in enumerate(manifest):
        split = r["split"]
        if split not in ("train", "val", "test"):
            raise ValueError("Invalid original dataset split")
        img = safe_path(base, r["curated_image"])
        lbl = safe_path(base, f"labels/{split}/{img.stem}.txt")
        if not img.is_file() or not lbl.is_file():
            raise ValueError(f"Missing audited original image/label for manifest row {i}")
        if digest(img) != r["image_sha256"] or digest(lbl) != r["label_sha256"]:
            raise ValueError(f"Audited base image/label was modified: {img.name}")
        base_records.append((r, img, lbl))

    candidate_records = []
    for r in selected:
        if r["source_group"] in holdout_groups:
            raise ValueError("Incoming video group overlaps frozen original validation/test")
        if not r["source_group"] or not r["source_url"].startswith("https://www.youtube.com/watch?v="):
            raise ValueError("Missing original video provenance")
        img = safe_path(source, r["image"])
        lbl = safe_path(source, r["label"])
        if not img.is_file() or not lbl.is_file():
            raise ValueError(f"Missing Lifeguard file: {img} or {lbl}")
        nboxes = validate_yolo(lbl)
        if nboxes < 1:
            raise ValueError(f"Frame has no original bbox: {img}")
        # Verify every image can be decoded before creating an experiment.
        image_hash = digest(img)
        image_dhash = dhash(img)
        candidate_records.append((r, img, lbl, image_hash, image_dhash, nboxes))

    output.mkdir(parents=True)
    stats = Counter()
    records = []
    try:
        # Copy the immutable base data. Do not move or overwrite it.
        holdout_dhash = []
        for i, (r, img, lbl) in enumerate(base_records):
            split = r["split"]
            stem = f"base_{i:07d}"
            new_img = output / "images" / split / (stem + img.suffix.lower())
            new_lbl = output / "labels" / split / (stem + ".txt")
            new_img.parent.mkdir(parents=True, exist_ok=True)
            new_lbl.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, new_img)
            shutil.copy2(lbl, new_lbl)
            if split in ("val", "test"):
                holdout_dhash.append(dhash(new_img))
            stats["base_" + split] += 1
            records.append({"origin": "audited_base", "split": split, "source_group": r.get("source_group"),
                            "image": new_img.relative_to(output).as_posix(), "sha256": digest(new_img),
                            "label_sha256": digest(new_lbl), "source_image": str(img)})

        seen_hash = {r["sha256"] for r in records}
        skipped = []
        for i, (r, img, lbl, h, dh, boxes) in enumerate(candidate_records):
            if h in seen_hash:
                skipped.append({"image": r["image"], "reason": "exact_sha256_duplicate"})
                continue
            if any((dh ^ v).bit_count() <= args.dhash_threshold for v in holdout_dhash):
                skipped.append({"image": r["image"], "reason": "near_duplicate_with_frozen_holdout"})
                continue
            seen_hash.add(h)
            stem = f"lifeguard_{i:05d}_{h[:12]}"
            new_img = output / "images" / "train" / (stem + img.suffix.lower())
            new_lbl = output / "labels" / "train" / (stem + ".txt")
            new_img.parent.mkdir(parents=True, exist_ok=True)
            new_lbl.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, new_img)
            shutil.copy2(lbl, new_lbl)
            stats["lifeguard_train"] += 1
            stats["lifeguard_boxes"] += boxes
            records.append({"origin": "lifeguard_spotcheck", "split": "train", "source_group": r["source_group"],
                            "source_url": r["source_url"], "source_image": r["image"],
                            "image": new_img.relative_to(output).as_posix(), "sha256": digest(new_img),
                            "label_sha256": digest(new_lbl), "visual_triage": r["visual_triage"],
                            "rights_status": "unverified", "annotation_status": "not_temporally_verified"})
        if stats["lifeguard_train"] < 1:
            raise ValueError("No incoming images remained after holdout/duplicate checks")
        configuration = {"path": str(output), "train": "images/train", "val": "images/val",
                         "test": "images/test", "names": CLASS_NAMES}
        (output / "data.yaml").write_text(json.dumps(configuration, ensure_ascii=False, indent=2), encoding="utf-8")
        (output / "pilot_manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        details = {"created_utc": iso_now(), "experiment_only": True,
                   "reviewed_supervised_dataset": False, "rights_verified": False,
                   "model_deployment_permitted_by_this_tool": False,
                   "raw_frames_note": "49 visually promising clips were spot-checked at three contact-sheet frames each, not frame-by-frame or via temporal video review.",
                   "labels_note": "Original Z5cc CVAT drown/swim annotations, not independently verified clinical events.",
                   "source_license_note": "Video rights unverified; original YouTube footage and public annotations do not establish permission to train or redistribute.",
                   "frozen_holdout_note": "All originally audited val/test images and labels copied unchanged; holdout SHA256 preserved.",
                   "base_manifest_sha256": digest(base / "manifest.json"), "review_csv_sha256": digest(review),
                   "counts": dict(stats), "skipped": skipped,
                   "unique_new_sources": len({r["source_group"] for r in records if r["origin"] == "lifeguard_spotcheck"}),
                   "source_root": str(source), "base_root": str(base)}
        (output / "pilot_provenance.json").write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise
    print(json.dumps({"dataset": str(output), "counts": dict(stats),
                      "skipped": len(skipped), "rights_verified": False,
                      "safe_for_deployment": False}, indent=2))


def train(args):
    dataset, model, root = args.dataset.resolve(), args.model.resolve(), Path(__file__).resolve().parents[1]
    if not args.exploratory_unverified:
        raise ValueError("This is unverified YouTube footage. Explicitly pass --exploratory-unverified to run a local research experiment.")
    meta = json.loads((dataset / "pilot_provenance.json").read_text(encoding="utf-8"))
    if meta.get("experiment_only") is not True or meta.get("rights_verified") is not False:
        raise ValueError("Dataset is not the expected research-only pilot; refusing to train")
    if not model.is_file():
        raise ValueError(f"Missing local checkpoint: {model}")
    project = root / "data" / "training_exploratory"
    run = project / args.name
    if run.exists():
        raise ValueError(f"Run already exists, choose a new --name: {run}")
    project.mkdir(parents=True, exist_ok=True)
    run.mkdir()
    record = {"status": "running", "started_utc": iso_now(), "experiment_only": True,
              "rights_verified": False, "never_auto_deploy": True,
              "model": str(model), "model_sha256": digest(model), "dataset": str(dataset),
              "dataset_manifest_sha256": digest(dataset / "pilot_manifest.json"),
              "settings": {"epochs": args.epochs, "imgsz": args.imgsz, "batch": args.batch,
                           "device": args.device, "seed": 42},
              "limitations": ["Third-party footage rights unverified; not an approved public dataset.",
                              "CVAT labels are not independently verified temporal drowning events.",
                              "Cannot estimate alert accuracy from frame-level validation mAP."]}
    record_file = run / "research_record.json"
    def save():
        record_file.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    save()
    try:
        import torch
        from ultralytics import YOLO
        chosen_device = ("0" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
        os.environ.setdefault("YOLO_CONFIG_DIR", str(root / ".work" / "ultralytics"))
        os.environ.setdefault("MPLCONFIGDIR", str(root / ".work" / "matplotlib"))
        model_instance = YOLO(str(model))
        results = model_instance.train(data=str(dataset / "data.yaml"),
                    epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                    workers=0, device=chosen_device, project=str(project), name=args.name,
                    exist_ok=True, seed=42, deterministic=True, cache=False, amp=False,
                    plots=True, save=True, patience=12,
                    degrees=3, translate=0.05, scale=0.25, flipud=0,
                    fliplr=0.5, mosaic=0.25, mixup=0)
        best = run / "weights" / "best.pt"
        if not best.is_file():
            raise RuntimeError("Training completed without best.pt")
        record.update(status="completed", finished_utc=iso_now(),
                      best_model=str(best), best_model_sha256=digest(best),
                      validation_metrics=getattr(results, "results_dict", {}))
        save()
        print(json.dumps({"status": "completed", "experiment_only": True,
                          "candidate": str(best), "record": str(record_file)}))
    except Exception as exc:
        record.update(status="failed", finished_utc=iso_now(), error=str(exc))
        save()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("prepare", help="Build independent experimental YOLO dataset, preserving original val/test")
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--review", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--dhash-threshold", type=int, default=4)
    p.set_defaults(func=prepare)
    t = subs.add_parser("train", help="Run explicitly unverified research-only training, with no model promotion")
    t.add_argument("--dataset", type=Path, required=True)
    t.add_argument("--model", type=Path, required=True)
    t.add_argument("--name", default="lifeguard_pilot_v1")
    t.add_argument("--epochs", type=int, default=20)
    t.add_argument("--imgsz", type=int, default=416)
    t.add_argument("--batch", type=int, default=4)
    t.add_argument("--device", default="auto")
    t.add_argument("--exploratory-unverified", action="store_true")
    t.set_defaults(func=train)
    args = parser.parse_args()
    if args.command == "prepare" and not 0 <= args.dhash_threshold <= 64:
        parser.error("--dhash-threshold must be in [0,64]")
    if args.command == "train" and (args.epochs < 1 or args.imgsz < 32 or args.batch < 1):
        parser.error("Training parameters must be positive")
    try:
        args.func(args)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
