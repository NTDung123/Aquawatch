"""Run real library clips through the local model and record descriptive alarm behavior."""
import argparse
import json
import time
from pathlib import Path
import httpx


def alarm_duration(samples, duration, minimum_level=2):
    total = 0.0
    for index, sample in enumerate(samples):
        if sample["level"] < minimum_level:
            continue
        end = samples[index + 1]["time"] if index + 1 < len(samples) else min(duration, sample["time"] + .2)
        total += max(0, end - sample["time"])
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confidence", type=float, default=.4)
    parser.add_argument("--sample-fps", type=float, default=5)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output file to preserve previous benchmarks")
    report = {"status": "running", "scope": "Descriptive outputs on independent local video sources; not clinical drowning accuracy.",
              "confidence": args.confidence, "sample_fps": args.sample_fps, "videos": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    save()
    with httpx.Client(base_url=args.base_url, trust_env=False, timeout=120) as client:
        response = client.get("/api/videos")
        response.raise_for_status()
        videos = [v for v in response.json() if v.get("library") and (not args.only or v["id"] in args.only)]
        for video in videos:
            response = client.post("/api/jobs", json={"video_id": video["id"], "mode": "batch", "sample_fps": args.sample_fps,
                                                     "confidence": args.confidence, "camera_mode": video["camera_mode"]})
            response.raise_for_status()
            job = response.json()
            deadline = time.monotonic() + max(300, video["duration"] * 3)
            while time.monotonic() < deadline:
                response = client.get(f"/api/jobs/{job['id']}")
                response.raise_for_status()
                job = response.json()
                if job["status"] not in ("queued", "running"):
                    break
                time.sleep(.5)
            if job["status"] != "completed":
                raise RuntimeError(job)
            response = client.get(f"/api/jobs/{job['id']}/analysis")
            response.raise_for_status()
            analysis = response.json()
            alarms = [e for e in analysis["events"] if e["level"] >= 2]
            report["videos"].append({"id": video["id"], "name": video["name"], "job_id": job["id"],
                                      "scenario": video.get("scenario"), "camera_support": video.get("camera_support"),
                                      "duration": video["duration"], "summary": analysis["summary"],
                                      "alarm_segments": len(alarms), "first_alarm_seconds": min((e["start"] for e in alarms), default=None),
                                      "alarm_seconds": round(alarm_duration(analysis["samples"], video["duration"]), 3),
                                      "source_url": video.get("source_url"), "source_group": video.get("source_group"),
                                      "source_annotations": video.get("observational_annotations", video.get("annotations", []))})
            save()
            print(json.dumps(report["videos"][-1], ensure_ascii=False), flush=True)
    report["status"] = "completed"
    report["limitations"] = ["Normal/background clips provide exploratory negative checks, not a population false-alarm rate.",
                              "Staged signs and rescue context do not prove a real medical drowning event.",
                              "Videos were not used in local fine-tuning or validation confidence selection.",
                              "Multiple clips share sources; do not count each clip as an independent recording."]
    save()


if __name__ == "__main__":
    main()
