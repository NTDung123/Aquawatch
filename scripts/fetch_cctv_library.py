"""Build a reviewed pool-surveillance incident catalog without changing the active library.

Only manually approved intervals from the existing user-requested source archive
are encoded. Original source bytes and former library manifests are preserved.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import cv2
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LIBRARY = DATA / "library"
ARCHIVE = DATA / "research/nvbangg.zip"
ARCHIVE_URL = "https://www.kaggle.com/api/v1/datasets/download/nvbangg/drowning-test?datasetVersionNumber=2"
ARCHIVE_SHA = "1707c8dfbc59a6296d89514a42c7411af69c347dcd68b9f0ec34985f63b6e2bf"
DATASET_PAGE = "https://www.kaggle.com/datasets/nvbangg/drowning-test"
ORIGINAL_IDS = {"IOHBGgt5oG4": 22, "T5mDQeDkca0": 19, "vt6ZBq5jVec": 13}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def probe(path):
    cap = cv2.VideoCapture(str(path))
    fps, frames = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, image = cap.read()
    cap.release()
    if not ok or fps <= 0 or frames <= 0:
        raise ValueError(f"Cannot decode {path}")
    return {"duration": round(frames / fps, 6), "fps": fps, "frames": frames,
            "width": image.shape[1], "height": image.shape[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=ROOT / "assets/cctv_library_review.json")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--activate", action="store_true", help="Activate the generated catalog after all clips pass decode checks; preserve the previous catalog in history.")
    args = parser.parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    specs = review["videos"]
    if not specs:
        parser.error("No reviewed CCTV incident intervals")
    for spec in specs:
        if spec["source_id"] not in ORIGINAL_IDS or spec.get("review_status") != "approved":
            parser.error("Only explicitly approved archive-source intervals are allowed")
        if not (spec.get("above_water") and spec.get("fixed_pool_surveillance") and spec.get("incident_or_rescue_observed")):
            parser.error("Scope requires above-water fixed pool surveillance with an observed incident/rescue")
        if spec.get("upstream_target_marker_in_interval") is not False:
            parser.error("Source target markers must be excluded from selected intervals")
        if spec["source_end"] <= spec["source_start"]:
            parser.error("Invalid interval")
    for directory in (ARCHIVE.parent, LIBRARY / "raw/nvbangg", LIBRARY / "clips", LIBRARY / "posters", LIBRARY / "history"):
        directory.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE.exists():
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        temporary = ARCHIVE.with_suffix(".zip.part")
        with opener.open(urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "AquaWatch-academic/1.0"}), timeout=120) as response, temporary.open("wb") as out:
            shutil.copyfileobj(response, out)
        if digest(temporary) != ARCHIVE_SHA:
            raise ValueError("Downloaded source archive changed; re-review before use")
        temporary.replace(ARCHIVE)
    if digest(ARCHIVE) != ARCHIVE_SHA:
        raise ValueError("Source archive checksum differs from reviewed archive")
    previous = DATA / "video_library.json"
    archived = None
    if previous.exists():
        old = json.loads(previous.read_text(encoding="utf-8"))
        if old.get("scope") != "pool_cctv_incident_only":
            archived = LIBRARY / "history" / ("video_library_pre_cctv_" + digest(previous)[:12] + ".json")
            if not archived.exists():
                shutil.copy2(previous, archived)
    sources, by_source = [], {}
    with ZipFile(ARCHIVE) as archive:
        for source_id in sorted(set(spec["source_id"] for spec in specs)):
            member = source_id + ".mp4"
            audited_path = LIBRARY / "research_cctv/nvbangg" / member
            path = audited_path if audited_path.exists() else LIBRARY / "raw/nvbangg" / member
            if not path.exists():
                with archive.open(member) as src, path.open("wb") as out:
                    shutil.copyfileobj(src, out)
            expected_member_sha = hashlib.sha256(archive.read(member)).hexdigest()
            if digest(path) != expected_member_sha:
                raise ValueError("Cached source bytes differ from the pinned archive member")
            metadata_path = LIBRARY / "raw" / (source_id + ".player_metadata.json")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))["videoDetails"] if metadata_path.exists() else {}
            record = {"id": source_id, "path": str(path), **probe(path), "size_bytes": path.stat().st_size,
                      "sha256": digest(path), "source_url": "https://www.youtube.com/watch?v=" + source_id,
                      "dataset_url": DATASET_PAGE, "download_url": ARCHIVE_URL, "archive_sha256": ARCHIVE_SHA,
                      "archive_member": member, "original_title": metadata.get("title", f"Wavepool Lifeguard Rescue {ORIGINAL_IDS[source_id]}"),
                      "source_timebase": "Kaggle archive MP4; offset within the longer original YouTube video is unknown",
                      "original_youtube_offset_seconds": None,
                      "credit": "Lifeguard Rescue (original channel); nvbangg (Kaggle dataset uploader)",
                      "source_group": "lifeguard_rescue_wavepool_same_site_possible_same_camera",
                      "license": "MIT declared by Kaggle uploader; original footage rights unverified",
                      "license_url": DATASET_PAGE,
                      "rights": {"dataset_uploader_declared_license": "MIT", "original_channel": "Lifeguard Rescue",
                                 "original_footage_license_verified": False, "creative_commons_verified": False,
                                 "use_context": "User-requested local educational/research reference from the downloaded dataset; no claim of redistribution clearance"},
                      "metadata_evidence": str(metadata_path) if metadata_path.exists() else None}
            sources.append(record)
            by_source[source_id] = record
    videos, checks = [], []
    for spec in specs:
        source = by_source[spec["source_id"]]
        if spec["source_start"] < 0 or spec["source_end"] > source["duration"] + .1:
            raise ValueError("Reviewed interval escapes source duration")
        target = LIBRARY / "clips" / (spec["id"] + ".mp4")
        if args.rebuild or not target.exists():
            temporary = target.with_stem(target.stem + ".encoding")
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                            "-ss", str(spec["source_start"]), "-i", source["path"],
                            "-t", str(spec["source_end"] - spec["source_start"]),
                            "-vf", "scale='min(1280,trunc(iw/2)*2)':-2", "-r", "30", "-an", "-c:v", "libx264", "-threads", "2",
                            "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temporary)], check=True)
            probe(temporary)
            temporary.replace(target)
        info = probe(target)
        check = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-threads", "2",
                                "-i", str(target), "-f", "null", "-"], capture_output=True, text=True)
        if check.returncode or check.stderr.strip():
            raise ValueError(f"Full decode failed for {target}: {check.stderr}")
        checks.append({"id": spec["id"], "returncode": check.returncode, "stderr": check.stderr,
                       "sha256": digest(target), "duration": info["duration"]})
        poster = LIBRARY / "posters" / (spec["id"] + ".jpg")
        capture = cv2.VideoCapture(str(target))
        capture.set(cv2.CAP_PROP_POS_MSEC, min(spec.get("poster_seconds", 2), info["duration"] / 2) * 1000)
        ok, frame = capture.read()
        capture.release()
        if not ok or not cv2.imwrite(str(poster), frame):
            raise ValueError("Cannot create clip poster")
        videos.append({"id": spec["id"], "name": spec["name"], "path": target.relative_to(ROOT).as_posix(), "url": "/media/library/clips/" + target.name,
                       "thumbnail_url": "/media/library/posters/" + poster.name, **info, "size_bytes": target.stat().st_size,
                       "sha256": checks[-1]["sha256"], "source_id": source["id"], "source_group": source["source_group"],
                       "source_url": source["source_url"], "source_start": spec["source_start"], "source_end": spec["source_end"],
                       "source_timebase": source["source_timebase"], "source_archive_member": source["archive_member"],
                       "original_youtube_offset_seconds": None,
                       "source_sha256": source["sha256"], "license": source["license"], "license_url": source["license_url"],
                       "rights": source["rights"], "credit": source["credit"], "environment": "pool", "camera_mode": "fixed",
                       "camera_type": "fixed_pool_surveillance", "camera_support": "primary_pool_cctv_incident",
                       "camera_evidence": spec["camera_evidence"], "scenario": "pool_distress_rescue", "nature": "source_reported_real_rescue",
                       "above_water": True, "view": "above_water_reviewed", "review_status": "reviewed_clip",
                       "cctv": True, "pool_incident": True,
                       "fixed_pool_surveillance": True, "incident_or_rescue_observed": True,
                       "review_notes": spec["review_notes"], "scene_cuts": 0,
                       "upstream_target_marker_in_interval": False,
                       "changes": "One continuous source interval, source time/speed preserved; H.264 30fps transcode; audio removed; no generated content or added target marks.",
                       "annotations": spec.get("annotations", []), "medical_ground_truth": False,
                       "manual_timeline": spec.get("manual_timeline"),
                       "manual_timeline_timebase": spec.get("manual_timeline_timebase"),
                       "review_evidence": spec.get("review_evidence"),
                       "split": "cctv_library_diagnostic_do_not_train",
                       "independence": "Same wavepool series; possible overlap with existing image datasets/pretraining. Not an independent final test or three independent camera domains."})
        print(f"Ready {spec['id']}: {info['duration']}s", flush=True)
    now = datetime.now(timezone.utc).isoformat()
    catalog = {"schema_version": 1, "checked_date": now[:10], "scope": "pool_cctv_incident_only", "sources": sources, "videos": videos,
               "review_method": review.get("review_method"), "review_manifest_sha256": digest(args.review),
               "medical_ground_truth": False, "total_clip_seconds": round(sum(v["duration"] for v in videos), 3),
               "previous_manifest_archived": str(archived) if archived else None,
               "active_manifest_replacement_required": True,
               "rights_notice": "Dataset uploader license and original footage rights are distinct; original license has not been independently verified. Local educational/research reference; no redistribution clearance claimed."}
    destination = DATA / "cctv_video_library.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)
    (DATA / "cctv_library_decode_checks.json").write_text(json.dumps({"checked_utc": now, "all_passed": True, "checks": checks}, indent=2), encoding="utf-8")
    if args.activate:
        if previous.exists():
            backup = LIBRARY / "history" / ("video_library_before_restore_" + digest(previous)[:12] + ".json")
            if not backup.exists():
                shutil.copy2(previous, backup)
        catalog["active_manifest_replacement_required"] = False
        active_temporary = previous.with_suffix(".tmp")
        active_temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        active_temporary.replace(previous)
        print(f"Activated {previous}: {len(videos)} reviewed CCTV clips.", flush=True)
    else:
        print(f"Prepared {destination}: {len(videos)} clips, {catalog['total_clip_seconds']} seconds. Use --activate to enable this catalog.", flush=True)


if __name__ == "__main__":
    main()
