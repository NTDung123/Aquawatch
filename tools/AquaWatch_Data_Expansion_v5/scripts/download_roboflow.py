#!/usr/bin/env python3
"""Optional explicit Roboflow dataset downloads. No API key is persisted."""
import argparse
import csv
import os
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--catalog', type=Path, default=Path(__file__).resolve().parents[1] / 'catalog' / 'datasets.csv')
    ap.add_argument('--destination', type=Path, required=True)
    ap.add_argument('--ids', nargs='+', required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    with args.catalog.open(encoding='utf-8-sig', newline='') as f:
        records = {r['source_id']: r for r in csv.DictReader(f)}
    allowed = {'direct_candidate'}
    for slug in args.ids:
        if slug not in records:
            ap.error(f'Unknown source ID: {slug}')
        r = records[slug]
        if r['role'] not in allowed:
            ap.error(f'{slug} has role={r["role"]}; not a direct two-class training candidate')
        print(f'{slug}: {r["source_url"]} (version {r["version"]})')
    if args.dry_run:
        return
    key = os.environ.get('ROBOFLOW_API_KEY', '').strip()
    if not key:
        ap.error('ROBOFLOW_API_KEY missing. Set it locally, or export YOLOv8 ZIPs manually from Universe.')
    import roboflow
    rf = roboflow.Roboflow(api_key=key)
    args.destination.mkdir(parents=True, exist_ok=True)
    for slug in args.ids:
        record = records[slug]
        folder = args.destination / slug
        if folder.exists():
            print(f'Skipping existing folder {folder}. Check it before reusing.')
            continue
        print(f'Downloading {slug} from Roboflow. This may require access to the version.')
        try:
            project = rf.workspace(record['workspace']).project(record['project'])
            project.version(int(record['version'])).download('yolov8', location=str(folder))
        except Exception:
            print(f'Download failed for {slug}; remove partial folder only after inspecting its contents.')
            raise
        print('Downloaded:', folder)
    print('Finished downloads. Run prepare_multisource.py; no training was started.')


if __name__ == '__main__':
    main()
