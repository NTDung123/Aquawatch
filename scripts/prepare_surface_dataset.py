"""Propose, visually review, and export a scene-grouped above-water dataset."""

import argparse
import csv
import hashlib
import io
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "data" / "reviews"
DECISIONS = REVIEWS / "surface_v2_decisions.json"
FAMILIES = {
    "alanoud": {"archive": ROOT / "data/research/alanoud.zip", "url": "https://www.kaggle.com/datasets/alanoudawaji/swimming-and-drowning-dataset", "license": "CC BY 4.0", "mapping": {0: 0, 1: 1}},
    "mibugi": {"archive": ROOT / "data/research/mibugi.zip", "url": "https://github.com/Mibugi/Drowning-detection", "license": "CC BY 4.0", "mapping": {0: 0, 1: 1}},
}
MAIN = ("drowning1_mp4-", "drowning20_mp4-", "drowning47_mp4-", "drowning50_mp4_mp4-", "drowning51_mp4_mp4-", "drowning52_mp4_mp4-", "drowning53_mp4_mp4-", "drowning54_mp4_mp4-", "drowning55_mp4_mp4-", "12_mp4-", "-Clipchamp-_mp4-")
EXCLUDE_WORDS = ("stock", "istock", "getty", "depositphoto", "shutterstock", "passengers", "jennifer", "movie", "bikini", "funny-woman", "beautiful-")


def base_name(name):
    base = Path(name).name.split(".rf.")[0]
    while re.search(r"_(jpg|png|jpeg)$", base, re.I):
        base = re.sub(r"_(jpg|png|jpeg)$", "", base, flags=re.I)
    return base


def group_for(source, name):
    base = base_name(name)
    lower = base.lower()
    if any(word in lower for word in EXCLUDE_WORDS):
        return None, None, "stock/movie/source rights concern"
    if base.startswith("video_2022-12-07_23-08-"):
        return "high_pool", "val", "old validation scene locked outside train"
    if base.startswith("Untitled-video-Made-with-Clipchamp-1-_mp4-"):
        return "indoor_pool", "test", "old test scene locked outside train"
    if base.startswith(MAIN):
        return "waterpark_main", "train", "above-water CCTV scene seen in prior review"
    if base.startswith(("white-water_mp4-", "10_MOV-")):
        return "wave_pool", "train", "above-water pool candidate; requires individual review"
    if source == "mibugi" and re.match(r"IMG_36(?:07|08|09|10|11)_MOV-", base):
        return "indoor_training_pool", "train", "all five clips from same indoor pool grouped together"
    if source == "mibugi" and base.startswith("IMG_20240627"):
        return "outdoor_resort_pool", "val", "new outdoor scene held out as a group"
    if re.fullmatch(r"\d+", base):
        number = int(base)
        if source == "mibugi" and 998 <= number < 1200:
            return "competition_pool_cctv", "test", "new camera scene held out; ordinary swimmers/small targets"
        if number < 1000:
            return "numbered_pool_training_candidates", "train", "mixed numbered sources; approve only clear non-stock above-water pool views"
        if source == "alanoud" and number >= 10000:
            return "open_water_sequences", "train", "above-water aerial/shore candidates; individual viewpoint and box review required"
    if source == "mibugi":
        if base.startswith(("She-drowning_mp4-", "he-CANT-swim-and-went-to-a-water-park-_mp4-", "Screenshot-2024-07-30", "drown_girl_pool2_mp4-")):
            return "misc_above_water_demonstrations", "train", "above-water demonstration candidates; individual review required"
        if base.startswith(("WhatsApp-Video-2024-12-25", "Caught-on-tape-A-man-is-drowning-and-no-one-saves-him_mp4-")):
            return "indoor_other_cctv", "train", "indoor pool candidates; individual review required"
        if base.startswith(("output", "abovewater", "sw")) and not base.startswith("swim_man"):
            return "misc_pool_frames", "train", "unresolved pool frame candidates; individual review required"
    return None, None, "outside conservative above-water source whitelist; not exhaustively classified"


def quality(image):
    small = image.convert("RGB").resize((48, 48))
    pixels = list(small.get_flattened_data()) if hasattr(small, "get_flattened_data") else list(small.getdata())
    black = sum(max(pixel) < 12 for pixel in pixels) / len(pixels)
    natural_water = sum(g > r * 1.05 and b > r * 1.05 for r, g, b in pixels) / len(pixels)
    hsv_image = small.convert("HSV")
    hsv = list(hsv_image.get_flattened_data()) if hasattr(hsv_image, "get_flattened_data") else list(hsv_image.getdata())
    magenta = sum(180 < h < 245 and s > 70 for h, s, v in hsv) / len(hsv)
    gray = ImageStat.Stat(small.convert("HSV")).mean[1] < 15
    return natural_water - 5 * black - 2 * magenta - float(gray), black, magenta, gray


def labels_for(archive, name, source):
    label_name = name.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
    if label_name not in archive.namelist():
        raise ValueError("missing annotation")
    text = archive.read(label_name).decode("utf-8-sig")
    labels = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            raise ValueError("non-bbox annotation")
        class_id = int(parts[0])
        if class_id not in FAMILIES[source]["mapping"]:
            raise ValueError("image has noncanonical source class; no positive box silently dropped")
        values = list(map(float, parts[1:]))
        if not all(0 <= x <= 1 for x in values) or min(values[2:]) <= 0:
            raise ValueError("invalid bbox coordinates")
        labels.append([FAMILIES[source]["mapping"][class_id], *values])
    return labels


def propose(args):
    if args.decisions.exists():
        raise ValueError("Decisions exist; use review/build commands without replacing prior evidence")
    buckets = defaultdict(list)
    rejected = Counter()
    source_counts = {}
    for source, metadata in FAMILIES.items():
        with ZipFile(metadata["archive"]) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith((".jpg", ".png", ".jpeg"))]
            source_counts[source] = len(names)
            name_set = set(archive.namelist())
            for number, name in enumerate(names):
                group, split, reason = group_for(source, name)
                if group is None:
                    rejected[reason] += 1
                    continue
                try:
                    labels = labels_for(archive, name, source)
                except ValueError as error:
                    rejected[str(error)] += 1
                    continue
                data = archive.read(name)
                image = Image.open(io.BytesIO(data)).convert("RGB")
                score, black, magenta, gray = quality(image)
                # Generic numbered file names may represent different source images across exports.
                bucket = (source if re.fullmatch(r"\d+", base_name(name)) else "shared", base_name(name))
                buckets[bucket].append({"source": source, "entry": name, "original_name": base_name(name),
                                        "source_group": group, "split": split, "group_reason": reason,
                                        "labels": labels, "quality_score": score, "black_fraction": black,
                                        "magenta_fraction": magenta, "gray": gray})
    candidates = []
    duplicate_variants = 0
    samples = REVIEWS / "surface_v2_candidates"
    samples.mkdir(parents=True, exist_ok=True)
    archives = {key: ZipFile(value["archive"]) for key, value in FAMILIES.items()}
    try:
        for key, variants in sorted(buckets.items()):
            record = max(variants, key=lambda r: r["quality_score"])
            duplicate_variants += len(variants) - 1
            if record["black_fraction"] > 0.035 or record["magenta_fraction"] > 0.18 or record["gray"]:
                rejected["best variant still rotated/black-border/extreme tint/grayscale"] += 1
                continue
            data = archives[record["source"]].read(record["entry"])
            record["review_status"] = "pending"
            record["viewpoint"] = "unknown"
            record["review_notes"] = ""
            record["variant_count"] = len(variants)
            record["sha256"] = hashlib.sha256(data).hexdigest()
            record["candidate_id"] = len(candidates)
            target = samples / f"{len(candidates):05d}.jpg"
            target.write_bytes(data)
            record["preview_path"] = str(target)
            candidates.append(record)
    finally:
        for archive in archives.values():
            archive.close()
    args.decisions.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"source_image_counts": source_counts, "candidate_count": len(candidates),
               "candidate_groups": dict(Counter(r["source_group"] for r in candidates)),
               "excluded_before_individual_review": dict(rejected), "same_original_variants_removed": duplicate_variants}
    (REVIEWS / "surface_v2_proposal.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    sheets(candidates)
    print(json.dumps(summary, ensure_ascii=False))


def sheets(candidates):
    sheet_dir = REVIEWS / "surface_v2_sheets"
    sheet_dir.mkdir(exist_ok=True)
    for batch in range(math.ceil(len(candidates) / 32)):
        sheet = Image.new("RGB", (1920, 2080), "white")
        draw = ImageDraw.Draw(sheet)
        for k, record in enumerate(candidates[batch * 32: (batch + 1) * 32]):
            image = Image.open(record["preview_path"]).convert("RGB")
            width, height = image.size
            annotation = ImageDraw.Draw(image)
            for cl, cx, cy, w, h in record["labels"]:
                annotation.rectangle([(cx - w / 2) * width, (cy - h / 2) * height,
                                      (cx + w / 2) * width, (cy + h / 2) * height], outline="red" if cl == 0 else "lime", width=4)
            thumb = ImageOps.contain(image, (232, 230))
            x, y = (k % 8) * 240, (k // 8) * 520
            # Double-height cells keep each 232px image readable after tool resize.
            x, y = (k % 4) * 480, (k // 4) * 260
            thumb = ImageOps.contain(image, (470, 224))
            sheet.paste(thumb, (x + (480 - thumb.width) // 2, y + 32))
            draw.text((x + 4, y + 2), f"#{record['candidate_id']} {record['source']} {record['split']} {record['source_group'][:35]}", fill="black")
            draw.text((x + 4, y + 16), record["original_name"][:55], fill="black")
        sheet.save(sheet_dir / f"sheet_{batch:03d}.jpg", quality=94)


def build(args):
    records = json.loads(args.decisions.read_text(encoding="utf-8"))
    if any(r["review_status"] == "pending" for r in records):
        raise ValueError("All candidate review decisions must be completed before export")
    root = ROOT / "data" / "raw" / args.version
    if root.exists():
        raise ValueError("Raw output exists; preserve prior evidence")
    approved = [r for r in records if r["review_status"] == "approved" and r["viewpoint"] == "above_water"]
    root.mkdir(parents=True)
    (root / "images").mkdir()
    (root / "labels").mkdir()
    fields = ["image", "label", "review_status", "viewpoint", "camera_motion", "source_group", "split", "source_url", "license", "notes"]
    rows = []
    for record in approved:
        metadata = FAMILIES[record["source"]]
        name = f"{record['source']}_{record['candidate_id']:05d}.jpg"
        data = Path(record["preview_path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Candidate bytes changed after review")
        (root / "images" / name).write_bytes(data)
        label_name = Path(name).with_suffix(".txt").name
        (root / "labels" / label_name).write_text("\n".join(str(int(r[0])) + " " + " ".join(f"{v:.8f}" for v in r[1:]) for r in record["labels"]) + "\n", encoding="utf-8")
        rows.append({"image": "images/" + name, "label": "labels/" + label_name,
                     "review_status": "approved", "viewpoint": "above_water", "camera_motion": "unknown",
                     "source_group": record["source_group"], "split": record["split"], "source_url": metadata["url"],
                     "license": metadata["license"], "notes": record["review_notes"] + "; original=" + record["entry"]})
    review = REVIEWS / (args.version + ".csv")
    with review.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    source = {"sources": {key: {"archive": str(value["archive"]), "url": value["url"], "license": value["license"]} for key, value in FAMILIES.items()},
              "decisions": str(args.decisions.resolve()), "approved_images": len(approved), "rejected_images": len(records) - len(approved),
              "split_counts": dict(Counter(r["split"] for r in approved)), "scene_groups": dict(Counter(r["source_group"] for r in approved)),
              "limitations": ["Dataset labels are visual risk proxies, not verified clinical/event ground truth.",
                              "Pretrained community detector training provenance remains unknown; heldout scenes are independent only of this fine-tuning.",
                              "Declared CC BY 4.0 requires source attribution; upstream footage ownership is incompletely documented.",
                              "Old high_pool validation and indoor_pool test scenes and their variants never enter train.",
                              "Original export splits are replaced by conservative scene-level groups; near-duplicate review remains necessary."]}
    (root / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"raw": str(root), "review_csv": str(review), "approved_images": len(approved)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["propose", "build", "sheets"])
    parser.add_argument("--version", default="surface_v2")
    parser.add_argument("--decisions", type=Path, default=DECISIONS)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_-]+", args.version):
        parser.error("version must contain lowercase letters, numbers, underscores or hyphens")
    REVIEWS.mkdir(parents=True, exist_ok=True)
    if args.command == "propose":
        propose(args)
    elif args.command == "build":
        build(args)
    else:
        sheets(json.loads(DECISIONS.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
