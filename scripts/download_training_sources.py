"""Download public training-source archives with recorded provenance and hashes."""

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "mibugi": {
        "url": "https://raw.githubusercontent.com/Mibugi/Drowning-detection/a417d924b9d906dc50ab3078dd48b0c5c63a0f1c/datasets/Drowning%20Detect.v6-2000.yolov11.zip",
        "page": "https://github.com/Mibugi/Drowning-detection",
        "license": "CC BY 4.0 in embedded README.dataset.txt and data.yaml",
        "bytes": 101111276,
        "git_blob_sha1": "48ff50d2f5d9cf9fab7d08dee68d377d4848bc4b",
    },
    "alanoud": {
        "url": "https://www.kaggle.com/api/v1/datasets/download/alanoudawaji/swimming-and-drowning-dataset",
        "page": "https://www.kaggle.com/datasets/alanoudawaji/swimming-and-drowning-dataset",
        "license": "CC BY 4.0 in embedded README.dataset.txt and data.yaml",
        "bytes": 388922012,
        "sha256": "54b20dcb7c85c9bf717938e7a5f61c81fbd75ec0af35ffbcc93891ca1bd9f9b1",
    },
    "deeprescue": {
        "url": "https://www.kaggle.com/api/v1/datasets/download/deeprescue/drowning-dataset",
        "page": "https://www.kaggle.com/datasets/deeprescue/drowning-dataset",
        "license": "CC0 uploader declaration; underlying footage provenance unresolved",
        "bytes": 219926172,
    },
    "nvbangg": {
        "url": "https://www.kaggle.com/api/v1/datasets/download/nvbangg/drowning-test",
        "page": "https://www.kaggle.com/datasets/nvbangg/drowning-test",
        "license": "MIT uploader declaration; inspect archive and camera viewpoint before retaining data",
        "bytes": 42519810,
    },
}


def hashes(path):
    sha = hashlib.sha256()
    git = hashlib.sha1(b"blob " + str(path.stat().st_size).encode() + b"\0")
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
            git.update(block)
    return sha.hexdigest(), git.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="+", choices=list(SOURCES), default=["mibugi", "alanoud", "deeprescue", "nvbangg"])
    parser.add_argument("--direct", action="store_true", help="Bypass an unavailable local proxy for these public URLs")
    args = parser.parse_args()
    target = ROOT / "data" / "research"
    target.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if args.direct else urllib.request.build_opener()
    records = []
    for name in args.sources:
        source = SOURCES[name]
        path = target / (name + ".zip")
        record = {"name": name, **source, "archive": str(path), "checked_utc": datetime.now(timezone.utc).isoformat()}
        if not path.exists():
            temporary = path.with_suffix(".zip.part")
            for attempt in range(3):
                try:
                    request = urllib.request.Request(source["url"], headers={"User-Agent": "AquaWatch-academic-source-audit"})
                    with opener.open(request, timeout=90) as response, temporary.open("wb") as output:
                        while block := response.read(1024 * 1024):
                            output.write(block)
                    temporary.replace(path)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2)
            record["downloaded_now"] = True
        else:
            record["downloaded_now"] = False
        record["actual_bytes"] = path.stat().st_size
        record["actual_sha256"], record["actual_git_blob_sha1"] = hashes(path)
        if source.get("bytes") != record["actual_bytes"]:
            raise ValueError(f"Unexpected archive length for {name}")
        if source.get("sha256") and source["sha256"] != record["actual_sha256"]:
            raise ValueError(f"SHA-256 mismatch for {name}")
        if source.get("git_blob_sha1") and source["git_blob_sha1"] != record["actual_git_blob_sha1"]:
            raise ValueError(f"Pinned Git blob mismatch for {name}")
        records.append(record)
        print(json.dumps({"name": name, "bytes": record["actual_bytes"], "sha256": record["actual_sha256"],
                          "downloaded_now": record["downloaded_now"]}), flush=True)
    (target / "training_downloads.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
