"""Verify real HTTP partial results, source pacing, media range, and cancellation."""
import argparse
import json
import time
from pathlib import Path
import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("data/realtime_verification.json"))
    parser.add_argument("--video-id", default="pool_normal_orient_15s")
    parser.add_argument("--confidence", type=float, default=.4)
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, trust_env=False, timeout=90) as client:
        catalog = client.get("/api/videos")
        catalog.raise_for_status()
        video = next(v for v in catalog.json() if v["id"] == args.video_id)
        media = client.get(video["url"], headers={"Range": "bytes=0-1023"})
        assert media.status_code == 206 and len(media.content) == 1024
        response = client.post("/api/jobs", json={"video_id": video["id"], "mode": "realtime", "sample_fps": 5,
                                                 "confidence": args.confidence, "camera_mode": video["camera_mode"]})
        response.raise_for_status()
        job = response.json()
        observations, partial_seen, last_count = [], False, 0
        started = time.monotonic()
        while time.monotonic() - started < max(180, video["duration"] * 3):
            state = client.get(f"/api/jobs/{job['id']}")
            state.raise_for_status()
            job = state.json()
            response = client.get(f"/api/jobs/{job['id']}/analysis")
            if response.status_code == 200:
                result = response.json()
                count = len(result["samples"])
                assert count >= last_count
                last_count = count
                frontier, source_elapsed = result.get("processed_until"), result.get("source_elapsed_seconds", 0)
                if frontier is not None:
                    assert frontier <= source_elapsed + .02, (frontier, source_elapsed)
                    assert all(s["time"] <= frontier for s in result["samples"])
                    assert all(e["start"] <= frontier for e in result["events"])
                    if job["status"] == "running" and count > 0:
                        partial_seen = True
                    observations.append({"wall_seconds": round(time.monotonic() - started, 3),
                                         "state": job["status"], "sample_count": count, "frontier": frontier,
                                         "source_elapsed_seconds": source_elapsed})
            elif response.status_code != 409:
                response.raise_for_status()
            if job["status"] not in ("running", "queued"):
                break
            time.sleep(.35)
        assert job["status"] == "completed", job
        assert partial_seen
        assert result["partial"] is False
        assert observations[-1]["source_elapsed_seconds"] >= result["samples"][-1]["time"]
        first_job = job
        # Cancellation must retain a truthful processed prefix instead of pretending the clip finished.
        response = client.post("/api/jobs", json={"video_id": video["id"], "mode": "realtime", "sample_fps": 5})
        response.raise_for_status()
        cancelled_job = response.json()
        time.sleep(1.2)
        client.post(f"/api/jobs/{cancelled_job['id']}/cancel").raise_for_status()
        for _ in range(60):
            cancelled_job = client.get(f"/api/jobs/{cancelled_job['id']}").json()
            if cancelled_job["status"] not in ("queued", "running"):
                break
            time.sleep(.1)
        assert cancelled_job["status"] == "cancelled", cancelled_job
        partial = client.get(f"/api/jobs/{cancelled_job['id']}/analysis").json()
        assert partial["partial"] is True and partial["processed_until"] < video["duration"]
        record = {"video": video, "job": first_job, "partial_results_seen_while_running": partial_seen,
                  "observations": observations, "range_status": media.status_code,
                  "cancelled_job": cancelled_job, "cancelled_frontier": partial["processed_until"],
                  "scope": "Real model/video HTTP and source-time causality test; not recognition accuracy or browser UI verification."}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"job": first_job["id"], "partial_seen": partial_seen, "summary": first_job["summary"],
                          "cancelled_job": cancelled_job["id"], "cancelled_frontier": partial["processed_until"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
