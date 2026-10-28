import argparse
import csv
import json
from pathlib import Path

import pytest
from PIL import Image

from scripts.audit_dataset import FIELDS, build


def make_source(tmp_path, same_image=False):
    source = tmp_path / "source"
    source.mkdir()
    records = []
    for index, split in enumerate(("train", "val")):
        image = Image.new("RGB", (16, 16), "white")
        for x in range(16):
            for y in range(16):
                if (x < 8) if (index == 0 or same_image) else (x >= 8):
                    image.putpixel((x, y), (0, 0, 0))
        image.save(source / f"{index}.png")
        (source / f"{index}.txt").write_text("0 0.5 0.5 0.4 0.4\n", encoding="utf-8")
        records.append({"image": f"{index}.png", "label": f"{index}.txt", "review_status": "approved",
                        "viewpoint": "above_water", "camera_motion": "fixed", "source_group": f"video{index}",
                        "split": split, "source_url": "https://example.org/dataset", "license": "CC0-1.0", "notes": "test fixture"})
    return source, records


def run_build(tmp_path, source, records):
    review = tmp_path / "review.csv"
    with review.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    output = tmp_path / "curated"
    args = argparse.Namespace(source_root=source, review=review, output=output, classes=["drowning", "swimming"])
    build(args)
    return output


def test_underwater_image_is_excluded_from_dataset(tmp_path):
    source, records = make_source(tmp_path)
    (source / "underwater.png").write_bytes((source / "0.png").read_bytes())
    (source / "underwater.txt").write_text("0 0.5 0.5 0.4 0.4\n", encoding="utf-8")
    records.append({**records[0], "image": "underwater.png", "label": "underwater.txt", "viewpoint": "underwater"})
    output = run_build(tmp_path, source, records)
    audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
    assert audit["retained_images"] == 2
    assert audit["rejected"][0]["image"] == "underwater.png"
    assert not any("underwater" in p.name for p in (output / "images").rglob("*"))


def test_same_source_group_cannot_cross_train_val(tmp_path):
    source, records = make_source(tmp_path)
    records[1]["source_group"] = records[0]["source_group"]
    with pytest.raises(ValueError, match="Audit failed"):
        run_build(tmp_path, source, records)
    assert not (tmp_path / "curated").exists()


def test_exact_duplicate_cannot_cross_train_val(tmp_path):
    source, records = make_source(tmp_path, same_image=True)
    with pytest.raises(ValueError, match="Audit failed"):
        run_build(tmp_path, source, records)
    errors = json.loads((tmp_path / "review.audit_errors.json").read_text(encoding="utf-8"))["errors"]
    assert any("exact duplicate crosses splits" in error for error in errors)


def test_invalid_box_stops_export(tmp_path):
    source, records = make_source(tmp_path)
    (source / "0.txt").write_text("0 0.5 0.5 nan 0.4\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Audit failed"):
        run_build(tmp_path, source, records)
