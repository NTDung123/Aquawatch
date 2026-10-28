import json
from aquawatch import library, store


def test_only_reviewed_clips_inside_library_can_be_registered(tmp_path, monkeypatch):
    clip_root = tmp_path / "library"
    (clip_root / "clips").mkdir(parents=True)
    (clip_root / "raw").mkdir()
    clip = clip_root / "clips" / "reviewed.mp4"
    clip.write_bytes(b"transport test")
    raw = clip_root / "raw" / "unreviewed.mp4"
    raw.write_bytes(b"transport test")
    monkeypatch.setattr(library, "DATA", tmp_path)
    monkeypatch.setattr(library, "LIBRARY", clip_root)
    monkeypatch.setattr(store, "DB", tmp_path / "test.sqlite3")
    records = [{"id": "good", "path": str(clip), "url": "/media/library/clips/reviewed.mp4", "above_water": True, "scenario": "normal_swimming"},
               {"id": "raw", "path": str(raw), "url": "/media/library/clips/unreviewed.mp4", "above_water": True},
               {"id": "not-reviewed", "path": str(clip), "url": "/media/library/clips/reviewed.mp4", "above_water": False}]
    (tmp_path / "video_library.json").write_text(json.dumps({"videos": records}), encoding="utf-8")
    assert library.register_library() == 1
    assert [v["id"] for v in store.all_items("videos")] == ["good"]
    assert store.get("videos", "good")["category"] == "normal_swimming"
    records[0]["above_water"] = False
    store.put("videos", {"id": "user-upload", "library": False})
    (tmp_path / "video_library.json").write_text(json.dumps({"videos": records}), encoding="utf-8")
    assert library.register_library() == 0
    assert store.get("videos", "good") is None
    assert store.get("videos", "user-upload") is not None
