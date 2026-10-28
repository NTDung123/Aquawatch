"""Create a human review sheet, then build a reviewed YOLO detection dataset."""

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
FIELDS = ["image", "label", "review_status", "viewpoint", "camera_motion", "source_group", "split",
          "source_url", "license", "notes"]
SPLITS = {"train", "val", "test"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def confined(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes source root: {name}")
    return path


def find_label(root, image):
    relative = image.relative_to(root)
    parts = list(relative.parts)
    if "images" in parts:
        parts[parts.index("images")] = "labels"
        candidate = root.joinpath(*parts).with_suffix(".txt")
        if candidate.is_file():
            return candidate.relative_to(root).as_posix()
    candidate = image.with_suffix(".txt")
    return candidate.relative_to(root).as_posix() if candidate.is_file() else ""


def init_review(args):
    root = args.source_root.resolve()
    if not root.is_dir():
        raise ValueError(f"Source directory does not exist: {root}")
    if args.review.exists():
        raise ValueError(f"Review file already exists; refusing to overwrite: {args.review}")
    images = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    args.review.parent.mkdir(parents=True, exist_ok=True)
    with args.review.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for image in images:
            writer.writerow({"image": image.relative_to(root).as_posix(), "label": find_label(root, image),
                             "review_status": "pending", "viewpoint": "unknown", "camera_motion": "unknown"})
    print(json.dumps({"images": len(images), "review": str(args.review.resolve()),
                      "message": "Review every retained image and annotation before approval."}))


def read_labels(path, classes):
    content = path.read_text(encoding="utf-8-sig")
    counts = Counter()
    for number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"{path}:{number}: expected class x_center y_center width height")
        class_id = int(fields[0])
        if str(class_id) != fields[0] or not 0 <= class_id < len(classes):
            raise ValueError(f"{path}:{number}: invalid class ID")
        x, y, width, height = map(float, fields[1:])
        if not all(0 <= value <= 1 for value in (x, y, width, height)) or width <= 0 or height <= 0:
            raise ValueError(f"{path}:{number}: invalid normalized box")
        if x - width / 2 < -0.01 or y - height / 2 < -0.01 or x + width / 2 > 1.01 or y + height / 2 > 1.01:
            raise ValueError(f"{path}:{number}: box exceeds image boundaries")
        counts[classes[class_id]] += 1
    return counts


def image_info(path):
    from PIL import Image

    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        width, height = image.size
        small = image.convert("L").resize((9, 8))
        pixels = [small.getpixel((x, y)) for y in range(8) for x in range(9)]
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return width, height, f"{value:016x}"


def build(args):
    root = args.source_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"Output already exists; use a new versioned destination: {output}")
    with args.review.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError(f"Review CSV must contain fields: {', '.join(FIELDS)}")
        rows = list(reader)
    candidates, rejected, duplicates = [], [], []
    seen_images, seen_sha, groups, perceptual = set(), {}, {}, defaultdict(list)
    errors = []
    for row_number, row in enumerate(rows, 2):
        row = {key: (value or "").strip() for key, value in row.items() if key is not None}
        filename = row["image"]
        if filename in seen_images:
            errors.append(f"row {row_number}: duplicate review row for {filename}")
            continue
        seen_images.add(filename)
        if row["review_status"].lower() != "approved" or row["viewpoint"].lower() != "above_water":
            rejected.append({"image": filename, "reason": "not approved above-water", "review": row})
            continue
        try:
            if row["camera_motion"] not in {"fixed", "ptz", "handheld", "unknown"}:
                raise ValueError("camera_motion must be fixed, ptz, handheld, or unknown")
            split, group = row["split"], row["source_group"]
            if split not in SPLITS or not group:
                raise ValueError("approved image requires explicit split and original video/session source_group")
            if group in groups and groups[group] != split:
                raise ValueError(f"source_group {group!r} appears in both {groups[group]} and {split}")
            groups[group] = split
            if not row["source_url"] or not row["license"] or row["license"].lower() in {"unknown", "none", "unverified", "chưa xác minh được"}:
                raise ValueError("approved image requires a source URL and verified usable license")
            image = confined(root, filename)
            label = confined(root, row["label"])
            if not image.is_file() or image.suffix.lower() not in IMAGE_SUFFIXES or not label.is_file():
                raise ValueError("image/label is missing or image extension is unsupported")
            counts = read_labels(label, args.classes)
            width, height, dhash = image_info(image)
            digest, label_digest = sha256(image), sha256(label)
            if digest in seen_sha:
                prior = seen_sha[digest]
                if prior["split"] != split:
                    raise ValueError(f"exact duplicate crosses splits: {prior['image']} vs {filename}")
                if prior["label_sha256"] != label_digest:
                    raise ValueError(f"exact duplicate has inconsistent labels: {prior['image']} vs {filename}")
                duplicates.append({"image": filename, "same_as": prior["image"], "reason": "exact SHA-256 duplicate"})
                continue
            record = {**row, "image_sha256": digest, "label_sha256": label_digest,
                      "width": width, "height": height, "dhash": dhash, "class_counts": dict(counts)}
            seen_sha[digest] = record
            candidates.append(record)
            perceptual[dhash].append(record)
        except (OSError, ValueError) as error:
            errors.append(f"row {row_number} ({filename}): {error}")
    near_matches = []
    for values in perceptual.values():
        if len(values) > 1:
            near_matches.append({"images": [r["image"] for r in values],
                                 "splits": sorted({r["split"] for r in values}),
                                 "reason": "same dHash, possible near duplicate; manual review required"})
            if len({r["split"] for r in values}) > 1:
                errors.append("possible near duplicate crosses splits: " + ", ".join(r["image"] for r in values))
    counts = Counter(record["split"] for record in candidates)
    if not counts["train"] or not counts["val"]:
        errors.append("a training experiment requires nonempty train and val with disjoint source_group")
    audit = {"created_utc": datetime.now(timezone.utc).isoformat(), "source_root": str(root),
             "review_csv": str(args.review.resolve()), "review_sha256": sha256(args.review),
             "classes": args.classes, "review_rows": len(rows), "retained_images": len(candidates),
             "split_counts": dict(counts), "group_split": groups, "rejected": rejected,
             "exact_duplicates_removed": duplicates, "possible_near_duplicates": near_matches,
             "errors": errors, "build_completed": not errors,
             "limitations": ["dHash equality does not detect all near duplicates.",
                             "Human review supplies camera viewpoint, label validity, source group and license.",
                             "Source group separation does not prove independence from unknown pretrained training data."]}
    if (root / "source.json").is_file():
        audit["source_metadata"] = json.loads((root / "source.json").read_text(encoding="utf-8"))
    if errors:
        report = args.review.with_name(args.review.stem + ".audit_errors.json")
        report.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        raise ValueError(f"Audit failed ({len(errors)} errors). See {report}; no dataset was built.")
    output.mkdir(parents=True)
    totals = {split: Counter() for split in SPLITS}
    for number, record in enumerate(candidates):
        split = record["split"]
        image = confined(root, record["image"])
        identifier = f"{number:07d}_{record['image_sha256'][:12]}"
        image_target = output / "images" / split / (identifier + image.suffix.lower())
        label_target = output / "labels" / split / (identifier + ".txt")
        image_target.parent.mkdir(parents=True, exist_ok=True)
        label_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image, image_target)
        shutil.copy2(confined(root, record["label"]), label_target)
        record["curated_image"] = image_target.relative_to(output).as_posix()
        totals[split].update(record["class_counts"])
    configuration = {"path": output.as_posix(), "train": "images/train", "val": "images/val",
                     "names": args.classes}
    if counts["test"]:
        configuration["test"] = "images/test"
    # JSON is a YAML subset and can be loaded by Ultralytics' YAML reader.
    (output / "data.yaml").write_text(json.dumps(configuration, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "manifest.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    audit["class_box_counts"] = {key: dict(value) for key, value in totals.items()}
    (output / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "retained_images": len(candidates), "split_counts": dict(counts)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init")
    initialize.add_argument("--source-root", type=Path, required=True)
    initialize.add_argument("--review", type=Path, required=True)
    initialize.set_defaults(action=init_review)
    curate = commands.add_parser("build")
    curate.add_argument("--source-root", type=Path, required=True)
    curate.add_argument("--review", type=Path, required=True)
    curate.add_argument("--output", type=Path, required=True)
    curate.add_argument("--classes", nargs="+", required=True, help="Class names in original YOLO class-ID order")
    curate.set_defaults(action=build)
    args = parser.parse_args()
    try:
        args.action(args)
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
