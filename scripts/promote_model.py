"""Install a measured candidate locally while preserving the previous deployment."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--preprocessing", choices=["letterbox", "stretch640"], default="letterbox")
    args = parser.parse_args()
    record = json.loads((args.run / "training_record.json").read_text(encoding="utf-8"))
    comparison = json.loads(args.comparison.read_text(encoding="utf-8"))
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    candidate = args.run / "weights" / "best.pt"
    checksum = digest(candidate)
    if record.get("status") != "completed" or record.get("best_model_sha256") != checksum:
        parser.error("Training is incomplete or the checkpoint checksum changed")
    if comparison.get("status") != "completed" or comparison.get("split") != "val":
        parser.error("A completed validation comparison is required")
    if comparison["models"]["candidate"]["sha256"] != checksum or calibration.get("model_sha256") != checksum:
        parser.error("Validation/calibration do not refer to the same candidate")
    base = comparison["models"]["baseline"]["metrics"]
    new = comparison["models"]["candidate"]["metrics"]
    if new["metrics/mAP50-95(B)"] < base["metrics/mAP50-95(B)"]:
        parser.error("Candidate did not improve the validation mAP50-95; retain the current deployment")
    per_class = comparison["models"]
    base_risk = next(c for c in per_class["baseline"]["per_class"] if c["class_id"] == 0)
    new_risk = next(c for c in per_class["candidate"]["per_class"] if c["class_id"] == 0)
    if new_risk["mAP50"] < base_risk["mAP50"]:
        parser.error("Candidate regressed validation drowning AP50; retain the current deployment")
    target = ROOT / "models" / "finetuned" / "weights" / "best.pt"
    deployed_record = ROOT / "data" / "training_record.json"
    if target.exists():
        history = ROOT / "models" / "history" / digest(target)
        history.mkdir(parents=True, exist_ok=True)
        if not (history / "best.pt").exists():
            shutil.copy2(target, history / "best.pt")
        if deployed_record.exists() and not (history / "training_record.json").exists():
            shutil.copy2(deployed_record, history / "training_record.json")
    record["deployment"] = {"run_name": args.run.name, "display_name": "YOLOv8s · " + args.run.name,
                            "validation_comparison": str(args.comparison.resolve()),
                            "confidence_calibration": str(args.calibration.resolve()),
                            "recommended_confidence": calibration["selected_confidence"],
                            "preprocessing": args.preprocessing,
                            "quality_validated_for_rescue": False}
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    shutil.copy2(candidate, temporary)
    if digest(temporary) != checksum:
        parser.error("Copy checksum failed; old deployment retained")
    temporary.replace(target)
    temp_record = deployed_record.with_suffix(".tmp")
    temp_record.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_record.replace(deployed_record)
    print(json.dumps({"installed": str(target), "sha256": checksum, "confidence": calibration["selected_confidence"]}))


if __name__ == "__main__":
    main()
