"""Download official generic COCO initialization; preserve source and actual hashes."""
import hashlib
import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amp-check", action="store_true")
    args = parser.parse_args()
    destination = ROOT / "models" / "base" / "yolov8s_coco.pt"
    url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s.pt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=120) as response, destination.with_suffix(".part").open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        destination.with_suffix(".part").replace(destination)
    record = {"path": str(destination.relative_to(ROOT)), "url": url, "release": "v8.3.0",
              "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "bytes": destination.stat().st_size,
              "license": "Ultralytics AGPL-3.0", "role": "generic COCO initialization, not a drowning detector",
              "scope": "No drowning-specific images from the community checkpoint are used for this initialization. Generic pretraining is distinct from the reviewed project fine-tuning data."}
    (ROOT / "data" / "base_model_manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    if record["sha256"] != "1f47a78bf100391c2a140b7ac73a1caae18c32779be7d310658112f7ac9aa78a":
        raise RuntimeError("Official COCO checkpoint differs from pinned checksum")
    print(json.dumps(record))
    if args.amp_check:
        target = ROOT / "weights" / "yolo26n.pt"
        target.parent.mkdir(parents=True, exist_ok=True)
        amp_url = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt"
        if not target.exists():
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(amp_url, timeout=120) as response, target.with_suffix(".part").open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            target.with_suffix(".part").replace(target)
        checksum = hashlib.sha256(target.read_bytes()).hexdigest()
        if checksum != "9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef":
            raise RuntimeError("AMP numerical-check model differs from pinned checksum")
        print(json.dumps({"role": "AMP numerical check only; not training initialization", "path": str(target), "sha256": checksum}))


if __name__ == "__main__":
    main()
