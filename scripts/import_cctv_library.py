"""Import manually approved incident windows from a read-only local video collection.

The review manifest is data, never executable code. The source directory is never
modified. Outputs are silent browser-compatible clips, posters, and a catalog.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time

import cv2
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LIBRARY = DATA / "library"
SCOPE = "pool_cctv_incident_only"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def probe(path):
    cap = cv2.VideoCapture(str(path))
    fps, frames = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, image = cap.read()
    cap.release()
    if not ok or fps <= 0 or frames <= 0:
        raise ValueError(f"Cannot decode {path}")
    return {"duration": round(frames / fps, 6), "fps": fps, "frames": frames,
            "width": image.shape[1], "height": image.shape[0]}


def canonical_source_id(record, path):
    source_id = record.get("source_id") or record.get("video_id") or record.get("id")
    if source_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", str(source_id)):
        return str(source_id)
    match = re.search(r"\[([A-Za-z0-9_-]{11})\]", path.name)
    if not match:
        raise ValueError(f"No unambiguous source video ID: {path.name}")
    return match[1]


def approved_rows(review):
    for row in review.get("videos", []):
        if row.get("approved") is True or row.get("status") == "approved":
            yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(r"D:\drowning-detection\dataset_lifeguard\videos_source"))
    parser.add_argument("--review", type=Path, default=DATA / "source_library_review.json")
    parser.add_argument("--workers", type=int, choices=[1, 2, 3], default=2)
    parser.add_argument("--limit", type=int, help="Bound one batch without changing review status")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    review_bytes = args.review.read_bytes()
    review = json.loads(review_bytes)
    review_sha = hashlib.sha256(review_bytes).hexdigest()
    for directory in (LIBRARY / "clips", LIBRARY / "posters", LIBRARY / "history"):
        directory.mkdir(parents=True, exist_ok=True)
    cache_path = LIBRARY / "local_cctv_import_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {"clips": {}}
    tasks, source_records, rejected = [], {}, []
    rows = list(approved_rows(review))
    if args.limit:
        rows = rows[:args.limit]
    for row in rows:
        path = Path(row["path"]).resolve()
        if not path.is_relative_to(source_root) or not path.is_file():
            raise ValueError(f"Reviewed source is outside the read-only source root: {path}")
        source_id = canonical_source_id(row, path)
        camera = row.get("camera_mode", row.get("camera", ""))
        if row.get("above_water") is not True or row.get("environment", "pool") != "pool" or camera not in ("fixed", "fixed_pool_cctv", "fixed_pool_surveillance"):
            rejected.append({"source_id": source_id, "reason": "Approved row lacks explicit above-water fixed pool viewpoint"})
            continue
        if row.get("incident", row.get("pool_incident", row.get("incident_or_rescue_observed"))) is not True:
            rejected.append({"source_id": source_id, "reason": "Incident/rescue not explicitly approved"})
            continue
        info, source_sha = probe(path), digest(path)
        expected = row.get("source_sha256", row.get("sha256"))
        if expected and expected != source_sha:
            raise ValueError(f"Source changed after review: {path.name}")
        title = re.sub(r"\s*\[[A-Za-z0-9_-]{11}\]$", "", path.stem)
        episode = re.search(r"Wavepool Lifeguard Rescue\s+(\d+)", title, re.I)
        series = "Wavepool Lifeguard Rescue" in title
        group = "lifeguard_rescue_wavepool_same_site_possible_same_camera" if series else row.get("source_group", "local_pool_surveillance_" + source_id)
        source_records[source_id] = {"id": source_id, "path": str(path), "filename": path.name, "original_title": title,
                                     "source_url": "https://www.youtube.com/watch?v=" + source_id,
                                     "source_id": source_id, "sha256": source_sha, "size_bytes": path.stat().st_size,
                                     **info, "source_group": group,
                                     "license": "User-provided local footage; original footage license unverified",
                                     "license_url": "https://www.youtube.com/watch?v=" + source_id,
                                     "credit": "Lifeguard Rescue series; user-provided local copy" if series else "User-provided local pool surveillance source",
                                     "rights": {"user_provided": True, "local_import_requested": True,
                                                "original_footage_license_verified": False,
                                                "redistribution_clearance_verified": False,
                                                "note": "Repository code licenses do not establish rights in original video footage."}}
        windows = row.get("windows", [])
        for index, window in enumerate(windows):
            if window.get("approved") is False:
                continue
            markers = window.get("target_markers", window.get("markers", row.get("target_markers", row.get("markers"))))
            if markers is not False:
                rejected.append({"source_id": source_id, "window": index, "reason": "No explicit confirmation that selected interval excludes source target marks"})
                continue
            start, end = float(window["start"]), float(window["end"])
            if not all(math.isfinite(v) for v in (start, end)) or not 0 <= start < end <= info["duration"] + .05 or end - start < 3:
                raise ValueError(f"Invalid reviewed source interval: {source_id} {start}..{end}")
            clip_id = f"cctv_local_{source_id}_{round(start * 1000)}_{round(end * 1000)}_{source_sha[:8]}"
            if series:
                name = "CCTV bể sóng · cứu hộ" + (" #" + episode[1] if episode else "")
            else:
                name = "CCTV bể bơi · tình huống cứu hộ " + source_id
            if len(windows) > 1:
                name += " · đoạn " + str(index + 1)
            tasks.append({"id": clip_id, "name": name, "source_id": source_id, "source": source_records[source_id],
                          "start": start, "end": end, "window": window, "review": row,
                          "cache": cache["clips"].get(clip_id), "review_manifest_sha256": review_sha})
    if not tasks:
        write_json(LIBRARY / "local_cctv_import_report.json", {"status": "no_approved_windows", "review_manifest_sha256": review_sha,
                                                           "approved_rows": len(rows), "rejected": rejected})
        print("No qualifying approved windows; active library unchanged.", flush=True)
        return
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    def build(task):
        started = time.perf_counter()
        target = LIBRARY / "clips" / (task["id"] + ".mp4")
        cached = task["cache"]
        reused = not args.rebuild and target.exists() and cached and cached.get("decode_passed") and digest(target) == cached.get("sha256")
        if not reused:
            temporary = target.with_stem(target.stem + ".encoding")
            subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(task["start"]),
                            "-i", task["source"]["path"], "-t", str(task["end"] - task["start"]),
                            "-vf", "scale='min(1280,trunc(iw/2)*2)':-2,fps=30", "-an", "-c:v", "libx264", "-threads", "2",
                            "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temporary)],
                           check=True, capture_output=True, text=True)
            info = probe(temporary)
            if abs(info["duration"] - (task["end"] - task["start"])) > .15:
                raise ValueError(f"Encoded duration mismatch: {task['id']}")
            result = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-threads", "2", "-i", str(temporary), "-f", "null", "-"],
                                    capture_output=True, text=True)
            if result.returncode or result.stderr.strip():
                raise ValueError(f"Full decode failed: {task['id']} {result.stderr}")
            temporary.replace(target)
            cached = {"sha256": digest(target), "decode_passed": True, "decode_returncode": result.returncode,
                      "decode_stderr": result.stderr, "info": info, "size_bytes": target.stat().st_size,
                      "source_sha256": task["source"]["sha256"], "source_start": task["start"], "source_end": task["end"]}
        info = cached["info"]
        poster = LIBRARY / "posters" / (task["id"] + ".jpg")
        if not poster.exists() or not reused:
            capture = cv2.VideoCapture(str(target))
            capture.set(cv2.CAP_PROP_POS_MSEC, min(2, info["duration"] / 2) * 1000)
            ok, frame = capture.read()
            capture.release()
            if not ok or not cv2.imwrite(str(poster), frame):
                raise ValueError(f"Cannot create poster: {task['id']}")
        annotations = []
        window, row, source = task["window"], task["review"], task["source"]
        incident_start, incident_end = window.get("incident_start"), window.get("incident_end")
        if incident_start is not None and incident_end is not None:
            a_start = max(0., float(incident_start) - task["start"])
            a_end = min(info["duration"], float(incident_end) - task["start"])
            if not all(math.isfinite(v) for v in (a_start, a_end)) or a_end <= a_start:
                raise ValueError(f"Invalid incident annotation endpoints: {task['id']}")
            annotations.append({"start": a_start, "end": a_end, "label": "manually_reviewed_pool_incident_or_rescue_window",
                                "certainty": "Approximate visual/source annotation, not clinical onset or independent event truth"})
        if not annotations:
            annotations.append({"start": 0., "end": info["duration"], "label": "pool_incident_rescue_context",
                                "certainty": "Source context and manual visible behavior, not clinical ground truth"})
        record = {"id": task["id"], "name": task["name"], "path": target.relative_to(ROOT).as_posix(), "url": "/media/library/clips/" + target.name,
                  "thumbnail_url": "/media/library/posters/" + poster.name, **info, "size_bytes": cached["size_bytes"],
                  "sha256": cached["sha256"], "source_id": source["id"], "source_group": source["source_group"],
                  "source_url": source["source_url"], "source_filename": source["filename"], "source_path": source["path"],
                  "source_sha256": source["sha256"], "source_start": task["start"], "source_end": task["end"],
                  "source_timebase": "Seconds in the user-provided full local source file", "original_youtube_offset_seconds": None,
                  "credit": source["credit"], "license": source["license"], "license_url": source["license_url"], "rights": source["rights"],
                  "environment": "pool", "camera_mode": "fixed", "camera_type": "fixed_pool_surveillance",
                  "camera_support": "primary_pool_cctv_incident", "cctv": True, "pool_incident": True, "above_water": True,
                  "view": "above_water_reviewed", "scenario": "pool_distress_rescue", "nature": "source_reported_incident_rescue",
                  "review_status": "reviewed_clip", "review_notes": str(window.get("notes", "")) + " " + str(row.get("notes", "")),
                  "review_method": row.get("review_method", review.get("review_method", review.get("method"))),
                  "review_timestamps": row.get("review_timestamps", row.get("sample_times", [])),
                  "review_manifest_sha256": task["review_manifest_sha256"], "reviewed_utc": row.get("reviewed_utc", review.get("reviewed_utc")),
                  "upstream_target_marker_in_interval": False, "scene_cuts": 0, "annotations": annotations,
                  "split": "cctv_library_diagnostic_do_not_train", "medical_ground_truth": False,
                  "changes": "One continuous manually reviewed source interval; original source time/speed preserved; H.264/30fps transcode and audio removal; no generated footage or added target marks.",
                  "independence": "Possible overlap with image training/pretraining and same wavepool series. Not an independent final test; multiple windows from one source are not independent videos."}
        return record, cached, {"id": task["id"], "source_id": task["source_id"], "seconds": info["duration"],
                                "bytes": cached["size_bytes"], "decode_passed": True, "reused": bool(reused),
                                "processing_seconds": round(time.perf_counter() - started, 3)}

    started = time.perf_counter()
    built, checks, failures = [], [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(build, task): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                record, result_cache, check = future.result()
                built.append(record)
                checks.append(check)
                cache["clips"][task["id"]] = result_cache
                write_json(cache_path, cache)
                print(f"Ready {len(built)}/{len(tasks)} {task['source_id']}: {record['duration']}s", flush=True)
            except Exception as error:
                failures.append({"id": task["id"], "source_id": task["source_id"], "error": str(error)})
                print(f"FAILED {task['source_id']}: {error}", flush=True)
    active_path = DATA / "video_library.json"
    old = json.loads(active_path.read_text(encoding="utf-8")) if active_path.exists() else {"videos": [], "sources": []}
    old_sha = digest(active_path) if active_path.exists() else None
    history = LIBRARY / "history" / ("video_library_before_local_import_" + (old_sha[:12] if old_sha else "empty") + ".json")
    if active_path.exists() and not history.exists():
        shutil.copy2(active_path, history)
    imported_source_ids = {record["source_id"] for record in built}
    retained = [v for v in old.get("videos", []) if v.get("source_id") not in imported_source_ids
                and v.get("cctv") and v.get("pool_incident") and v.get("above_water")
                and v.get("environment") == "pool" and v.get("camera_mode") == "fixed"]
    replaced = [v["id"] for v in old.get("videos", []) if v.get("source_id") in imported_source_ids and v["id"] not in {b["id"] for b in built}]
    sources = {s["id"]: s for s in old.get("sources", []) if s["id"] not in imported_source_ids}
    sources.update({source_id: source_records[source_id] for source_id in imported_source_ids})
    videos = sorted(retained + built, key=lambda v: (v.get("source_id", ""), v.get("source_start", 0)))
    now = datetime.now(timezone.utc).isoformat()
    catalog = {**old, "schema_version": 1, "scope": SCOPE, "checked_date": datetime.now(timezone(timedelta(hours=7))).date().isoformat(), "updated_utc": now,
               "sources": list(sources.values()), "videos": videos,
               "total_clip_seconds": round(sum(v["duration"] for v in videos), 3),
               "distinct_source_videos": len({v["source_id"] for v in videos}),
               "source_groups": len({v["source_group"] for v in videos}),
               "review_method": "Only explicitly approved fixed-pool incident windows from the source review manifest; review details/timestamps retained per clip.",
               "review_manifest": str(args.review.resolve()), "review_manifest_sha256": review_sha,
               "active_manifest_replacement_required": False,
               "rights_notice": "Local user-provided footage requested for educational/research use. Original footage licenses have not been independently verified; no redistribution clearance claimed.",
               "independence_notice": "These clips may overlap existing training images/pretraining. Same-venue wavepool videos and multiple windows are not independent camera domains or an untouched test."}
    report = {"status": "completed_with_failures" if failures else "completed", "updated_utc": now,
              "source_root": str(source_root), "source_root_modified": False, "review_manifest_sha256": review_sha,
              "approved_rows_in_snapshot": len(rows), "requested_windows": len(tasks), "successful_windows": len(built),
              "active_clips": len(videos), "active_distinct_source_videos": catalog["distinct_source_videos"],
              "active_seconds": catalog["total_clip_seconds"], "active_mp4_bytes": sum(v["size_bytes"] for v in videos),
              "catalog_archive": str(history), "replaced_duplicate_source_records": replaced, "checks": checks,
              "rejected": rejected, "failures": failures, "processing_seconds": round(time.perf_counter() - started, 3)}
    write_json(LIBRARY / "local_cctv_import_report.json", report)
    if built:
        write_json(active_path, catalog)
    print(json.dumps({k: v for k, v in report.items() if k not in ("checks", "rejected", "failures")}), flush=True)


if __name__ == "__main__":
    main()
