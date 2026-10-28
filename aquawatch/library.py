import json
from pathlib import Path
from . import store
from .settings import DATA, LIBRARY


def register_library():
    """Register reviewed clips only; raw research media is never exposed by this module."""
    manifest = DATA / "video_library.json"
    content = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {"videos": []}
    count = 0
    retained = set()
    for record in content.get("videos", []):
        if record.get("above_water") is not True:
            continue
        path = Path(record["path"]).resolve()
        if not path.is_relative_to((LIBRARY / "clips").resolve()) or not path.is_file():
            continue
        if record.get("url") != "/media/library/clips/" + path.name:
            continue
        item = {**record, "path": str(path), "view": "above_water_reviewed",
                "source": record.get("credit", "Thư viện video đã kiểm duyệt"),
                "category": record.get("scenario", "unknown"),
                "benchmark_role": record.get("camera_support", "secondary_motion_stress"),
                "library": True}
        existing = store.get("videos", record["id"])
        if existing != item:
            store.put("videos", item)
        count += 1
        retained.add(record["id"])
    for item in store.all_items("videos"):
        if item.get("library") and item["id"] not in retained:
            store.delete_library_video(item["id"])
    return count
