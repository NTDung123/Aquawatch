"""Review previously unselected source images without changing locked datasets."""

import argparse
import csv
import hashlib
import io
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageOps

import audit_dataset
from prepare_surface_dataset import FAMILIES, ROOT, base_name, group_for, quality

REVIEW = ROOT / "data/reviews/expanded_v4_decisions.json"
PREV = ROOT / "data/reviews/surface_v3_decisions.json"


def family(name):
    original = base_name(name)
    if re.match(r"image\d+$", original, re.I):
        return "image_numbered"
    if re.match(r"(?:D|dr)\d+$", original):
        return "static_numbered"
    if original.startswith("drowning_"):
        return "drowning_numbered_sequences"
    return re.sub(r"([_-])\d+(?:-\d+)?$", "", original)


def read_source_labels(archive, name, source):
    entry = name.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
    values = [[float(value) for value in line.split()] for line in
              archive.read(entry).decode("utf-8-sig").splitlines() if line.strip()]
    if any(len(row) != 5 or not row[0].is_integer() for row in values):
        raise ValueError("invalid source annotation")
    classes = {int(row[0]) for row in values}
    if source == "alanoud" and classes == {2}:
        return [], "Only source out_of_water boxes; reviewed as target-free background, not relabeled swimming."
    if not classes.issubset({0, 1}):
        raise ValueError("mixed/noncanonical source classes; no target box silently dropped")
    if any(not all(math.isfinite(v) and 0 <= v <= 1 for v in row[1:]) or
           min(row[3:]) <= 0 for row in values):
        raise ValueError("invalid normalized source annotation")
    return [[int(row[0]), *row[1:]] for row in values], ""


def discover(args):
    if args.review.exists():
        raise ValueError("Review already exists; preserving previous decisions")
    previous = json.loads(PREV.read_text(encoding="utf-8"))
    old_names = {(r["source"], r["original_name"]) for r in previous}
    buckets = defaultdict(list)
    counts = Counter()
    for source, metadata in FAMILIES.items():
        with ZipFile(metadata["archive"]) as archive:
            for name in archive.namelist():
                if not name.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                original = base_name(name)
                group, split, reason = group_for(source, name)
                if (source, original) in old_names or group is not None:
                    counts["already considered by surface_v3"] += 1
                    continue
                if "rights concern" in reason:
                    counts["explicit stock/movie name"] += 1
                    continue
                try:
                    labels, note = read_source_labels(archive, name, source)
                except (ValueError, KeyError) as error:
                    counts[str(error)] += 1
                    continue
                data = archive.read(name)
                image = Image.open(io.BytesIO(data)).convert("RGB")
                score, black, magenta, gray = quality(image)
                key = (source if re.fullmatch(r"\d+", original) else "shared", original)
                buckets[key].append({"source": source, "entry": name, "original_name": original,
                                     "labels": labels, "source_label_note": note,
                                     "quality_score": score, "black_fraction": black,
                                     "magenta_fraction": magenta, "gray": gray})
    preview = ROOT / "data/reviews/expanded_v4_candidates"
    preview.mkdir(parents=True, exist_ok=True)
    records = []
    with ZipFile(FAMILIES["alanoud"]["archive"]) as alanoud, ZipFile(FAMILIES["mibugi"]["archive"]) as mibugi:
        archives = {"alanoud": alanoud, "mibugi": mibugi}
        for _, variants in sorted(buckets.items(), key=lambda item: (family(item[1][0]["entry"]), item[0])):
            best = max(variants, key=lambda row: row["quality_score"])
            counts["same-original alternate exports removed"] += len(variants) - 1
            if best["black_fraction"] > .035 or best["magenta_fraction"] > .18 or best["gray"]:
                counts["best variant artificial border/tint/grayscale"] += 1
                continue
            data = archives[best["source"]].read(best["entry"])
            number = len(records)
            path = preview / f"{number:05d}.jpg"
            path.write_bytes(data)
            best.update(candidate_id=number, preview_path=str(path), sha256=hashlib.sha256(data).hexdigest(),
                        source_family=family(best["entry"]), source_group="unresolved", split="unresolved",
                        viewpoint="unknown", review_status="pending", review_notes="", reviewer="",
                        variant_count=len(variants))
            records.append(best)
    args.review.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"candidates": len(records), "families": dict(Counter(r["source_family"] for r in records)),
               "pre_review_counts": dict(counts), "scope": "Previously unselected originals only; not a dataset approval."}
    args.review.with_name("expanded_v4_discovery.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    render(records, args.review)
    print(json.dumps(summary, ensure_ascii=True))


def render(records, review):
    target = review.parent / "expanded_v4_sheets"
    target.mkdir(exist_ok=True)
    for start in range(0, len(records), 24):
        sheet = Image.new("RGB", (1920, 1560), "white")
        draw = ImageDraw.Draw(sheet)
        for offset, record in enumerate(records[start:start + 24]):
            image = Image.open(record["preview_path"]).convert("RGB")
            width, height = image.size
            annotation = ImageDraw.Draw(image)
            for cl, cx, cy, w, h in record["labels"]:
                annotation.rectangle(((cx - w / 2) * width, (cy - h / 2) * height,
                                      (cx + w / 2) * width, (cy + h / 2) * height),
                                     outline="red" if cl == 0 else "lime", width=3)
            thumb = ImageOps.contain(image, (472, 220))
            x, y = offset % 4 * 480, offset // 4 * 260
            sheet.paste(thumb, (x + (480 - thumb.width) // 2, y + 35))
            draw.text((x + 3, y + 2), f"#{record['candidate_id']} {record['source']} {record['source_family'][:42]}", fill="black")
            draw.text((x + 3, y + 18), record["original_name"][:65], fill="black")
        sheet.save(target / f"sheet_{start // 24:03d}.jpg", quality=95)


def build(args):
    extra = json.loads(args.review.read_text(encoding="utf-8"))
    if any(row["review_status"] == "pending" for row in extra):
        raise ValueError("Every discovered candidate must receive a recorded decision")
    previous = json.loads(PREV.read_text(encoding="utf-8"))
    previous = [r for r in previous if r["review_status"] == "approved" and r["viewpoint"] == "above_water"]
    added = [r for r in extra if r["review_status"] == "approved" and r["viewpoint"] == "above_water"]
    if not added:
        raise ValueError("No newly reviewed images approved; use existing surface_v3 rather than create a duplicate dataset")
    root = ROOT / "data/raw" / args.version
    output = ROOT / "data/curated" / args.version
    if root.exists() or output.exists():
        raise ValueError("Dataset version already exists; refusing to overwrite evidence")
    root.mkdir(parents=True)
    (root / "images").mkdir()
    (root / "labels").mkdir()
    rows = []
    hashes = {}
    duplicates = []
    evaluation_signature = set()
    old_test = {r["sha256"]: r["split"] for r in previous if r["split"] != "train"}
    for index, record in enumerate(previous + added):
        if record["split"] not in {"train", "val", "test"} or record["source_group"] == "unresolved":
            raise ValueError("Approved candidate requires camera/source group and split")
        if index >= len(previous):
            if record["split"] != "train":
                raise ValueError("Additional images must be train-only; preserve exact v3 validation/test imagery")
            if record["source_group"] in {"high_pool", "indoor_pool", "outdoor_resort_pool", "competition_pool_cctv", "indoor_other_cctv"}:
                raise ValueError("Locked evaluation scene cannot enter training")
            if not record.get("reviewer") or not record.get("review_notes"):
                raise ValueError("Every added image requires explicit visual reviewer and decision notes")
        data = Path(record["preview_path"]).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != record["sha256"]:
            raise ValueError("Image changed after visual review")
        if digest in old_test and old_test[digest] != record["split"]:
            raise ValueError("Existing evaluation image crossed splits")
        label_text = "\n".join(str(int(v[0])) + " " + " ".join(f"{x:.8f}" for x in v[1:]) for v in record["labels"]) + "\n"
        if digest in hashes:
            prior = hashes[digest]
            if prior != (record["split"], label_text):
                raise ValueError("Duplicate bytes have conflicting labels or splits")
            duplicates.append({"source": record["source"], "entry": record["entry"],
                               "reason": "same image SHA-256 and identical canonical labels"})
            continue
        hashes[digest] = (record["split"], label_text)
        name = f"{record['source']}_{index:05d}.jpg"
        (root / "images" / name).write_bytes(data)
        label = Path(name).with_suffix(".txt").name
        (root / "labels" / label).write_text(label_text, encoding="utf-8")
        if record["split"] != "train":
            evaluation_signature.add((digest, audit_dataset.sha256(root / "labels" / label),
                                      record["split"], record["source_group"]))
        metadata = FAMILIES[record["source"]]
        rows.append({"image": "images/" + name, "label": "labels/" + label,
                     "review_status": "approved", "viewpoint": "above_water", "camera_motion": "unknown",
                     "source_group": record["source_group"], "split": record["split"],
                     "source_url": metadata["url"], "license": metadata["license"],
                     "notes": record["review_notes"] + "; original=" + record["entry"]})
    csv_path = args.review.parent / (args.version + ".csv")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=audit_dataset.FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    frozen = json.loads((ROOT / "data/curated/surface_v3/manifest.json").read_text(encoding="utf-8"))
    frozen_signature = {(r["image_sha256"], r["label_sha256"], r["split"], r["source_group"])
                        for r in frozen if r["split"] != "train"}
    if evaluation_signature != frozen_signature:
        raise ValueError("Exact validation/test image-label-group signature differs from frozen surface_v3")
    source = {"parent_dataset": "surface_v3", "sources": FAMILIES,
              "prior_review": str(PREV), "additional_review": str(args.review),
              "additional_approved": len(added), "pre_audit_exact_duplicates_removed": duplicates,
              "frozen_v3_validation_test_signatures_equal": True,
              "limitations": [
                  "Source labels are weak visual risk proxies, not independent clinical annotation.",
                  "All old evaluation scenes remain evaluation-only; adjacent frames are not independent events.",
                  "Uploader CC BY 4.0 does not independently establish third-party footage ownership."]}
    (root / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    audit_dataset.build(SimpleNamespace(source_root=root, review=csv_path, output=output, classes=["drowning", "swimming"]))
    attribution = output / "attribution"
    for source_name, metadata in FAMILIES.items():
        destination = attribution / source_name
        destination.mkdir(parents=True)
        with ZipFile(metadata["archive"]) as archive:
            for entry in archive.namelist():
                if Path(entry).name.lower() in {"readme.dataset.txt", "readme.roboflow.txt", "license", "license.txt", "data.yaml"}:
                    (destination / Path(entry).name).write_bytes(archive.read(entry))
        (destination / "SOURCE.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["discover", "sheets", "build"])
    parser.add_argument("--review", type=Path, default=REVIEW)
    parser.add_argument("--version", default="surface_v4")
    args = parser.parse_args()
    if args.command == "discover":
        discover(args)
    elif args.command == "sheets":
        render(json.loads(args.review.read_text(encoding="utf-8")), args.review)
    else:
        build(args)


if __name__ == "__main__":
    main()
