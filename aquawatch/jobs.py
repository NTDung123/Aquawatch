import json
import hashlib
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import cv2
import numpy as np
from . import store
from .settings import RESULTS, selected_model
from .risk import RiskEngine
from .vision import CameraMotion, VisionEngine

POOL = ThreadPoolExecutor(max_workers=1)
CANCELLED = set()
LOCK = threading.Lock()
ENGINE = None


def probe(path):
    cap = cv2.VideoCapture(str(path))
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ok, frame = cap.read()
        if not ok or fps <= 0 or count <= 0:
            raise ValueError("Video không giải mã được hoặc thiếu FPS/thời lượng.")
        h, w = frame.shape[:2]
        duration = count / fps
        if duration > 1800:
            raise ValueError("Mỗi video MVP tối đa 30 phút; hãy cắt đoạn cần phân tích.")
        return {"fps": fps, "frames": count, "duration": duration, "width": w, "height": h}
    finally:
        cap.release()


def submit(video, config):
    job = {"id": uuid.uuid4().hex, "status": "queued", "progress": 0, "video": video,
           "config": config, "created_at": store.now(), "summary": None, "error": None,
           "processed_until": None, "source_elapsed_seconds": 0}
    store.put("jobs", job)
    POOL.submit(run, job)
    return job


def write_analysis(folder, result):
    temp = folder / "analysis.tmp"
    temp.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    for attempt in range(5):
        try:
            temp.replace(folder / "analysis.json")
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.02)


def pace_sample(job_id, timestamp, stream_started, clock=None, sleeper=None):
    clock, sleeper = clock or time.perf_counter, sleeper or time.sleep
    while job_id not in CANCELLED:
        remaining = stream_started + timestamp - clock()
        if remaining <= 0:
            return True
        sleeper(min(.1, remaining))
    return False


def evidence(frame, detections, path):
    image = frame.copy()
    h, w = image.shape[:2]
    for detection in detections:
        if detection.get("inferred"):
            continue
        coords = [int(v * (w if i % 2 == 0 else h)) for i, v in enumerate(detection["box"])]
        color = (55, 55, 235) if detection["level"] >= 2 else (0, 190, 240)
        cv2.rectangle(image, tuple(coords[:2]), tuple(coords[2:]), color, 3)
        cv2.putText(image, f"T{detection['track_id']} L{detection['level']}", (coords[0], max(20, coords[1] - 8)), cv2.FONT_HERSHEY_SIMPLEX, .7, color, 2)
    cv2.imwrite(str(path), image)


def run(job, clock=None, sleeper=None):
    global ENGINE
    clock, sleeper = clock or time.perf_counter, sleeper or time.sleep
    folder = RESULTS / job["id"]
    folder.mkdir(exist_ok=True)
    cap = None
    mode = job["config"].get("mode", "batch")
    result = {"samples": [], "events": [], "duration": job["video"]["duration"], "summary": {},
              "mode": mode, "partial": True, "state": "running", "processed_until": None,
              "source_elapsed_seconds": 0, "updated_at": store.now()}
    started = clock()
    stream_started = None
    last_snapshot = started
    try:
        job.update(status="running", started_at=store.now())
        store.put("jobs", job)
        write_analysis(folder, result)
        model_load_started = clock()
        desired_path = selected_model()
        desired_sha = hashlib.sha256(desired_path.read_bytes()).hexdigest()
        if ENGINE is None or ENGINE.path != desired_path or ENGINE.sha256 != desired_sha:
            ENGINE = VisionEngine()
        model_load_seconds = clock() - model_load_started
        config, video = job["config"], job["video"]
        cap = cv2.VideoCapture(video["path"])
        if not cap.isOpened():
            raise RuntimeError("Không mở được video nguồn; chưa có frame nào được phân tích.")
        stride = max(1, round(video["fps"] / config["sample_fps"]))
        engine = RiskEngine(config["water_polygon"], video["fps"] / stride)
        motion = CameraMotion(config["water_polygon"])
        index, previous_boxes, active_events = 0, [], {}
        inference_start, rejected_start = len(ENGINE.inference_ms), ENGINE.rejected
        cuts = pans = 0
        stream_started = clock()
        job["stream_started_at"] = store.now()
        while True:
            ok = cap.grab()
            if not ok:
                if index == 0 or not result["samples"]:
                    raise RuntimeError("Video không giải mã được frame nào; không tạo kết quả hoàn tất giả.")
                if index + max(2, int(video["frames"] * .005)) < video["frames"]:
                    raise RuntimeError(f"Video kết thúc/giải mã lỗi sớm tại frame {index}/{video['frames']}; chỉ có kết quả từng phần.")
                break
            if job["id"] in CANCELLED:
                job["status"] = "cancelled"
                break
            if index % stride:
                index += 1
                continue
            timestamp = index / video["fps"]
            if mode == "realtime" and not pace_sample(job["id"], timestamp, stream_started, clock, sleeper):
                job["status"] = "cancelled"
                break
            ok, frame = cap.retrieve()
            if not ok:
                raise RuntimeError(f"Không giải mã được frame {index}.")
            movement = motion.update(frame, previous_boxes)
            detections = ENGINE.predict(frame, config["confidence"])
            tracked = engine.update(timestamp, detections, movement["camera_moving"], movement["scene_cut"], movement["motion_known"])
            previous_boxes = [d["box"] for d in detections]
            cuts += int(movement["scene_cut"])
            pans += int(movement["camera_moving"])
            sample = {"time": round(timestamp, 4), "detections": tracked,
                      "level": max((d["level"] for d in tracked), default=0), **movement,
                      "missing_inference_enabled": engine.visibility_valid and bool(config["water_polygon"]) and movement["motion_known"]}
            result["samples"].append(sample)
            result["processed_until"] = sample["time"]
            result["source_elapsed_seconds"] = round(clock() - stream_started, 3)
            current = set()
            for d in tracked:
                if not d["level"]:
                    continue
                key = (d["track_id"], d["level"], d["inferred"])
                current.add(key)
                if key not in active_events:
                    event_id = uuid.uuid4().hex
                    image_name = event_id + ".jpg"
                    evidence(frame, [d], folder / image_name)
                    event = {"id": event_id, "track_id": d["track_id"], "start": sample["time"], "end": sample["time"],
                             "level": d["level"], "reasons": d["reasons"], "confidence": d["confidence"],
                             "inferred": d["inferred"], "acknowledged": False,
                             "evidence_url": f"/media/results/{job['id']}/{image_name}"}
                    result["events"].append(event)
                    active_events[key] = event
                active_events[key]["end"] = sample["time"]
            # Keep an episode across a short detector gap, without filling that gap with boxes.
            active_events = {k: e for k, e in active_events.items() if sample["time"] - e["end"] <= 1.0}
            if clock() - last_snapshot >= .5 or len(result["samples"]) == 1:
                job["progress"] = min(.999, (index + 1) / video["frames"])
                job["processed_until"] = sample["time"]
                job["source_elapsed_seconds"] = result["source_elapsed_seconds"]
                result["updated_at"] = store.now()
                result["summary"] = {"samples": len(result["samples"]), "events": len(result["events"]),
                                     "processing_seconds": round(clock() - started, 3), "provisional": True,
                                     "accuracy": None}
                job["summary"] = result["summary"]
                write_analysis(folder, result)
                store.put("jobs", job)
                last_snapshot = clock()
            index += 1
        timings = ENGINE.inference_ms[inference_start:]
        elapsed = clock() - started
        result["summary"] = {"samples": len(result["samples"]), "detections": sum(len(s["detections"]) for s in result["samples"]),
                             "events": len(result["events"]), "max_level": max((s["level"] for s in result["samples"]), default=0),
                             "processing_seconds": round(elapsed, 3), "sample_throughput_fps": round(len(timings) / max(.001, elapsed), 2),
                             "inference_seconds": round(sum(timings) / 1000, 3), "mode": mode,
                             "model_load_seconds": round(model_load_seconds, 3),
                             "source_processing_seconds": round(clock() - stream_started, 3),
                             "effective_sample_fps": round(video["fps"] / stride, 3), "provisional": job["status"] == "cancelled",
                             "mean_inference_ms": round(float(np.mean(timings)), 2) if timings else None,
                             "p95_inference_ms": round(float(np.percentile(timings, 95)), 2) if timings else None,
                             "oversized_rejected_count": ENGINE.rejected - rejected_start, "camera_motion_samples": pans,
                             "scene_cuts": cuts, "model": str(ENGINE.path.relative_to(ENGINE.path.parents[2])) if "finetuned" in ENGINE.path.parts else ENGINE.path.name,
                             "model_sha256": ENGINE.sha256, "fine_tuned": "finetuned" in ENGINE.path.parts, "device": ENGINE.device,
                             "preprocessing": getattr(ENGINE, "preprocessing", "letterbox"),
                             "accuracy": None, "evaluation_note": "Chưa có ground truth độc lập; đây là đo hiệu năng pipeline, không phải độ chính xác."}
        job.update(status="cancelled" if job["status"] == "cancelled" else "completed", progress=1 if job["status"] != "cancelled" else job["progress"],
                   summary=result["summary"], finished_at=store.now(), processed_until=result["processed_until"],
                   source_elapsed_seconds=result["source_elapsed_seconds"])
        result.update(state=job["status"], partial=job["status"] != "completed", updated_at=store.now())
        write_analysis(folder, result)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        result["summary"].update(samples=len(result["samples"]), events=len(result["events"]),
                                 processing_seconds=round(clock() - started, 3), provisional=True)
        job.update(status="failed", error=error, finished_at=store.now(),
                   processed_until=result["processed_until"], source_elapsed_seconds=result["source_elapsed_seconds"],
                   progress=min(.999, (result["processed_until"] or 0) / max(.001, job["video"]["duration"])),
                   summary=result["summary"])
        result.update(state="failed", error=error, partial=True, updated_at=store.now())
        write_analysis(folder, result)
    finally:
        if cap:
            cap.release()
        store.put("jobs", job)
        CANCELLED.discard(job["id"])
