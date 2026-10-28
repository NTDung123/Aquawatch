import os
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VIDEOS = DATA / "videos"
RESULTS = DATA / "results"
LIBRARY = DATA / "library"
MODEL = ROOT / "models" / "drowning_yolov8s.pt"
for directory in (VIDEOS, RESULTS, LIBRARY / "clips", LIBRARY / "posters", ROOT / ".work", ROOT / ".work" / "matplotlib"):
    directory.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".work"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".work" / "matplotlib"))
os.environ.setdefault("YOLO_AUTOINSTALL", "false")

MODEL_SHA256 = "6e8094468fa0294887a930bf18db9e7c5989a74d5e3c1753ec21c4d742e72c29"


def selected_model():
    trained = ROOT / "models" / "finetuned" / "weights" / "best.pt"
    record_path = DATA / "training_record.json"
    if trained.is_file() and record_path.is_file():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("status") == "completed" and hashlib.sha256(trained.read_bytes()).hexdigest() == record.get("best_model_sha256"):
            return trained
    return MODEL
