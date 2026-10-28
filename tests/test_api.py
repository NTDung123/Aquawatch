import csv
import io
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aquawatch import api, jobs, store


@pytest.fixture
def isolated_client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "register_library", lambda: 0)
    videos = tmp_path / "videos"
    results = tmp_path / "results"
    videos.mkdir()
    results.mkdir()
    model = tmp_path / "unused-test-checkpoint.pt"
    model.touch()
    monkeypatch.setattr(store, "DB", tmp_path / "isolated.sqlite3")
    monkeypatch.setattr(api, "VIDEOS", videos)
    monkeypatch.setattr(api, "RESULTS", results)
    monkeypatch.setattr(api, "MODEL", model)
    for route in api.app.routes:
        if getattr(route, "path", None) == "/media/videos":
            monkeypatch.setattr(route.app, "directory", str(videos))
            monkeypatch.setattr(route.app, "all_directories", [str(videos)])
    with TestClient(api.app) as client:
        yield client, videos, results


def seed_video(videos):
    video_id = "1" * 32
    path = videos / f"{video_id}.mp4"
    path.write_bytes(bytes(range(256)))
    item = {
        "id": video_id,
        "name": "transport-test.mp4",
        "path": str(path),
        "url": f"/media/videos/{path.name}",
        "duration": 1.0,
        "width": 320,
        "height": 180,
        "fps": 5.0,
        "frames": 5,
        "view": "above_water_declared_by_user",
    }
    store.put("videos", item)
    return item


def seed_completed(videos, results):
    video = seed_video(videos)
    job_id, event_id = "2" * 32, "3" * 32
    job = {"id": job_id, "status": "completed", "video": video, "config": {}, "progress": 1}
    store.put("jobs", job)
    folder = results / job_id
    folder.mkdir()
    result = {
        "duration": 1.0,
        "samples": [],
        "events": [{"id": event_id, "track_id": 1, "start": .2, "end": .8,
                    "level": 1, "confidence": None, "inferred": True,
                    "reasons": ["Test transport; not inference output"], "acknowledged": False}],
        "summary": {"accuracy": None},
    }
    (folder / "analysis.json").write_text(json.dumps(result), encoding="utf-8")
    return job_id, event_id


@pytest.mark.parametrize("declaration", [None, "false"])
def test_upload_requires_explicit_above_water(isolated_client, declaration):
    client, videos, _ = isolated_client
    data = {} if declaration is None else {"above_water": declaration}
    response = client.post("/api/videos", data=data, files={"file": ("clip.mp4", b"test", "video/mp4")})
    assert response.status_code == 422
    assert list(videos.iterdir()) == []
    assert store.all_items("videos") == []


def test_upload_rejects_disallowed_format(isolated_client):
    client, videos, _ = isolated_client
    response = client.post("/api/videos", data={"above_water": "true"}, files={"file": ("payload.html", b"test", "text/html")})
    assert response.status_code == 415
    assert list(videos.iterdir()) == []


def test_invalid_video_does_not_leave_orphan_file(isolated_client):
    client, videos, _ = isolated_client
    response = client.post("/api/videos", data={"above_water": "true"}, files={"file": ("invalid.mp4", b"not a video", "video/mp4")})
    assert response.status_code == 422
    assert list(videos.iterdir()) == []
    assert store.all_items("videos") == []


def test_upload_sanitizes_filename_and_keeps_private_path_private(isolated_client, monkeypatch):
    client, videos, _ = isolated_client
    monkeypatch.setattr(jobs, "probe", lambda path: {"fps": 5, "frames": 5, "duration": 1, "width": 320, "height": 180})
    response = client.post("/api/videos", data={"above_water": "true", "camera_mode": "ptz", "environment": "beach"},
                           files={"file": ("../../outside\\clip.mp4", b"transport fixture", "video/mp4")})
    assert response.status_code == 201
    item = response.json()
    assert item["name"] == "clip.mp4"
    assert re.fullmatch("[0-9a-f]{32}", item["id"])
    assert "path" not in item
    saved = store.get("videos", item["id"])
    assert Path(saved["path"]).parent == videos
    assert saved["camera_mode"] == "ptz"
    assert saved["environment"] == "beach"
    assert saved["view"] == "above_water_declared_by_user"


def test_media_range_supports_seeking_and_rejects_invalid_range(isolated_client):
    client, videos, _ = isolated_client
    item = seed_video(videos)
    response = client.get(item["url"], headers={"Range": "bytes=10-29"})
    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 10-29/256"
    assert response.content == bytes(range(10, 30))
    assert client.get(item["url"], headers={"Range": "bytes=999-1000"}).status_code == 416


def test_media_cannot_escape_video_directory(isolated_client, tmp_path):
    client, _, _ = isolated_client
    (tmp_path / "secret.txt").write_text("private-test-data", encoding="utf-8")
    response = client.get("/media/videos/%2e%2e/secret.txt")
    assert response.status_code == 404
    assert b"private-test-data" not in response.content


@pytest.mark.parametrize("payload", [
    {"sample_fps": 0}, {"sample_fps": 11}, {"confidence": .1}, {"confidence": 1.1},
    {"camera_mode": "handheld"}, {"water_polygon": [[.1, .1], [.9, .9]]},
    {"water_polygon": [[.1, .1], [1.1, .9], [.2, .5]]},
])
def test_job_configuration_rejects_invalid_values(isolated_client, payload):
    client, _, _ = isolated_client
    response = client.post("/api/jobs", json={"video_id": "not-present", **payload})
    assert response.status_code == 422


def test_missing_video_returns_404_without_starting_worker(isolated_client, monkeypatch):
    client, _, _ = isolated_client
    monkeypatch.setattr(jobs, "submit", lambda *args: pytest.fail("No background worker may be started"))
    assert client.post("/api/jobs", json={"video_id": "missing"}).status_code == 404


def test_busy_job_rejects_second_submission(isolated_client, monkeypatch):
    client, videos, _ = isolated_client
    video = seed_video(videos)
    store.put("jobs", {"id": "busy", "status": "running", "video": video})
    monkeypatch.setattr(jobs, "submit", lambda *args: pytest.fail("No background worker may be started"))
    assert client.post("/api/jobs", json={"video_id": video["id"]}).status_code == 409


def test_job_submission_preserves_config_and_redacts_path(isolated_client, monkeypatch):
    client, videos, _ = isolated_client
    video = seed_video(videos)

    def no_inference_submit(source, config):
        job = {"id": "transport-job", "status": "queued", "video": source, "config": config}
        store.put("jobs", job)
        return job

    monkeypatch.setattr(jobs, "submit", no_inference_submit)
    polygon = [[.1, .1], [.8, .1], [.8, .8]]
    response = client.post("/api/jobs", json={"video_id": video["id"], "camera_mode": "ptz", "sample_fps": 3,
                                            "confidence": .5, "water_polygon": polygon})
    assert response.status_code == 202
    result = response.json()
    assert "path" not in result["video"]
    assert result["config"]["water_polygon"] == polygon
    assert result["config"]["camera_mode"] == "ptz"
    assert result["config"]["sample_fps"] == 3
    assert client.get("/api/jobs/transport-job").json()["config"] == result["config"]


def test_acknowledgment_persists_in_history_and_exports(isolated_client):
    client, videos, results = isolated_client
    job_id, event_id = seed_completed(videos, results)
    endpoint = f"/api/jobs/{job_id}"
    assert client.get(endpoint + "/analysis").json()["events"][0]["acknowledged"] is False
    response = client.post(endpoint + f"/events/{event_id}/ack", json={"note": "Reviewed; not a safety conclusion"})
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True
    assert response.json()["acknowledged_at"]
    event = client.get(endpoint + "/analysis").json()["events"][0]
    assert event["acknowledged"] is True
    assert event["note"] == "Reviewed; not a safety conclusion"
    exported = client.get(endpoint + "/export?format=json")
    assert exported.status_code == 200
    assert exported.json()["events"][0]["acknowledged"] is True
    csv_response = client.get(endpoint + "/export?format=csv")
    rows = list(csv.DictReader(io.StringIO(csv_response.content.decode("utf-8-sig"))))
    assert rows[0]["acknowledged"] == "True"
    assert rows[0]["confidence"] == ""
    assert client.post(endpoint + "/events/missing/ack", json={}).status_code == 404


def test_pending_analysis_and_invalid_evidence_paths_are_rejected(isolated_client):
    client, videos, _ = isolated_client
    video = seed_video(videos)
    job_id = "4" * 32
    store.put("jobs", {"id": job_id, "status": "running", "video": video})
    assert client.get(f"/api/jobs/{job_id}/analysis").status_code == 409
    assert client.get(f"/media/results/{job_id}/analysis.json").status_code == 404
    assert client.get("/media/results/not-a-job/" + "5" * 32 + ".jpg").status_code == 404
