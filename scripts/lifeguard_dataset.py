"""Import Z5cc Lifeguard CVAT annotations into AquaWatch's audited YOLO pipeline.

Usage from the AquaWatch project root:
  python scripts/lifeguard_dataset.py import --source D:/drowning-detection/dataset_lifeguard --out data/raw/lifeguard_z5cc --review data/reviews/lifeguard_z5cc.csv --stride 30
  python scripts/lifeguard_dataset.py merge --base data/curated/surface_v4 --source data/raw/lifeguard_z5cc --review data/reviews/lifeguard_z5cc.csv --out data/curated/surface_v5_lifeguard

Review rows are pending by default. The importer does not assume that YouTube footage,
CVAT labels, camera viewpoint, or third-party copyright permissions are verified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

FIELDS = ["image", "label", "review_status", "viewpoint", "camera_motion", "source_group",
          "split", "source_url", "license", "notes"]
CANONICAL_CLASSES = ["drowning", "swimming"]
CLASS_IDS = {"drown": 0, "swim": 1}
IMAGE_TYPES = (".jpg", ".jpeg", ".png")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def confined(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Unsafe path outside source root: {relative}")
    return path


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError(f"Review CSV must contain columns: {', '.join(FIELDS)}")
        return [{key: (row.get(key) or "").strip() for key in FIELDS} for row in reader]


def to_yolo(frame: ET.Element) -> list[str]:
    """Convert all CVAT boxes in one image to canonical normalized YOLO boxes.

    Reject an invalid frame in its entirety rather than silently dropping objects.
    """
    w, h = int(frame.attrib["width"]), int(frame.attrib["height"])
    if w <= 0 or h <= 0:
        raise ValueError("Invalid CVAT frame dimensions")
    result = []
    for box in frame.findall("box"):
        label = box.get("label", "")
        if label not in CLASS_IDS:
            raise ValueError(f"Unknown CVAT label {label!r}")
        x1, y1, x2, y2 = (float(box.attrib[p]) for p in ("xtl", "ytl", "xbr", "ybr"))
        if not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
            raise ValueError(f"Invalid/overflow CVAT bounding box: {x1,y1,x2,y2} in {w}x{h}")
        xc, yc = (x1 + x2) / (2*w), (y1 + y2) / (2*h)
        bw, bh = (x2 - x1) / w, (y2 - y1) / h
        result.append(f"{CLASS_IDS[label]} {xc:.8f} {yc:.8f} {bw:.8f} {bh:.8f}")
    return result


def import_lifeguard(source: Path, out: Path, review: Path, stride: int) -> dict:
    """Create reviewable, raw YOLO pairs. Never auto-approve observations."""
    source, out, review = source.resolve(), out.resolve(), review.resolve()
    if stride < 1:
        raise ValueError("--stride must be >=1 (e.g. 30 = 1 FPS from 30-FPS source)")
    if out.exists() or review.exists():
        raise ValueError("Raw output/review already exists. Use new version names; do not overwrite a review.")
    xml_dir, frame_dir = source / "labels", source / "frames"
    if not xml_dir.is_dir() or not frame_dir.is_dir():
        raise ValueError(f"Expected CVAT labels/ and frames/ under {source}")
    annotations = sorted(xml_dir.glob("*.xml"))
    if not annotations:
        raise ValueError("No CVAT XML labels found")

    # Prepare rows in memory first. No empty frame is called a hard negative without review.
    candidates = []
    issues = []
    stats = Counter()
    for xml_file in annotations:
        stats["xml_files"] += 1
        clip = xml_file.stem
        if len(clip) <= 12 or clip[11] != "_":
            issues.append(f"{clip}: filename does not start with an 11-char YouTube ID")
            continue
        youtube_id = clip[:11]
        frames = frame_dir / clip
        if not frames.is_dir():
            stats["missing_clip_directories"] += 1
            issues.append(f"{clip}: missing frames directory")
            continue
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError as exc:
            raise ValueError(f"Invalid XML: {xml_file}") from exc
        if root.tag != "annotations":
            raise ValueError(f"Not a CVAT annotations XML: {xml_file}")
        for ann in root.findall("image"):
            frame_id = int(ann.attrib["id"])
            if frame_id < 0 or frame_id % stride:
                continue
            stats["sampled_annotations"] += 1
            try:
                lines = to_yolo(ann)
            except (ValueError, KeyError) as exc:
                stats["invalid_annotations"] += 1
                issues.append(f"{clip} frame {frame_id}: {exc}")
                continue
            if not lines:
                stats["empty_box_frames_omitted"] += 1
                continue
            # Verified against upstream LifeguardUtils.get_box_and_label_list:
            # CVAT image ID is 0-based, FFmpeg's %06d.jpg numbering is 1-based.
            source_frame = frames / f"{frame_id + 1:06d}.jpg"
            if not source_frame.is_file():
                stats["missing_frame_files"] += 1
                issues.append(f"{clip} frame {frame_id}: {source_frame.name} missing")
                continue
            output_stem = f"{clip}__frame_{frame_id:06d}"
            image_rel = f"images/{output_stem}.jpg"
            label_rel = f"labels/{output_stem}.txt"
            candidates.append((source_frame, image_rel, label_rel, lines, youtube_id, clip, frame_id))
            stats["bbox_drowning"] += sum(line.startswith("0 ") for line in lines)
            stats["bbox_swimming"] += sum(line.startswith("1 ") for line in lines)
    if not candidates:
        raise ValueError("No usable annotated frames. Check XML/frames and --stride.")
    out.mkdir(parents=True)
    (out / "images").mkdir()
    (out / "labels").mkdir()
    rows = []
    for original, image_rel, label_rel, lines, vid, clip, frame_id in candidates:
        shutil.copy2(original, out / image_rel)
        (out / label_rel).write_text("\n".join(lines) + "\n", encoding="utf-8")
        rows.append({"image": image_rel, "label": label_rel, "review_status": "pending",
                     "viewpoint": "unknown", "camera_motion": "unknown",
                     "source_group": f"z5cc_youtube_{vid}", "split": "train",
                     "source_url": f"https://www.youtube.com/watch?v={vid}", "license": "",
                     "notes": f"Z5cc/CVAT interpolated boxes; clip={clip}; frame={frame_id}; review scene, boxes, rights"})
    write_csv(review, rows)
    stats["candidate_images"] = len(rows)
    stats["unique_youtube_sources"] = len(set(row["source_group"] for row in rows))
    meta = {"dataset": "Z5cc/drowning-detection Lifeguard", "repo": "https://github.com/Z5cc/drowning-detection",
            "created_utc": datetime.now(timezone.utc).isoformat(), "source": str(source),
            "stride": stride, "canonical_names": CANONICAL_CLASSES,
            "license_status": "unverified; requires actual permission/valid license checks before audit approval",
            "annotation_note": "CVAT manual keyframes, interpolated intermediate boxes; labels are not clinical diagnoses",
            "review_csv": str(review), "stats": dict(stats), "issues": issues}
    (out / "source.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "review": str(review), "stats": dict(stats),
                      "issue_count": len(issues)}, ensure_ascii=False, indent=2))
    return meta


def add_file(src: Path, dest: Path):
    if not src.is_file():
        raise ValueError(f"Missing input file: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise ValueError(f"Staging collision: {dest}")
    shutil.copy2(src, dest)


def extend_dataset(base: Path, source: Path, review: Path, out: Path, stage: Path) -> dict:
    """Re-audit baseline + manually approved new TRAIN items. Freeze old val/test."""
    base, source, review, out, stage = (p.resolve() for p in (base, source, review, out, stage))
    if out.exists() or stage.exists():
        raise ValueError("Output/staging path already exists. Use a fresh version name.")
    if base == source or stage.is_relative_to(base) or stage.is_relative_to(source):
        raise ValueError("Staging must be separate from base and incoming data")
    try:
        base_audit = json.loads((base / "audit.json").read_text(encoding="utf-8"))
        base_config = json.loads((base / "data.yaml").read_text(encoding="utf-8"))
        base_manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Cannot read audited base dataset") from exc
    if not base_audit.get("build_completed") or base_audit.get("errors") or base_audit.get("classes") != CANONICAL_CLASSES:
        raise ValueError("Base audit is incomplete or class mapping differs from drowning/swimming")
    if base_config.get("names") != CANONICAL_CLASSES or not base_manifest:
        raise ValueError("Base data.yaml/manifest missing or incompatible")
    rows = read_csv(review)
    approved = [r for r in rows if r["review_status"].lower() == "approved"]
    if not approved:
        raise ValueError("No approved review rows; inspect and mark selected above-water examples before merging")
    for r in approved:
        if r["split"] != "train" or r["viewpoint"] != "above_water":
            raise ValueError("Incoming approved examples must be above_water TRAIN only; old val/test are frozen")
        if not r["source_group"] or not r["source_url"] or not r["license"] or r["license"].lower() in {"unknown", "none", "unverified"}:
            raise ValueError("Approved examples require video-level source_group, source URL and a verified usable license")
    # Reuse the repository's own audit builder after combining the two sources.
    stage.mkdir(parents=True)
    combined = []
    for i, entry in enumerate(base_manifest):
        split = entry["split"]
        if split not in {"train", "val", "test"}:
            raise ValueError("Invalid base split")
        source_image = confined(base, entry["curated_image"])
        source_label = confined(base, f"labels/{split}/{source_image.stem}.txt")
        if sha256(source_image) != entry["image_sha256"] or sha256(source_label) != entry["label_sha256"]:
            raise ValueError(f"Base manifest SHA mismatch: {source_image}")
        ext = source_image.suffix.lower()
        target_stem = f"base_{i:07d}"
        dest_image = f"images/{target_stem}{ext}"
        dest_label = f"labels/{target_stem}.txt"
        add_file(source_image, stage / dest_image)
        add_file(source_label, stage / dest_label)
        row = {key: str(entry.get(key, "")) for key in FIELDS}
        row.update(image=dest_image, label=dest_label)
        combined.append(row)
    for i, entry in enumerate(approved):
        source_image = confined(source, entry["image"])
        source_label = confined(source, entry["label"])
        if source_image.suffix.lower() not in IMAGE_TYPES:
            raise ValueError(f"Unsupported source image extension: {source_image}")
        dest_image = f"images/lifeguard_{i:07d}{source_image.suffix.lower()}"
        dest_label = f"labels/lifeguard_{i:07d}.txt"
        add_file(source_image, stage / dest_image)
        add_file(source_label, stage / dest_label)
        combined.append({**entry, "image": dest_image, "label": dest_label})
    combined_review = stage / "combined_review.csv"
    write_csv(combined_review, combined)
    (stage / "source.json").write_text(json.dumps({"base": str(base), "base_sha256": sha256(base / "manifest.json"),
        "lifeguard_source": str(source), "lifeguard_review": str(review), "review_sha256": sha256(review),
        "license_note": "Source-level rights verified by user review only; no automatic verification"}, indent=2), encoding="utf-8")
    # sys.path[0] is scripts/ when invoked as a file from PowerShell.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from audit_dataset import build  # type: ignore

    build(SimpleNamespace(source_root=stage, review=combined_review, output=out, classes=CANONICAL_CLASSES))
    output_manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    def locked_signatures(items):
        return sorted((e["split"], e["image_sha256"], e["label_sha256"], e["source_group"])
                      for e in items if e["split"] in {"val", "test"})
    if locked_signatures(base_manifest) != locked_signatures(output_manifest):
        raise ValueError("FAIL: validation/test frozen signatures changed, do not train on this output")
    result = {"output": str(out), "base_images": len(base_manifest), "approved_lifeguard_images": len(approved),
              "output_images": len(output_manifest), "frozen_val_test": True,
              "stage": str(stage), "audit": str(out / "audit.json")}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result



def render_sheets(source: Path, review: Path, out: Path, columns: int = 5, rows_per_sheet: int = 5) -> int:
    """Draw review sheets with all source YOLO boxes, never assign approval automatically."""
    from PIL import Image, ImageDraw

    source, review, out = source.resolve(), review.resolve(), out.resolve()
    if out.exists():
        raise ValueError("Review sheets directory already exists; use a new path")
    entries = read_csv(review)
    if not entries:
        raise ValueError("No review entries")
    if columns < 1 or rows_per_sheet < 1:
        raise ValueError("columns and rows must be positive")
    out.mkdir(parents=True)
    tile_w, tile_h = 224, 254
    count = 0
    batch_size = columns * rows_per_sheet
    for start in range(0, len(entries), batch_size):
        batch = entries[start:start + batch_size]
        sheet = Image.new("RGB", (columns * tile_w, rows_per_sheet * tile_h), "#EEEEEE")
        d = ImageDraw.Draw(sheet)
        for index, entry in enumerate(batch):
            original = confined(source, entry["image"])
            label_path = confined(source, entry["label"])
            with Image.open(original) as opened:
                img = opened.convert("RGB")
            width, height = img.size
            img.thumbnail((tile_w, tile_w))
            col, row = index % columns, index // columns
            x0, y0 = col * tile_w, row * tile_h
            sheet.paste(img, (x0, y0))
            sx, sy = img.width / width, img.height / height
            for line in label_path.read_text(encoding="utf-8").splitlines():
                fields = line.split()
                if len(fields) != 5:
                    raise ValueError(f"Malformed YOLO label in {label_path}")
                cls = int(fields[0])
                xc, yc, bw, bh = map(float, fields[1:])
                if cls not in (0, 1):
                    raise ValueError(f"Unsupported class {cls} in {label_path}")
                left = x0 + (xc - bw/2) * width * sx
                top = y0 + (yc - bh/2) * height * sy
                right = x0 + (xc + bw/2) * width * sx
                bottom = y0 + (yc + bh/2) * height * sy
                color = "#FF4141" if cls == 0 else "#1E98FF"
                d.rectangle((left, top, right, bottom), outline=color, width=2)
            d.text((x0 + 4, y0 + 226), f"#{start+index} {Path(entry['image']).stem[:11]}", fill="#101010")
            d.text((x0 + 4, y0 + 239), Path(entry['image']).stem.rsplit("__frame_", 1)[-1], fill="#444444")
        sheet.save(out / f"sheet_{count:04d}.jpg", quality=90)
        count += 1
    print(json.dumps({"review_sheets": str(out), "sheets": count, "images": len(entries),
                      "legend": {"red": "drowning", "blue": "swimming"}}))
    return count

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    importer = commands.add_parser("import", help="CVAT XML + original frames -> raw YOLO pairs & pending review")
    importer.add_argument("--source", type=Path, required=True, help="Path to Z5cc dataset_lifeguard folder")
    importer.add_argument("--out", type=Path, required=True, help="New raw YOLO destination")
    importer.add_argument("--review", type=Path, required=True, help="New CSV requiring manual review")
    importer.add_argument("--stride", type=int, default=30, help="Use every Nth annotated frame, default 30 (1 FPS)")
    sheets = commands.add_parser("sheets", help="Draw image+bounding-box contact sheets for manual review")
    sheets.add_argument("--source", type=Path, required=True, help="Output of import step")
    sheets.add_argument("--review", type=Path, required=True, help="Review CSV produced by import step")
    sheets.add_argument("--out", type=Path, required=True, help="New directory containing contact sheets")
    merger = commands.add_parser("merge", help="Combine existing audited dataset with approved Lifeguard training data")
    merger.add_argument("--base", type=Path, required=True, help="Existing audited dataset, typically surface_v4")
    merger.add_argument("--source", type=Path, required=True, help="Output of import step")
    merger.add_argument("--review", type=Path, required=True, help="Reviewed CSV produced by import step")
    merger.add_argument("--out", type=Path, required=True, help="New curated YOLO dataset")
    merger.add_argument("--stage", type=Path, help="New staging directory (defaults to data/raw/<output name>_union)")
    args = cli.parse_args()
    try:
        if args.command == "import":
            import_lifeguard(args.source, args.out, args.review, args.stride)
        elif args.command == "sheets":
            render_sheets(args.source, args.review, args.out)
        else:
            stage = args.stage or (args.out.parent.parent / "raw" / (args.out.name + "_union"))
            extend_dataset(args.base, args.source, args.review, args.out, stage)
    except (ValueError, OSError) as exc:
        cli.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
