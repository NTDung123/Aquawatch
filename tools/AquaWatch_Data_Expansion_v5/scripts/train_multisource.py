#!/usr/bin/env python3
"""Train an isolated, explicitly exploratory YOLO candidate; never deploy it."""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--exploratory-unverified', action='store_true', help='Explicitly acknowledge upstream footage rights and behavior labels are unverified')
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--epochs', type=int, default=30)
    p.add_argument('--imgsz', type=int, default=416)
    p.add_argument('--batch', type=int, default=4)
    p.add_argument('--name', default='multi_v5_experiment_01')
    p.add_argument('--project', type=Path, default=Path('data/training_exploratory'))
    args = p.parse_args()
    dataset, model, project = args.dataset.resolve(), args.model.resolve(), args.project.resolve()
    if not args.exploratory_unverified:
        p.error('Research sources have unverified original rights/behavior annotations; add --exploratory-unverified for an internal experiment')
    if args.epochs < 1 or args.batch < 1 or args.imgsz < 32:
        p.error('Invalid training parameters')
    if not model.is_file():
        p.error('Pretrained local model missing')
    if not (dataset / 'data.yaml').is_file() or not (dataset / 'research_manifest.json').is_file():
        p.error('Dataset metadata missing')
    source_record = json.loads((dataset / 'research_record.json').read_text(encoding='utf-8'))
    if source_record.get('status') != 'completed' or not source_record.get('research_only'):
        p.error('Dataset is not a completed research-only dataset')
    run = project / args.name
    if run.exists():
        p.error(f'Run already exists; use a new name: {run}')
    os.environ.setdefault('YOLO_CONFIG_DIR', str(project / '.ultralytics'))
    os.environ.setdefault('MPLCONFIGDIR', str(project / '.matplotlib'))
    from ultralytics import YOLO
    import torch
    project.mkdir(parents=True, exist_ok=True)
    run.mkdir()
    record = {'status': 'running', 'started_utc': utc(), 'experiment_only': True,
              'do_not_deploy': True, 'args': sys.argv, 'dataset': str(dataset),
              'dataset_sha256': digest(dataset / 'research_record.json'),
              'manifest_sha256': digest(dataset / 'research_manifest.json'),
              'base_model': str(model), 'base_model_sha256': digest(model),
              'cuda': torch.cuda.is_available(),
              'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
              'limitations': source_record['warnings']}
    dest = run / 'exploratory_training_record.json'
    dest.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    try:
        model_obj = YOLO(str(model))
        metrics = model_obj.train(data=str(dataset / 'data.yaml'), epochs=args.epochs,
                                  imgsz=args.imgsz, batch=args.batch,
                                  device='0' if torch.cuda.is_available() else 'cpu',
                                  workers=0, amp=False, seed=42, deterministic=True,
                                  project=str(project), name=args.name, exist_ok=True,
                                  optimizer='auto', save=True, plots=True,
                                  degrees=3, translate=.05, scale=.25,
                                  flipud=0, fliplr=.5, mosaic=.25, mixup=0,
                                  verbose=True)
        best = run / 'weights' / 'best.pt'
        last = run / 'weights' / 'last.pt'
        if not best.is_file() or not last.is_file() or not (run / 'results.csv').is_file():
            raise RuntimeError('No best/last checkpoint or optimizer results found')
        record.update(status='completed', finished_utc=utc(), best_model=str(best),
                      best_sha256=digest(best), last_sha256=digest(last),
                      validation_metrics=getattr(metrics, 'results_dict', {}))
        dest.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
        print(json.dumps({'status': 'completed', 'research_only': True, 'best': str(best)}))
    except Exception as exc:
        record.update(status='failed', finished_utc=utc(), error=str(exc))
        dest.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
