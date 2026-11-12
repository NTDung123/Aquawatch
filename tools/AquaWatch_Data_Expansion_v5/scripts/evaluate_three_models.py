#!/usr/bin/env python3
"""Compare CURRENT/PILOT/V5 on the same frozen validation frames (no test or deployment)."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True, type=Path)
    p.add_argument('--current', required=True, type=Path)
    p.add_argument('--pilot', required=True, type=Path)
    p.add_argument('--candidate', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--imgsz', type=int, default=416)
    args = p.parse_args()
    dataset, output = args.dataset.resolve(), args.output.resolve()
    if output.exists():
        p.error('Output exists; choose a different report filename')
    record = json.loads((dataset / 'research_record.json').read_text(encoding='utf-8'))
    manifest = json.loads((dataset / 'research_manifest.json').read_text(encoding='utf-8'))
    if record.get('status') != 'completed' or not record.get('research_only'):
        p.error('Expected a completed research dataset')
    val = [r for r in manifest if r['split'] == 'val']
    if len(val) != record['val_images']:
        p.error('Validation manifest size mismatch')
    for r in val:
        img = (dataset / r['path']).resolve()
        if not img.is_relative_to(dataset) or sha(img) != r['sha256']:
            p.error(f'Validation image mismatch: {img}')
        lab = dataset / 'labels' / 'val' / (img.stem + '.txt')
        if sha(lab) != r['label_sha256']:
            p.error(f'Validation label mismatch: {lab}')
    import torch
    from ultralytics import YOLO
    device = '0' if torch.cuda.is_available() else 'cpu'
    summary = {'created_utc': datetime.now(timezone.utc).isoformat(), 'validation_only': True,
               'images': len(val), 'dataset': str(dataset), 'device': device,
               'caveats': ['Weak source annotations; not real event-level sensitivity',
                           'Dataset provenance is unverified and comparison is for research only'], 'models': {}}
    for name in ('current', 'pilot', 'candidate'):
        filename = getattr(args, name).resolve()
        if not filename.is_file():
            p.error(f'Model missing: {filename}')
        model = YOLO(str(filename))
        if model.names != {0: 'drowning', 1: 'swimming'}:
            p.error(f'{name} has unexpected class mapping: {model.names}')
        m = model.val(data=str(dataset / 'data.yaml'), split='val', imgsz=args.imgsz,
                      batch=4, device=device, workers=0, conf=.001, iou=.7,
                      half=False, plots=False, verbose=False,
                      project=str(output.parent / 'val_plots'), name=name, exist_ok=True)
        per_class = {}
        for idx, cls in enumerate(m.box.ap_class_index):
            prec, recall, ap50, ap = m.box.class_result(idx)
            per_class[model.names[int(cls)]] = {'precision': float(prec), 'recall': float(recall),
                                                 'map50': float(ap50), 'map50_95': float(ap)}
        summary['models'][name] = {'path': str(filename), 'sha256': sha(filename),
                                   'map50': float(m.box.map50), 'map50_95': float(m.box.map),
                                   'per_class': per_class}
        print(name.upper(), json.dumps(summary['models'][name], ensure_ascii=False), flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print('REPORT:', output)


if __name__ == '__main__':
    main()
