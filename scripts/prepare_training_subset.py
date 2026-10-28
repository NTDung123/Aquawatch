"""Export only individually reviewed above-water COCO images into YOLO format."""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

FIELDS = ["image", "label", "review_status", "viewpoint", "camera_motion", "source_group", "split",
          "source_url", "license", "notes"]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("data/research/deeprescue.zip"))
    parser.add_argument("--decisions", type=Path, default=Path("data/reviews/deeprescue_candidates.json"))
    parser.add_argument("--output", type=Path, default=Path("data/raw/deeprescue_reviewed"))
    parser.add_argument("--review-csv", type=Path, default=Path("data/reviews/deeprescue_reviewed.csv"))
    args = parser.parse_args()
    if args.output.exists() or args.review_csv.exists():
        parser.error("Use new output/review paths; existing evidence is not overwritten")
    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    approved = [r for r in decisions if r.get("review_status") == "approved" and r.get("viewpoint") == "above_water"]
    if not approved:
        parser.error("No individually approved above-water images exist in decisions")
    with ZipFile(args.archive) as archive:
        coco = json.loads(archive.read("train/_annotations.coco.json"))
        categories = {c["id"]: c["name"] for c in coco["categories"]}
        if categories.get(1) != "Drowning" or categories.get(3) != "Swimming":
            parser.error("Unexpected source class mapping; inspect archive before export")
        images = {r["id"]: r for r in coco["images"]}
        annotations = defaultdict(list)
        for annotation in coco["annotations"]:
            annotations[annotation["image_id"]].append(annotation)
        source_url = "https://www.kaggle.com/datasets/deeprescue/drowning-dataset"
        args.output.mkdir(parents=True)
        (args.output / "images").mkdir()
        (args.output / "labels").mkdir()
        csv_rows, clipped = [], []
        for decision in approved:
            image = images[decision["image_id"]]
            if image["file_name"] != decision["image"]:
                raise ValueError("Review image ID/name does not match source archive")
            boxes = annotations[image["id"]]
            if any(a["category_id"] not in {1, 3} for a in boxes):
                raise ValueError("Approved image contains an excluded source class")
            filename = Path(image["file_name"]).name
            (args.output / "images" / filename).write_bytes(archive.read("train/" + image["file_name"]))
            converted = []
            for box in boxes:
                x, y, width, height = box["bbox"]
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(image["width"], x + width), min(image["height"], y + height)
                if x2 <= x1 or y2 <= y1:
                    raise ValueError(f"Invalid source bbox in image {image['id']}")
                if [x1, y1, x2 - x1, y2 - y1] != box["bbox"]:
                    clipped.append({"image_id": image["id"], "annotation_id": box["id"], "original_bbox": box["bbox"],
                                    "clipped_bbox": [x1, y1, x2 - x1, y2 - y1]})
                class_id = 0 if box["category_id"] == 1 else 1
                converted.append(f"{class_id} {(x1+x2)/2/image['width']:.8f} {(y1+y2)/2/image['height']:.8f} "
                                 f"{(x2-x1)/image['width']:.8f} {(y2-y1)/image['height']:.8f}")
            label = Path(filename).with_suffix(".txt").name
            (args.output / "labels" / label).write_text("\n".join(converted) + "\n", encoding="utf-8")
            csv_rows.append({"image": "images/" + filename, "label": "labels/" + label,
                             "review_status": "approved", "viewpoint": "above_water",
                             "camera_motion": "unknown" if decision["source_group"] == "high_pool" else "fixed",
                             "source_group": decision["source_group"], "split": decision["split"],
                             "source_url": source_url,
                             "license": "CC0-1.0 (Kaggle uploader metadata; upstream footage rights unverified)",
                             "notes": decision["review_notes"]})
        args.review_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.review_csv.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(csv_rows)
        source = {"archive": str(args.archive.resolve()), "archive_sha256": digest(args.archive),
                  "source_url": source_url, "uploader_license": "CC0-1.0", "coco_licenses": coco.get("licenses"),
                  "decisions": str(args.decisions.resolve()), "decisions_sha256": digest(args.decisions),
                  "total_source_images": len(coco["images"]), "reviewed_candidates": len(decisions),
                  "approved_images": len(approved), "clipped_boxes": clipped,
                  "original_to_target_classes": {"1 Drowning": "0 drowning", "3 Swimming": "1 swimming"},
                  "excluded_source_categories": ["Humans", "Person out of water", "underwater_swimmers"],
                  "limitations": ["Uploader CC0 declaration does not verify upstream footage ownership.",
                                  "Local coursework experiment; original video attribution requires further verification before redistribution.",
                                  "Candidate contact sheets were visually reviewed for viewpoint and geometric plausibility, not clinical drowning truth.",
                                  "Source drowning/swimming labels remain weak labels and can be incomplete or semantically wrong.",
                                  "The three scene groups are disjoint only for this fine-tuning subset, not proven independent of pretraining.",
                                  "Unselected source images were excluded by whitelist, not exhaustively classified as underwater."]}
        (args.output / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "review_csv": str(args.review_csv), "approved": len(approved)}))


if __name__ == "__main__":
    main()
