"""Fetch licensed sources and cut manually reviewed continuous above-water clips."""
import argparse
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

import cv2
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "data" / "library"
RAW = LIBRARY / "raw"
CLIPS = LIBRARY / "clips"
PD_LICENSE = "Public Domain as marked by DVIDS; subject to DVIDS usage notice"
PD_URL = "https://www.dvidshub.net/about/copyright"
SOURCES = {
    "navy_swim": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2304/DOD_109586372/DOD_109586372.mp4",
        "page": "https://www.dvidshub.net/video/880397/navy-wounded-warrior-trials-swimming-b-roll",
        "credit": "Jonathan Snyder, Alexa Trafton, Samuel Tyson / Defense Media Activity - Navy Production, 2023-03-30",
        "source_group": "navy_wounded_warrior_trials_2023", "extension": ".mp4",
    },
    "s3t_active": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2003/DOD_107705947/DOD_107705947-1024x576-1769k.mp4",
        "page": "https://www.dvidshub.net/video/741392/swim-survival-skills-training-s3t-conduct-buddy-assist-active-drowning-victim",
        "credit": "Michael Stevenson / Marine and Family Programs, 2020-01-01",
        "source_group": "s3t_pool_training_2020", "extension": ".mp4",
    },
    "s3t_passive": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2003/DOD_107731122/DOD_107731122-1024x576-1769k.mp4",
        "page": "https://www.dvidshub.net/video/743307/swim-survival-skills-training-s3t-conduct-buddy-assist-whole-video",
        "credit": "Michael Stevenson / Marine and Family Programs, 2020-01-01",
        "source_group": "s3t_pool_training_2020", "extension": ".mp4",
    },
    "s3t_orient": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2003/DOD_107705966/DOD_107705966-1024x576-1769k.mp4",
        "page": "https://www.dvidshub.net/video/741399/swim-survival-skills-training-s3t-orient-safety",
        "credit": "Michael Stevenson / Marine and Family Programs, 2020-01-01",
        "source_group": "s3t_pool_training_2020", "extension": ".mp4",
    },
    "rescue_drill": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2503/DOD_110843934/DOD_110843934.mp4",
        "page": "https://www.dvidshub.net/video/954300/train-trainer-rescue-watercraft-course-mcbh",
        "credit": "Cpl Dezmond Browning / Marine Corps Base Hawaii, 2025-02-26",
        "source_group": "mcbh_watercraft_drill_2025", "extension": ".mp4",
    },
    "commons_pool_480": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/transcoded/0/01/Swimming_pool_1_2019-02-23.webm/Swimming_pool_1_2019-02-23.webm.480p.vp9.webm",
        "page": "https://commons.wikimedia.org/wiki/File:Swimming_pool_1_2019-02-23.webm",
        "credit": "FASTILY, own work, 2019-02-19", "source_group": "fastily_pool_2019_02_19",
        "extension": ".webm", "license": "CC BY-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    },
    "usbp_rescue": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2109/DOD_108554715/DOD_108554715-1024x576-1769k.mp4",
        "page": "https://www.dvidshub.net/video/812817/usbp-rescues-drowning-man",
        "credit": "Matthew Dyman / U.S. Customs and Border Protection, 2021-09-01",
        "source_group": "usbp_imperial_beach_2021_09_01", "extension": ".mp4",
        "existing_path": "data/examples/usbp_rescue_imperial_beach_2021.mp4",
    },
    "invictus_swim": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2502/DOD_110800100/DOD_110800100.mp4",
        "page": "https://www.dvidshub.net/video/951507/jblm-training-camp-swimming-b-roll-package",
        "credit": "Anthony Beauchamp / U.S. Army Transformation and Training Command, 2025-02-05",
        "source_group": "invictus_jblm_swimming_2025", "extension": ".mp4",
    },
    "sasebo_sar": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/1410/DOD_102006411/DOD_102006411-640x480-922k.mp4",
        "page": "https://www.dvidshub.net/video/364098/broll-search-and-rescue-training",
        "credit": "Krystina Coffey / AFN Sasebo, 2014-09-25",
        "source_group": "sasebo_sar_pool_training_2014", "extension": ".mp4",
    },
    "warrior_swim_2024": {
        "url": "https://d34w7g4gy10iej.cloudfront.net/video/2406/DOD_110417736/DOD_110417736.mp4",
        "page": "https://www.dvidshub.net/video/929329/2024-dod-warrior-games-swimming",
        "credit": "Maurice Moore / Warrior Games, 2024-06-29",
        "source_group": "warrior_games_swimming_orlando_2024", "extension": ".mp4",
    },
}
SPECS = [
    {"id": "pool_normal_lane_35s", "name": "Bể bơi · vận động viên nghỉ và bơi có kiểm soát · 35 giây", "source_id": "navy_swim", "start": 113, "end": 148, "scenario": "normal_swimming", "environment": "pool", "camera_mode": "fixed", "camera_support": "primary_fixed_view_segment", "label": "controlled_pool_activity_no_visible_distress", "nature": "sports_training", "notes": "Steady poolside view. Resting/treading is a useful hard negative; normality is an observational annotation, not a medical judgment."},
    {"id": "pool_normal_orient_15s", "name": "Bể bơi · định hướng và bơi chủ động · 15 giây", "source_id": "s3t_orient", "start": 7, "end": 22, "scenario": "normal_swimming", "environment": "pool", "camera_mode": "fixed", "camera_support": "primary_fixed_view_segment", "label": "controlled_treading_then_swimming", "nature": "instructional_drill", "notes": "Single above-water fixed view, intentional treading then swimming. No observed emergency; source is a supervised skill demonstration."},
    {"id": "pool_empty_reflections_48s", "name": "Bể bơi · không có người, phản chiếu mặt nước · 48 giây", "source_id": "commons_pool_480", "start": 1, "end": 49, "scenario": "negative_background", "environment": "pool", "camera_mode": "fixed", "camera_support": "secondary_static_scene_minor_drift", "label": "empty_pool_no_person_visible", "nature": "ordinary_pool_scene", "notes": "Above-water pool view with small framing drift. Background-only negative; cannot substitute for normal-swimming negative footage. Physical CCTV installation not verified."},
    {"id": "pool_staged_active_18s", "name": "Diễn tập · dấu hiệu chới với và người tiếp cận · 18 giây", "source_id": "s3t_active", "start": 19, "end": 37, "scenario": "staged_distress", "environment": "pool", "camera_mode": "fixed", "camera_support": "primary_fixed_view_segment", "label": "staged_active_distress_with_rescuer_approach", "nature": "instructional_drill", "notes": "Wide single shot. Source identifies an active drowning-victim drill. Annotation refers to simulated visible behavior, not a real clinical incident."},
    {"id": "pool_staged_assist_18s", "name": "Diễn tập · tiếp cận và hỗ trợ nổi · 18 giây", "source_id": "s3t_active", "start": 41, "end": 59, "scenario": "rescue_assist", "environment": "pool", "camera_mode": "fixed", "camera_support": "primary_fixed_view_segment", "label": "staged_rescue_assist_with_flotation_pack", "nature": "instructional_drill", "notes": "Close above-water view of pack presentation and assisted movement. Same source as active_18s; never treat as independent event/source when splitting."},
    {"id": "pool_staged_passive_9s", "name": "Diễn tập · người nổi thụ động nhìn từ trên bờ · 9 giây", "source_id": "s3t_passive", "start": 26, "end": 35, "scenario": "staged_passive_float", "environment": "pool", "camera_mode": "fixed", "camera_support": "primary_fixed_view_segment", "label": "staged_passive_surface_float", "nature": "instructional_drill", "notes": "Only the above-water wide shot is retained. Underwater-camera shots later in the original are excluded. Short clip does not establish loss of consciousness."},
    {"id": "beach_watercraft_drill_16s", "name": "Diễn tập ven biển · người chờ hỗ trợ và mô tô nước · 16 giây", "source_id": "rescue_drill", "start": 47, "end": 63, "scenario": "rescue_assist", "environment": "beach", "camera_mode": "ptz", "camera_support": "secondary_motion_stress", "scene_cuts": 1, "label": "supervised_watercraft_rescue_drill", "nature": "instructional_drill", "notes": "Above-water shore views with reframing and an original edit at approximately clip second 6. Secondary camera-motion/scene-cut/domain-stress sample; not a continuous fixed CCTV benchmark."},
    {"id": "beach_usbp_rescue_full", "name": "Cứu hộ thật · Imperial Beach · camera xoay/zoom", "source_id": "usbp_rescue", "start": 0, "end": 105.5, "scenario": "real_rescue", "environment": "beach", "camera_mode": "ptz", "camera_support": "secondary_motion_stress", "label": "real_rescue_context_interval_not_event_ground_truth", "nature": "real_rescue", "notes": "Source confirms a real rip-current rescue. Camera pans/zooms. No frame-level victim identity or incident-onset truth is claimed; annotation is contextual only."},
    {"id": "pool_normal_edge_32s", "name": "Bể bơi · nghỉ ở mép bể và người bơi qua · 32 giây", "source_id": "navy_swim", "start": 180, "end": 212, "scenario": "normal_swimming", "environment": "pool", "camera_mode": "fixed", "camera_support": "primary_fixed_view_segment", "label": "controlled_poolside_rest_and_swimmers_passing", "nature": "sports_training", "notes": "Continuous stable shore view. People sit/rest by the pool while swimmers pass in front, with partial occlusion. No visible emergency. Same source group as pool_normal_lane_35s; not an independent camera/event source."},
    {"id": "pool_normal_goggles_12s", "name": "Bể bơi · đứng nước chỉnh kính · 12 giây", "source_id": "invictus_swim", "start": 60, "end": 72, "scenario": "normal_swimming", "environment": "pool", "camera_mode": "fixed", "camera_support": "primary_fixed_view_segment", "label": "athlete_adjusting_goggles_in_pool_no_visible_distress", "nature": "sports_training", "notes": "Above-water stable close shore view of a supervised athlete adjusting goggles. Hands near head and upright posture form a hard negative. Physical CCTV installation is not established."},
    {"id": "pool_normal_backstroke_13s", "name": "Bể bơi · bơi ngửa chủ động · camera pan · 13 giây", "source_id": "invictus_swim", "start": 174, "end": 187, "scenario": "normal_swimming", "environment": "pool", "camera_mode": "ptz", "camera_support": "secondary_motion_stress", "label": "controlled_backstroke_with_camera_follow", "nature": "sports_training", "notes": "Continuous above-water shore camera following a backstroke swimmer. Secondary motion hard negative; no medical emergency observed. Same Invictus source group as goggles clip."},
    {"id": "pool_normal_race_8s", "name": "Bể ngoài trời · bơi thi đấu · 8 giây", "source_id": "warrior_swim_2024", "start": 93, "end": 101, "scenario": "normal_swimming", "environment": "pool", "camera_mode": "ptz", "camera_support": "secondary_motion_stress", "scene_cuts": 1, "label": "supervised_competitive_swimming_no_visible_distress", "nature": "sports_competition", "notes": "Above-water poolside camera follows swimming competitors, with lane splashes and partial occlusion. One original source edit occurs in the first second. Short motion/scene-cut hard negative, not a continuous fixed-CCTV benchmark."},
    {"id": "pool_staged_buddy_tow_5s", "name": "Diễn tập · tiếp cận người có vật nổi · 5 giây", "source_id": "sasebo_sar", "start": 198, "end": 203, "scenario": "rescue_assist", "environment": "pool", "camera_mode": "ptz", "camera_support": "secondary_motion_stress", "scene_cuts": 1, "label": "supervised_buddy_tow_assist_drill", "nature": "instructional_drill", "notes": "Above-water shore shots of a trainee approaching a floating role-player and starting assistance. An original edit in the last second changes the view; secondary scene-cut stress only. Explicitly a SAR drill; no real drowning or unconsciousness inferred. Underwater-camera intervals are excluded."},
]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def probe(path):
    cap = cv2.VideoCapture(str(path))
    fps, frames = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, frame = cap.read()
    cap.release()
    if not ok or fps <= 0 or frames <= 0:
        raise RuntimeError(f"Cannot decode {path}")
    return {"duration": round(frames / fps, 6), "fps": fps, "frames": frames, "width": frame.shape[1], "height": frame.shape[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="Re-encode the reviewed clips from their cached full sources")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    CLIPS.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    source_records = []
    for source_id, source in SOURCES.items():
        existing = ROOT / source.get("existing_path", "")
        path = existing if source.get("existing_path") and existing.is_file() else RAW / (source_id + source["extension"])
        cached_metadata = RAW / (source_id + ".metadata.json")
        url = source["url"]
        if cached_metadata.exists():
            url = json.loads(cached_metadata.read_text(encoding="utf-8"))["url"]
        if not path.exists() or not path.stat().st_size:
            temporary = path.with_suffix(path.suffix + ".part")
            request = urllib.request.Request(url, headers={"User-Agent": "AquaWatch-academic/1.0"})
            with opener.open(request, timeout=120) as response, temporary.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            temporary.replace(path)
        record = {"id": source_id, "source_url": source["page"], "download_url": url, "path": str(path),
                  "sha256": digest(path), "size_bytes": path.stat().st_size, "credit": source["credit"],
                  "license": source.get("license", PD_LICENSE), "license_url": source.get("license_url", PD_URL),
                  "source_group": source["source_group"], **probe(path)}
        source_records.append(record)
    by_id = {source["id"]: source for source in source_records}
    videos = []
    for spec in SPECS:
        source = by_id[spec["source_id"]]
        target = CLIPS / (spec["id"] + ".mp4")
        if args.rebuild or not target.exists():
            encoded = target.with_stem(target.stem + ".encoding")
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                            "-ss", str(spec["start"]), "-i", source["path"], "-t", str(spec["end"] - spec["start"]),
                            "-vf", "scale='min(1280,iw)':-2", "-r", "30", "-an", "-c:v", "libx264", "-threads", "2",
                            "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(encoded)], check=True)
            probe(encoded)
            encoded.replace(target)
        info = probe(target)
        poster = CLIPS / (spec["id"] + ".jpg")
        capture = cv2.VideoCapture(str(target))
        capture.set(cv2.CAP_PROP_POS_MSEC, min(1.0, info["duration"] / 2) * 1000)
        ok, frame = capture.read()
        capture.release()
        if ok:
            cv2.imwrite(str(poster), frame)
        videos.append({"id": spec["id"], "name": spec["name"], "path": str(target),
                       "url": "/media/library/clips/" + target.name, **info, "size_bytes": target.stat().st_size,
                       "thumbnail_url": "/media/library/clips/" + poster.name,
                       "sha256": digest(target), "source_id": source["id"], "source_group": source["source_group"],
                       "source_url": source["source_url"], "source_start": spec["start"], "source_end": spec["end"],
                       "source_sha256": source["sha256"], "license": source["license"], "license_url": source["license_url"],
                       "credit": source["credit"], "environment": spec["environment"], "camera_mode": spec["camera_mode"],
                       "camera_type": "visually_stable_shore_view_mount_unknown" if spec["camera_mode"] == "fixed" else "shore_view_pan_zoom_or_edits_mount_unknown",
                       "camera_support": spec["camera_support"], "scenario": spec["scenario"], "nature": spec["nature"],
                       "above_water": True, "view": "above_water_reviewed_segment", "review_status": "reviewed_clip",
                       "review_notes": spec["notes"], "scene_cuts": spec.get("scene_cuts", 0), "changes": "One continuous source time interval; H.264 transcode; output 30fps; audio removed; no added scene assembly, synthetic content or speed change. Original source edits may remain where explicitly marked.",
                       "annotations": [{"start": 0, "end": info["duration"], "label": spec["label"],
                                        "certainty": "manual_observable_behavior_or_source_context; not medical event truth"}],
                       "split": "video_library_holdout_do_not_train", "independence": "Not used by local training. Overlap with unknown upstream pretrained data has not been established."})
        print(f"Ready {spec['id']}: {info['duration']}s, {target.stat().st_size} bytes", flush=True)
    catalog = {"schema_version": 1, "checked_date": "2026-10-28", "sources": source_records, "videos": videos,
               "review_method": "Manual source contact-sheet review across the source timeline, plus selected clips sampled every 1 second (2 seconds for the longer USBP clip), including interval boundaries. This is sample-based visual review, not certification of each frame. Fixed-view means observed stable framing; physical camera installation is not established.",
               "medical_ground_truth": False, "total_clip_seconds": round(sum(v["duration"] for v in videos), 3),
               "no_endorsement_notice": "The appearance of U.S. Department of War (DoW) visual information does not imply or constitute DoW endorsement."}
    destination = ROOT / "data" / "video_library.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)
    print(f"Catalog: {destination}; {len(videos)} clips, {catalog['total_clip_seconds']} seconds", flush=True)


if __name__ == "__main__":
    main()
