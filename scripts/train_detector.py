"""Run an actual Ultralytics fine-tuning experiment on an audited dataset."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".work" / "ultralytics"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".work" / "matplotlib"))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="Directory built by audit_dataset.py")
    parser.add_argument("--model", type=Path, required=True, help="Existing local pretrained checkpoint")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--name", default="finetune_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--purpose", choices=["smoke", "experiment", "final_candidate"], default="experiment")
    parser.add_argument("--evaluate-test", action="store_true", help="Evaluate locked test split once; do not tune on it")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--amp", action="store_true", help="Enable mixed precision; Ultralytics may download a separate AMP-check model")
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--cctv-augment", action="store_true", help="Use modest geometry augmentation without vertical flipping")
    parser.add_argument("--optimizer", choices=["auto", "SGD", "Adam", "AdamW"], default="auto")
    parser.add_argument("--lr0", type=float, help="Explicit initial learning rate; requires a non-auto optimizer")
    args = parser.parse_args()
    dataset, model_path = args.dataset.resolve(), args.model.resolve()
    if not model_path.is_file():
        parser.error("--model must be an existing local checkpoint; no implicit model download is performed")
    if args.epochs < 1 or args.imgsz < 32 or args.batch < 1 or args.patience < 1:
        parser.error("epochs/batch must be positive and imgsz must be at least 32")
    if args.lr0 is not None and (not 0 < args.lr0 <= 1 or args.optimizer == "auto"):
        parser.error("Explicit lr0 must be in (0,1] and requires a named optimizer")
    try:
        audit = json.loads((dataset / "audit.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        parser.error(f"Missing/invalid dataset audit: {error}")
    if not audit.get("build_completed") or audit.get("errors"):
        parser.error("Dataset has not passed audit_dataset.py build")
    if not all(audit.get("split_counts", {}).get(split, 0) for split in ("train", "val")):
        parser.error("Nonempty train and validation splits are required")
    if args.evaluate_test and not audit.get("split_counts", {}).get("test", 0):
        parser.error("No locked test split exists in this audited dataset")
    configuration = json.loads((dataset / "data.yaml").read_text(encoding="utf-8"))
    if Path(configuration.get("path", "")).resolve() != dataset or configuration.get("names") != audit.get("classes"):
        parser.error("Dataset configuration does not match the audited root/classes")
    for split in ("train", "val", "test"):
        if split in configuration and configuration[split] != "images/" + split:
            parser.error("Dataset split paths must match the audited layout")
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest:
        image = (dataset / entry["curated_image"]).resolve()
        label = dataset / "labels" / entry["split"] / image.with_suffix(".txt").name
        if not image.is_relative_to(dataset) or not label.resolve().is_relative_to(dataset):
            parser.error("Manifest file escapes dataset root")
        if sha256(image) != entry["image_sha256"] or sha256(label) != entry["label_sha256"]:
            parser.error("Dataset bytes changed after audit; create a new reviewed dataset version")
    project = ROOT / "data" / "training"
    run = project / args.name
    if run.exists():
        parser.error("Run directory exists; choose a new --name to preserve previous evidence")
    import torch
    from ultralytics import YOLO
    from runtime_threads import configure_image_cache_threads

    configure_image_cache_threads()

    device = ("0" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    record = {"status": "running", "started_utc": now(), "purpose": args.purpose,
              "argv": sys.argv, "python": sys.version, "platform": platform.platform(),
              "packages": {name: importlib.metadata.version(name) for name in ("torch", "torchvision", "ultralytics", "numpy")},
              "cuda_available": torch.cuda.is_available(), "torch_cuda": torch.version.cuda,
              "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
              "image_cache_executor": "concurrent.futures.ThreadPoolExecutor; image/label verification unchanged",
              "dataset": str(dataset), "audit_sha256": sha256(dataset / "audit.json"),
              "manifest_sha256": sha256(dataset / "manifest.json"), "base_model": str(model_path),
              "base_model_sha256": sha256(model_path), "seed": args.seed,
              "data_config_sha256": sha256(dataset / "data.yaml"),
              "split_counts": audit["split_counts"], "group_split": audit["group_split"],
              "limitations": ["Short smoke training proves optimization ran, not detection quality.",
                              "Validation mAP on images is not event-level drowning accuracy.",
                              "Data provenance limitations remain as documented in the dataset audit."]}
    run.mkdir(parents=True)

    def save_record():
        (run / "training_record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    save_record()
    try:
        model = YOLO(str(model_path))
        augmentation = ({"degrees": 3, "translate": .05, "scale": .25, "flipud": 0,
                         "fliplr": .5, "mosaic": .25, "mixup": 0, "close_mosaic": 8}
                        if args.cctv_augment else {})
        optimization = {"optimizer": args.optimizer}
        if args.lr0 is not None:
            optimization["lr0"] = args.lr0
        result = model.train(data=str(dataset / "data.yaml"), epochs=args.epochs, imgsz=args.imgsz,
                             batch=args.batch, device=device, workers=0, project=str(project), name=args.name,
                             exist_ok=True, seed=args.seed, deterministic=True, patience=args.patience,
                             pretrained=True, cache=False, amp=args.amp and device != "cpu", plots=True,
                             save=True, verbose=True, **augmentation, **optimization)
        best = run / "weights" / "best.pt"
        last = run / "weights" / "last.pt"
        if not best.is_file() or not last.is_file() or not (run / "results.csv").is_file():
            raise RuntimeError("Training did not produce required checkpoints and optimizer metrics")
        record["validation_metrics"] = getattr(result, "results_dict", {})
        record["best_model"] = str(best)
        record["best_model_sha256"] = sha256(best)
        record["last_model_sha256"] = sha256(last)
        record["weights_file_differs_from_base"] = record["best_model_sha256"] != record["base_model_sha256"]
        if args.evaluate_test:
            evaluation = YOLO(str(best)).val(data=str(dataset / "data.yaml"), split="test", imgsz=args.imgsz,
                                             batch=args.batch, device=device, workers=0,
                                             project=str(project), name=args.name + "_test", plots=True)
            record["test_metrics"] = evaluation.results_dict
        record["status"] = "completed"
        record["finished_utc"] = now()
        save_record()
        print(json.dumps({"status": record["status"], "record": str(run / "training_record.json"),
                          "best_model": str(best), "purpose": args.purpose}))
    except Exception as error:
        record.update(status="failed", finished_utc=now(), error=str(error))
        save_record()
        raise


if __name__ == "__main__":
    main()
