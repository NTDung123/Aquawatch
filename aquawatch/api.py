import csv
import hashlib
import io
import json
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from . import jobs, store
from .settings import DATA, LIBRARY, MODEL, RESULTS, ROOT, VIDEOS, selected_model
from .library import register_library


@asynccontextmanager
async def lifespan(app):
    register_library()
    for job in store.all_items("jobs"):
        if job["status"] in ("running", "queued"):
            job.update(status="failed", error="Lần xử lý trước bị gián đoạn. Hãy tạo lượt phân tích mới.")
            store.put("jobs", job)
    yield


app = FastAPI(title="AquaWatch", lifespan=lifespan)


class JobRequest(BaseModel):
    video_id: str
    mode: Literal["batch", "realtime"] = "batch"
    camera_mode: Literal["fixed", "ptz"] = "fixed"
    water_polygon: list[list[float]] = Field(default_factory=list, max_length=30)
    sample_fps: float = Field(default=5, ge=1, le=10)
    confidence: float = Field(default=.4, ge=.15, le=.95)

    @field_validator("water_polygon")
    @classmethod
    def polygon_valid(cls, value):
        if value and len(value) < 3:
            raise ValueError("Vùng nước cần ít nhất 3 điểm")
        if any(len(p) != 2 or any(not 0 <= c <= 1 for c in p) for p in value):
            raise ValueError("Tọa độ vùng nước phải thuộc [0,1]")
        return value


class AcknowledgeRequest(BaseModel):
    note: str = Field(default="", max_length=500)


def required_job(job_id):
    item = store.get("jobs", job_id)
    if item is None:
        raise HTTPException(404, "Không tìm thấy lượt phân tích")
    return item


def public_video(item):
    return {k: v for k, v in item.items() if k != "path"}


def public_job(item):
    return {**item, "video": public_video(item["video"])}


@app.get("/api/status")
def status():
    import psutil
    import torch
    selected = selected_model()
    actual = jobs.ENGINE.path if jobs.ENGINE else selected
    fine = "finetuned" in actual.parts
    record_file = DATA / "training_record.json"
    record = json.loads(record_file.read_text(encoding="utf-8")) if fine and record_file.is_file() else {}
    deployment = getattr(jobs.ENGINE, "deployment", {}) if jobs.ENGINE else record.get("deployment", {})
    memory = psutil.virtual_memory()
    return {"name": "AquaWatch", "mode": "local", "model": {"ready": MODEL.exists(),
             "name": deployment.get("display_name", "YOLOv8s fine-tuned local") if fine else "YOLOv8s community baseline",
             "recommended_confidence": deployment.get("recommended_confidence", .4),
             "preprocessing": deployment.get("preprocessing", "letterbox"),
             "classes": ["drowning", "swimming"], "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
             "fine_tuned": fine, "validated": False,
             "reload_pending": actual != selected or bool(jobs.ENGINE and jobs.ENGINE.sha256 != hashlib.sha256(selected.read_bytes()).hexdigest()),
             "path": str(actual.relative_to(ROOT))},
            "hardware": {"ram_gb": round(memory.total / 1024**3, 1), "cpu_logical": psutil.cpu_count(), "cuda": torch.cuda.is_available()},
            "limits": {"upload_mb": 1024, "duration_minutes": 30, "concurrent_jobs": 1},
            "notice": "Sản phẩm học thuật hỗ trợ nhận biết nguy cơ; chưa kiểm định thay thế nhân viên cứu hộ."}


@app.get("/api/videos")
def videos():
    register_library()
    return [public_video(v) for v in store.all_items("videos")]


@app.post("/api/videos", status_code=201)
async def upload(file: UploadFile = File(...), camera_mode: Literal["fixed", "ptz"] = Form("fixed"),
                 environment: Literal["pool", "beach", "river", "flood", "other"] = Form("pool"),
                 above_water: bool = Form(False)):
    if not above_water:
        raise HTTPException(422, "Cần xác nhận video được ghi bằng camera phía trên mặt nước.")
    extension = Path(file.filename or "").suffix.lower()
    if extension not in (".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"):
        raise HTTPException(415, "Chọn video MP4, MOV, M4V, WebM, AVI hoặc MKV.")
    video_id = uuid.uuid4().hex
    path = VIDEOS / (video_id + extension)
    size = 0
    try:
        with path.open("wb") as target:
            while block := await file.read(1024 * 1024):
                size += len(block)
                if size > 1024**3:
                    raise HTTPException(413, "Video vượt giới hạn 1 GB")
                target.write(block)
        info = jobs.probe(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()
    name = Path((file.filename or "Video").replace("\\", "/")).name[:200]
    video = {"id": video_id, "name": name, "path": str(path), "url": f"/media/videos/{path.name}",
             **info, "size_bytes": size, "camera_mode": camera_mode, "environment": environment,
             "view": "above_water_declared_by_user", "source": "Người dùng tải lên", "created_at": store.now()}
    store.put("videos", video)
    return public_video(video)


@app.post("/api/jobs", status_code=202)
def create_job(request: JobRequest):
    video = store.get("videos", request.video_id)
    if video is None:
        raise HTTPException(404, "Không tìm thấy video")
    if not MODEL.exists():
        raise HTTPException(503, "Thiếu model. Chạy scripts/fetch_assets.py trước.")
    with jobs.LOCK:
        if any(j["status"] in ("queued", "running") for j in store.all_items("jobs")):
            raise HTTPException(409, "Đang xử lý một video. Hãy chờ hoặc hủy lượt hiện tại.")
        return public_job(jobs.submit(video, request.model_dump()))


@app.get("/api/jobs")
def list_jobs():
    return [public_job(j) for j in store.all_items("jobs")]


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    return public_job(required_job(job_id))


@app.post("/api/jobs/{job_id}/cancel")
def cancel(job_id: str):
    job = required_job(job_id)
    if job["status"] in ("queued", "running"):
        jobs.CANCELLED.add(job_id)
    return {"id": job_id, "cancel_requested": job["status"] in ("queued", "running")}


def analysis(job_id):
    job = required_job(job_id)
    path = RESULTS / job_id / "analysis.json"
    if not path.exists():
        raise HTTPException(409, "Chưa có kết quả. Hãy chờ xử lý xong.")
    result = json.loads(path.read_text(encoding="utf-8"))
    result["state"] = job["status"]
    result["mode"] = job.get("config", {}).get("mode", "batch")
    result["partial"] = job["status"] != "completed"
    result.setdefault("processed_until", result["samples"][-1]["time"] if result.get("samples") else None)
    acks = store.acknowledgments(job_id)
    for event in result["events"]:
        event.update(acks.get(event["id"], {}))
    return result


@app.get("/api/jobs/{job_id}/analysis")
def get_analysis(job_id: str):
    return analysis(job_id)


@app.post("/api/jobs/{job_id}/events/{event_id}/ack")
def acknowledge(job_id: str, event_id: str, request: AcknowledgeRequest):
    if not any(e["id"] == event_id for e in analysis(job_id)["events"]):
        raise HTTPException(404, "Không tìm thấy sự kiện")
    return store.acknowledge(job_id, event_id, request.note)


@app.get("/api/jobs/{job_id}/export")
def export(job_id: str, format: Literal["json", "csv"] = "json"):
    result = analysis(job_id)
    if format == "json":
        content = json.dumps(result, ensure_ascii=False, indent=2)
        media = "application/json"
    else:
        target = io.StringIO()
        writer = csv.writer(target)
        writer.writerow(["id", "track_id", "start_seconds", "end_seconds", "level", "confidence", "inferred", "reasons", "acknowledged"])
        for event in result["events"]:
            writer.writerow([event["id"], event["track_id"], event["start"], event["end"], event["level"], event["confidence"],
                             event["inferred"], "; ".join(event["reasons"]), event["acknowledged"]])
        content, media = "\ufeff" + target.getvalue(), "text/csv; charset=utf-8"
    return Response(content=content, media_type=media, headers={"Content-Disposition": f'attachment; filename="aquawatch-{job_id}.{format}"'})


@app.get("/media/results/{job_id}/{filename}")
def result_image(job_id: str, filename: str):
    if not re.fullmatch(r"[0-9a-f]{32}", job_id) or not re.fullmatch(r"[0-9a-f]{32}\.jpg", filename):
        raise HTTPException(404)
    path = RESULTS / job_id / filename
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


app.mount("/media/videos", StaticFiles(directory=VIDEOS), name="videos")
app.mount("/media/library/clips", StaticFiles(directory=LIBRARY / "clips"), name="library_clips")
app.mount("/media/library/posters", StaticFiles(directory=LIBRARY / "posters"), name="library_posters")
app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
