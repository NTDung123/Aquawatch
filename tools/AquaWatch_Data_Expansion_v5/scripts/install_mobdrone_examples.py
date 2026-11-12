#!/usr/bin/env python3
"""Add real MOBDrone source videos as browser-friendly AquaWatch examples.

Uses the Zenodo archive of 66 aerial source videos (NOT fake drowning labels).
Keeps originals locally and adds only enough preview clips to bring the library
to the requested number; never edits the existing 13 videos or their files.
The archive must be downloaded by the user and pass the official MD5 check.
Short/unreadable sources are skipped and replaced with reserve candidates.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://zenodo.org/records/5996890'
ARCHIVE_URL = 'https://zenodo.org/records/5996890/files/MOBDrone_videos.zip?download=1'
MD5 = '250c19fdd6fb0b5aa5fa43e5ad140306'
VIDEO_SUFFIXES = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
CREDIT = ('Donato Cafarelli, Luca Ciampi, Lucia Vadicamo, Claudio Gennaro, '
          'Andrea Berton, Marco Paterni, Chiara Benvenuti, Mirko Passera, Fabrizio Falchi')


def filehash(path, alg='sha256'):
    h = hashlib.new(alg)
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def probe(path):
    import cv2
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError(f'Cannot open video {path}')
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ok, frame = cap.read()
        if not ok or fps <= 0 or count <= 0:
            raise ValueError(f'Corrupted/empty video: {path}')
        height, width = frame.shape[:2]
        return {'fps': fps, 'frames': count, 'duration': count / fps, 'width': width, 'height': height}
    finally:
        cap.release()


def valid_entries(archive):
    entries = []
    for e in archive.infolist():
        path = Path(e.filename)
        if e.is_dir() or path.suffix.lower() not in VIDEO_SUFFIXES or '__MACOSX' in path.parts:
            continue
        if '..' in path.parts or e.filename.startswith('/') or e.filename.startswith('\\'):
            continue
        if e.file_size <= 10000:
            continue
        entries.append(e)
    return sorted(entries, key=lambda e: e.filename.lower())


def get_catalog(path):
    if not path.is_file():
        raise ValueError('AquaWatch video_library.json does not exist; run scripts/fetch_video_library.py first')
    doc = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(doc.get('videos'), list) or not isinstance(doc.get('sources'), list):
        raise ValueError('Unexpected AquaWatch catalog schema')
    return doc


def choose(existing, entries, target):
    already = {v['id'] for v in existing}
    needed = max(0, target - len(existing))
    candidates = []
    for info in entries:
        stem = re.sub(r'[^0-9a-zA-Z_-]+', '_', Path(info.filename).stem).strip('_')[:45] or 'video'
        uid = hashlib.sha256(info.filename.encode('utf-8')).hexdigest()[:10]
        vid = f'mobdrone_{stem}_{uid}'.lower()
        if vid in already:
            continue
        candidates.append((info, vid))
    if needed > len(candidates):
        raise ValueError(f'Only {len(candidates)} new videos in archive, need {needed}')
    if needed == 0:
        return [], 0
    # Spread the first choices through the source collection. Keep all remaining
    # entries as fallback candidates for originals that are too short/unreadable.
    indices = [(i * len(candidates)) // needed for i in range(needed)]
    selected = set(indices)
    order = indices + [i for i in range(len(candidates)) if i not in selected]
    return [candidates[i] for i in order], needed


def extract_member(archive, info, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        return
    temp = target.with_name(target.name + '.partial')
    with archive.open(info, 'r') as src, temp.open('wb') as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    if temp.stat().st_size != info.file_size:
        temp.unlink(missing_ok=True)
        raise ValueError('Uncompressed video length mismatch for ' + info.filename)
    temp.replace(target)


def transcode(ffmpeg, raw, dest, seconds):
    detail = probe(raw)
    if detail['duration'] < 2:
        raise ValueError('Original video too short')
    start = min(5.0, max(0.0, detail['duration'] * .12))
    length = min(float(seconds), max(1.0, detail['duration'] - start))
    dest.parent.mkdir(parents=True, exist_ok=True)
    encoded = dest.with_name(dest.stem + '.part.mp4')
    if encoded.exists():
        encoded.unlink()
    command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{start:.3f}', '-i', str(raw),
               '-t', f'{length:.3f}', '-vf', "scale='min(1280,iw)':-2", '-r', '30', '-an',
               '-c:v', 'libx264', '-preset', 'fast', '-crf', '21', '-pix_fmt', 'yuv420p',
               '-movflags', '+faststart', str(encoded)]
    try:
        subprocess.run(command, check=True)
        info = probe(encoded)
        if info['duration'] > 1800 or encoded.stat().st_size > 1024**3:
            raise ValueError('AquaWatch preview video exceeds upload limits')
        encoded.replace(dest)
        return info, start
    finally:
        # Do not leave a broken preview on FFmpeg/decode errors.
        encoded.unlink(missing_ok=True)


def thumbnail(video, poster):
    import cv2
    cap = cv2.VideoCapture(str(video))
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f'Failed thumbnail decode: {video}')
        if not cv2.imwrite(str(poster), frame):
            raise ValueError(f'Failed thumbnail output: {poster}')
    finally:
        cap.release()


def run(args):
    archive_file, root = args.archive.resolve(), args.app_root.resolve()
    library = root / 'data' / 'library'
    catalog_file = root / 'data' / 'video_library.json'
    cat = get_catalog(catalog_file)
    clips_folder = library / 'clips'
    # Existing missing clips are not playable, so do not count them towards 50.
    existing = [r for r in cat['videos'] if Path(r['path']).is_file() and Path(r['path']).resolve().is_relative_to(clips_folder.resolve())]
    if args.target < len(existing):
        raise ValueError('Target lower than existing clip count; do not delete existing catalog videos')
    if not archive_file.is_file():
        raise FileNotFoundError(f'{archive_file} is missing. Download official archive at {ARCHIVE_URL}')
    if not args.skip_checksum:
        current = filehash(archive_file, 'md5')
        if current != MD5:
            raise ValueError(f'Official MOBDrone ZIP MD5 mismatch: {current}')
    with zipfile.ZipFile(archive_file) as z:
        # Each selected member is CRC-checked by zipfile during extraction.
        # Avoid scanning all 5.5 GB twice before processing.
        entries = valid_entries(z)
        queued, needed = choose(existing, entries, args.target)
        print(json.dumps({'existing_playable': len(existing), 'archive_videos': len(entries),
                          'new_selected': needed, 'backup_candidates': len(queued) - needed,
                          'target_total': args.target,
                          'new_video_entries': [e.filename for e, _ in queued[:needed]]}, indent=2))
        if not args.install:
            print('Planning only. Add --install to create local video previews and register them.')
            return
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        raw_folder = library / 'raw' / 'mobdrone'
        existing_ids = {item['id'] for item in cat['videos']}
        all_videos = list(cat['videos'])
        all_sources = list(cat['sources'])
        skipped = []
        added = 0
        for index, (entry, video_id) in enumerate(queued, 1):
            if added >= needed:
                break
            raw = raw_folder / (video_id + Path(entry.filename).suffix.lower())
            preview = clips_folder / (video_id + '.mp4')
            poster = clips_folder / (video_id + '.jpg')
            try:
                # An interrupted run might have already extracted/transcoded this video.
                extract_member(z, entry, raw)
                if not preview.exists():
                    metadata, begin = transcode(ffmpeg, raw, preview, args.seconds)
                else:
                    metadata, begin = probe(preview), None
                if not poster.exists():
                    thumbnail(preview, poster)
                source_hash = filehash(raw)
            except (ValueError, subprocess.CalledProcessError) as error:
                # A short or badly encoded source must not block the other 65 videos.
                reason = f'{type(error).__name__}: {error}'
                skipped.append({'source': entry.filename, 'error': reason})
                print(f'SKIP {entry.filename}: {reason}', flush=True)
                continue
            source_key = 'MOBDrone:' + entry.filename
            if not any(s.get('id') == source_key for s in all_sources):
                all_sources.append({'id': source_key, 'source_url': URL,
                                    'source_group': 'mobdrone_single_uav_source_campaign',
                                    'credit': CREDIT, 'license': 'Creative Commons Attribution (per authors)',
                                    'license_url': URL, 'source_original_name': entry.filename,
                                    'source_sha256': source_hash, 'source_path': str(raw)})
            if video_id not in existing_ids:
                all_videos.append({'id': video_id,
                    'name': f'MOBDrone - {Path(entry.filename).stem} (aerial, person in water)',
                    'path': str(preview.resolve()),
                    'url': '/media/library/clips/' + preview.name,
                    'thumbnail_url': '/media/library/clips/' + poster.name,
                    'source_id': source_key, 'source_group': 'mobdrone_single_uav_source_campaign',
                    'source_url': URL, 'source_original_name': entry.filename,
                    'source_sha256': source_hash, 'sha256': filehash(preview),
                    'size_bytes': preview.stat().st_size, **metadata,
                    'license': 'Creative Commons Attribution (per original dataset)', 'license_url': URL,
                    'credit': CREDIT, 'environment': 'beach', 'camera_mode': 'ptz',
                    'camera_type': 'moving_aerial_drone', 'camera_support': 'secondary_aerial_domain',
                    'scenario': 'open_water_unlabeled', 'nature': 'staged_man_overboard_simulation',
                    'above_water': True, 'view': 'aerial_above_water_from_source_description',
                    'review_status': 'metadata_only_needs_local_clip_review',
                    'review_notes': 'Original MOBDrone aerial videos; no drowning/swimming behavior ground truth. Check clips in player. No claim of clinical drowning.',
                    'annotations': [], 'split': 'video_library_holdout_do_not_train',
                    'source_start': begin, 'changes': 'Original copied unchanged to raw; H.264 30fps short preview extracted; audio removed.',
                    'independence': 'Never imported into local AquaWatch training by this package.'})
                existing_ids.add(video_id)
            added += 1
            print(f'{added}/{needed} ready: {video_id}', flush=True)
        target_file = catalog_file.with_name('video_library.pre_mobdrone.json')
        if not target_file.exists():
            shutil.copy2(catalog_file, target_file)
        cat['sources'] = all_sources
        cat['videos'] = all_videos
        cat['mobdrone_added_utc'] = datetime.now(timezone.utc).isoformat()
        cat['mobdrone_source_note'] = 'Metadata and attribution follow Zenodo 5996890. Person in water does not imply drowning.'
        temporary = catalog_file.with_suffix('.tmp')
        temporary.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(catalog_file)
        result = {'registered': len(all_videos), 'target': args.target,
                  'added_this_run': added, 'skipped': skipped,
                  'reached_target': len(all_videos) >= args.target,
                  'catalog': str(catalog_file),
                  'originals': str(raw_folder), 'previews': str(clips_folder)}
        report = library / 'mobdrone_import_report.json'
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({**result, 'report': str(report)}, ensure_ascii=False, indent=2), flush=True)
        if len(all_videos) < args.target:
            print('WARNING: fewer playable originals were available than requested; catalog saved with current valid entries.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-root', type=Path, required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--target', type=int, default=50)
    p.add_argument('--seconds', type=int, default=40)
    p.add_argument('--install', action='store_true')
    p.add_argument('--skip-checksum', action='store_true', help='Only for local test archives, never use for official source')
    args = p.parse_args()
    if args.target < 1 or not 3 <= args.seconds <= 300:
        p.error('Target must be positive and clip length 3..300 seconds')
    run(args)


if __name__ == '__main__':
    main()
