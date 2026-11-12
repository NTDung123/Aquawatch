"""Verify the bundled fine-tuned checkpoint; download optional reference assets explicitly."""
import hashlib
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ASSETS = [
    {
        "path": "models/drowning_yolov8s.pt",
        "url": "https://huggingface.co/Bagsangbin/yolo8s-drowning-detection/resolve/399ad3be040da0a0d7e0b4b2828bcc53177d42e6/yolo8s_drowning_detect.pt",
        "sha256": "6e8094468fa0294887a930bf18db9e7c5989a74d5e3c1753ec21c4d742e72c29",
        "source": "https://huggingface.co/Bagsangbin/yolo8s-drowning-detection",
        "license": "AGPL-3.0 as declared in repository metadata",
        "limitations": "Training dataset, camera viewpoints, independent metrics and overlap with external videos are not documented by the model card.",
    },
    {
        "path": "data/examples/usbp_rescue_imperial_beach_2021.mp4",
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2109/DOD_108554715/DOD_108554715-1024x576-1769k.mp4",
        "source": "https://www.dvidshub.net/video/812817/usbp-rescues-drowning-man",
        "license": "DVIDS marks PUBLIC DOMAIN; see https://www.dvidshub.net/about/copyright",
        "credit": "Matthew Dyman / U.S. Customs and Border Protection, 2021-09-01, VIRIN 210901-H-DO456-0701",
        "limitations": "Rescue footage; not a labelled benchmark. Camera motion/viewpoints require visual review. Absence from checkpoint training is not verified.",
    },
]


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def verify_finetuned():
    checkpoint = ROOT / "models/finetuned/weights/best.pt"
    record_path = ROOT / "data/training_record.json"
    if not checkpoint.is_file() or not record_path.is_file():
        raise RuntimeError("Bundled fine-tuned checkpoint or training record is missing. Re-download the full repository, or explicitly use --baseline for the community model.")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    checksum = digest(checkpoint)
    if record.get("status") != "completed" or checksum != record.get("best_model_sha256"):
        raise RuntimeError("Fine-tuned checkpoint does not match its completed training record. Restore both files from the same repository revision.")
    print(f"Verified fine-tuned checkpoint: {checkpoint.stat().st_size} bytes, SHA256 {checksum}")
    return {"path": checkpoint.relative_to(ROOT).as_posix(), "sha256": checksum,
            "bytes": checkpoint.stat().st_size, "source": "Bundled locally fine-tuned checkpoint and matching data/training_record.json",
            "preprocessing": record.get("deployment", {}).get("preprocessing", "letterbox"),
            "limitations": "Academic research model; image validation is not independent event-level rescue accuracy."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true", help="Explicitly download the pinned community baseline. The app still prefers a valid bundled fine-tuned checkpoint.")
    parser.add_argument("--example-video", action="store_true", help="Also download the historical public-domain beach rescue reference; it is not a reviewed pool CCTV library item.")
    parser.add_argument("--research-data", action="store_true", help="Also download the three research archives; they are not automatically approved training inputs.")
    args = parser.parse_args()
    assets, records = [], []
    if args.baseline:
        assets.append(ASSETS[0])
        try:
            records.append(verify_finetuned())
        except (OSError, ValueError, RuntimeError) as error:
            print(f"Using explicitly requested community fallback: {error}")
    else:
        records.append(verify_finetuned())
    if args.example_video:
        assets.append(ASSETS[1])
    if args.research_data:
        catalog = json.loads((ROOT / "docs/sources.json").read_text(encoding="utf-8"))
        for entry in catalog["downloaded_research_archives"]:
            assets.append({"path": entry["local_path"], "url": entry["download_url"], "sha256": entry["sha256"], "source": entry["url"], "license": entry["license_declared"], "limitations": entry["status"]})
    opener = urllib.request.build_opener()
    for asset in assets:
        destination = ROOT / asset["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_suffix(destination.suffix + ".part")
            request = urllib.request.Request(asset["url"], headers={"User-Agent": "AquaWatch-academic/1.0"})
            with opener.open(request, timeout=90) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if asset.get("sha256") and digest(temporary) != asset["sha256"]:
                raise RuntimeError(f"Checksum mismatch: {asset['path']}")
            temporary.replace(destination)
        checksum = digest(destination)
        if asset.get("sha256") and checksum != asset["sha256"]:
            raise RuntimeError(f"Checksum mismatch: {asset['path']}")
        records.append({**asset, "sha256": checksum, "bytes": destination.stat().st_size})
        print(f"Verified {asset['path']}: {destination.stat().st_size} bytes, SHA256 {checksum}")
    manifest = ROOT / "data" / "asset_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"checked_utc": datetime.now(timezone.utc).isoformat(), "assets": records}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
