"""Download and inspect the user-provided Alanoud Kaggle archive without training."""
import hashlib
import json
from pathlib import Path
from collections import Counter
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data" / "research"
ARCHIVE = FOLDER / "alanoud.zip"
URL = "https://www.kaggle.com/api/v1/datasets/download/alanoudawaji/swimming-and-drowning-dataset"


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    if not ARCHIVE.exists():
        temporary = ARCHIVE.with_suffix(".zip.part")
        request = urllib.request.Request(URL, headers={"User-Agent": "AquaWatch-academic/1.0"})
        with opener.open(request, timeout=120) as response, temporary.open("wb") as target:
            while block := response.read(1024 * 1024):
                target.write(block)
        if not zipfile.is_zipfile(temporary):
            raise RuntimeError("The endpoint did not return a ZIP archive")
        temporary.replace(ARCHIVE)
    digest = hashlib.sha256()
    with ARCHIVE.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    with zipfile.ZipFile(ARCHIVE) as archive:
        names = archive.namelist()
        metadata = {}
        images, labels = [], []
        splits = Counter()
        for name in names:
            lower = name.lower()
            if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
                images.append(name)
                splits[name.split("/")[0]] += 1
            elif lower.endswith(".txt") and "/labels/" in lower:
                labels.append(name)
            if lower.endswith(("readme.dataset.txt", "readme.roboflow.txt", "data.yaml", "license", "license.txt", "license.md", "classes.txt")):
                metadata[name] = archive.read(name).decode("utf-8", errors="replace")
        class_counts, empty_labels, label_errors = Counter(), 0, []
        for name in labels:
            lines = archive.read(name).decode("utf-8").splitlines()
            if not lines:
                empty_labels += 1
            for line in lines:
                parts = line.split()
                if len(parts) != 5:
                    label_errors.append({"file": name, "error": "Expected five fields"})
                    continue
                try:
                    class_id = int(parts[0])
                    coords = [float(x) for x in parts[1:]]
                    if any(not 0 <= x <= 1 for x in coords) or coords[2] <= 0 or coords[3] <= 0:
                        label_errors.append({"file": name, "error": "Invalid normalized bbox"})
                    class_counts[class_id] += 1
                except ValueError:
                    label_errors.append({"file": name, "error": "Invalid number"})
        result = {
            "checked_date": "2026-10-28", "source": "https://www.kaggle.com/datasets/alanoudawaji/swimming-and-drowning-dataset",
            "download_url": URL, "archive": str(ARCHIVE), "bytes": ARCHIVE.stat().st_size,
            "sha256": digest.hexdigest(), "archive_entries": len(names), "images": len(images),
            "label_files": len(labels), "split_image_counts": dict(splits),
            "box_counts_by_class_id": dict(class_counts), "empty_label_files": empty_labels,
            "label_format_errors": label_errors, "metadata_files": metadata,
            "video_files": [n for n in names if n.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm"))],
            "sample_image_names": images[:30],
        }
    output = FOLDER / "alanoud_audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
