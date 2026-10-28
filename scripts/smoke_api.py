"""Exercise the real local upload/inference/export/ack workflow on a supplied video."""
import argparse
import json
import time
from pathlib import Path
import httpx

parser = argparse.ArgumentParser()
parser.add_argument("video", type=Path)
parser.add_argument("--base-url", default="http://127.0.0.1:8000")
parser.add_argument("--output", type=Path, default=Path("data/live_smoke.json"))
parser.add_argument("--fps", type=float, default=5)
args = parser.parse_args()
with httpx.Client(base_url=args.base_url, timeout=180, trust_env=False) as client:
    status = client.get("/api/status")
    status.raise_for_status()
    with args.video.open("rb") as stream:
        response = client.post("/api/videos", files={"file": (args.video.name, stream, "video/mp4")},
                               data={"above_water": "true", "camera_mode": "ptz", "environment": "beach"})
    response.raise_for_status()
    video = response.json()
    response = client.post("/api/jobs", json={"video_id": video["id"], "camera_mode": "ptz", "sample_fps": args.fps, "water_polygon": [], "confidence": .4})
    response.raise_for_status()
    job = response.json()
    print("job", job["id"], flush=True)
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        response = client.get("/api/jobs/" + job["id"])
        response.raise_for_status()
        job = response.json()
        print(job["status"], round(job["progress"] * 100), flush=True)
        if job["status"] not in ("queued", "running"):
            break
        time.sleep(3)
    if job["status"] != "completed":
        raise RuntimeError(job)
    response = client.get(f"/api/jobs/{job['id']}/analysis")
    response.raise_for_status()
    analysis = response.json()
    checks = {"upload": True, "analysis": True, "samples": len(analysis["samples"])}
    for format in ("json", "csv"):
        response = client.get(f"/api/jobs/{job['id']}/export", params={"format": format})
        response.raise_for_status()
        checks["export_" + format] = len(response.content)
    if analysis["events"]:
        event = analysis["events"][0]
        response = client.post(f"/api/jobs/{job['id']}/events/{event['id']}/ack", json={"note": "Kiểm thử API local; không có can thiệp cứu hộ tự động."})
        response.raise_for_status()
        checks["acknowledged"] = response.json()["acknowledged"]
        response = client.get(event["evidence_url"])
        response.raise_for_status()
        checks["evidence_bytes"] = len(response.content)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"system": status.json(), "job": job, "checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"id": job["id"], "summary": job["summary"], "checks": checks}, ensure_ascii=False), flush=True)
