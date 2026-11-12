#!/usr/bin/env python3
"""Build an isolated, UNVERIFIED multi-source YOLO research dataset for AquaWatch.

This preserves the base audited validation/test byte-for-byte, imports ONLY
upstream train images, rejects unsupported classes, and removes exact/near
duplicates. It does NOT mark third-party annotations or rights as verified.
Never feed the result to AquaWatch's audited training/promote pipeline.
"""
import argparse
import csv
import hashlib
import json
import math
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CLASSES = ['drowning', 'swimming']
NAMES = {'drowning': 0, 'drown': 0, 'swim': 1, 'swimming': 1}
EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}


def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(piece)
    return h.hexdigest()


def dhash(path):
    from PIL import Image
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        pix = list(im.convert('L').resize((9, 8)).getdata())
    n = 0
    for row in range(8):
        for col in range(8):
            n = (n << 1) | (pix[row * 9 + col] > pix[row * 9 + col + 1])
    return n


def safe(root, rel):
    root = root.resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root):
        raise ValueError(f'Unsafe relative path: {rel}')
    return p


def load_yaml(path):
    import yaml
    with path.open(encoding='utf-8-sig') as f:
        return yaml.safe_load(f)


def names_from_config(config):
    names = config.get('names')
    if isinstance(names, dict):
        names = [names.get(i, names.get(str(i))) for i in range(len(names))]
    if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
        raise ValueError(f'Invalid classes in source data.yaml: {names}')
    return names


def parse_boxes(label_path, mapping):
    lines = []
    text = label_path.read_text(encoding='utf-8-sig')
    if not text.strip():
        return None, 'empty_label'
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            return None, 'not_5_value_bbox'
        try:
            source_id = int(parts[0])
            if str(source_id) != parts[0]:
                return None, 'noninteger_class_id'
            vals = [float(x) for x in parts[1:]]
        except ValueError:
            return None, 'invalid_number'
        if source_id not in mapping:
            return None, 'unsupported_class'
        x, y, w, h = vals
        if (not all(math.isfinite(v) and 0 <= v <= 1 for v in vals)
                or w <= 0 or h <= 0 or x - w / 2 < -0.01 or y - h / 2 < -0.01
                or x + w / 2 > 1.01 or y + h / 2 > 1.01):
            return None, 'invalid_bbox'
        lines.append(f'{mapping[source_id]} {x:.7f} {y:.7f} {w:.7f} {h:.7f}')
    return lines if lines else None, None


def locate_source(root):
    direct = root / 'data.yaml'
    if direct.is_file():
        return root
    paths = [p.parent for p in root.glob('*/data.yaml') if p.is_file()]
    if len(paths) == 1:
        return paths[0]
    raise ValueError(f'Cannot locate unambiguous data.yaml in {root}; extract a YOLOv8 export first')


def scan_source(source_root, source_id):
    source_root = locate_source(source_root)
    config = load_yaml(source_root / 'data.yaml')
    names = names_from_config(config)
    mapping = {}
    for idx, name in enumerate(names):
        normal = ' '.join(name.lower().strip().replace('_', ' ').replace('-', ' ').split())
        if normal in NAMES:
            mapping[idx] = NAMES[normal]
    if not 0 in mapping.values() or not 1 in mapping.values():
        raise ValueError(f'{source_id}: missing both direct canonical classes: {names}')
    roots = [source_root / 'train' / 'images', source_root / 'images' / 'train']
    image_root = next((p for p in roots if p.is_dir()), None)
    if image_root is None:
        raise ValueError(f'{source_id}: cannot find train/images or images/train')
    images = [p for p in image_root.rglob('*') if p.is_file() and p.suffix.lower() in EXTS]
    images.sort(key=lambda p: hashlib.sha256(p.relative_to(image_root).as_posix().encode()).hexdigest())
    return source_root, image_root, images, names, mapping


def label_for(source_root, image_root, image):
    rel = image.relative_to(image_root)
    layout = image_root.relative_to(source_root).parts
    if layout == ('train', 'images'):
        label = source_root / 'train' / 'labels' / rel.with_suffix('.txt')
    else:
        label = source_root / 'labels' / 'train' / rel.with_suffix('.txt')
    return label


def base_data(base):
    a = json.loads((base / 'audit.json').read_text(encoding='utf-8'))
    m = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    c = load_yaml(base / 'data.yaml')
    if not a.get('build_completed') or a.get('errors') or a.get('classes') != CLASSES:
        raise ValueError('Base dataset is not a completed two-class audit')
    if c.get('names') != CLASSES or not a.get('split_counts', {}).get('train') or not a.get('split_counts', {}).get('val'):
        raise ValueError('Base YAML or splits are inconsistent')
    rows = []
    for i, r in enumerate(m):
        split = r['split']
        if split not in {'train', 'val', 'test'}:
            raise ValueError('Invalid base split')
        img = safe(base, r['curated_image'])
        label = safe(base, f'labels/{split}/{img.stem}.txt')
        if not img.is_file() or not label.is_file():
            raise ValueError(f'Missing base image/label at manifest row {i}')
        if sha_file(img) != r['image_sha256'] or sha_file(label) != r['label_sha256']:
            raise ValueError(f'Base bytes changed since audit: {img.name}')
        rows.append((r, img, label))
    return a, m, c, rows


def write_image(output, img, labels, stem, split='train'):
    dst_img = output / 'images' / split / (stem + img.suffix.lower())
    dst_lbl = output / 'labels' / split / (stem + '.txt')
    dst_img.parent.mkdir(parents=True, exist_ok=True)
    dst_lbl.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(img, dst_img)
    if isinstance(labels, Path):
        shutil.copy2(labels, dst_lbl)
    else:
        dst_lbl.write_text('\n'.join(labels) + '\n', encoding='utf-8')
    return dst_img, dst_lbl


def build(args):
    base, output, source_home = args.base.resolve(), args.output.resolve(), args.sources_root.resolve()
    if output.exists():
        raise ValueError(f'Output already exists; refusing overwrite: {output}')
    if output.is_relative_to(base) or (source_home.is_dir() and output.is_relative_to(source_home)):
        raise ValueError('Output must be outside the source/base dataset')
    audit, manifest, conf, base_rows = base_data(base)
    selected = args.ids or []
    with args.catalog.open(encoding='utf-8-sig', newline='') as stream:
        source_info = {r['source_id']: r for r in csv.DictReader(stream)}
    for slug in selected:
        if slug not in source_info or source_info[slug]['role'] != 'direct_candidate':
            raise ValueError(f'{slug} is not an approved direct-class import candidate in the source catalog')
    if not selected and not args.pilot:
        raise ValueError('Choose at least one --ids source or --pilot path')
    sources = []
    for source_id in selected:
        if not source_id.replace('_', '').isalnum():
            raise ValueError('Invalid source_id: ' + source_id)
        folder = source_home / source_id
        if not folder.is_dir():
            raise ValueError(f'Missing downloaded source: {folder}')
        sources.append((source_id, *scan_source(folder, source_id)))
    pilot_path = args.pilot.resolve() if args.pilot else None
    pilot_rows = []
    if pilot_path:
        pm = json.loads((pilot_path / 'pilot_manifest.json').read_text(encoding='utf-8'))
        pilot_rows = [p for p in pm if p.get('origin') == 'lifeguard_spotcheck' and p.get('split') == 'train']
        if not pilot_rows:
            raise ValueError('Pilot dataset has no Lifeguard frame records')
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'research_only': True,
              'not_for_deployment': True, 'rights_verified': False,
              'annotation_temporal_validation': 'not_performed',
              'base_dataset': str(base), 'base_manifest_sha256': sha_file(base / 'manifest.json'),
              'base_audit_sha256': sha_file(base / 'audit.json'), 'source_dataset_origins': [],
              'counts': {}, 'skips': {}, 'dedup': {'dhash_max_hamming': args.dhash_threshold},
              'warnings': ['All external datasets are uploader-labeled; source-video rights and label correctness require review.',
                           'No automatic conversion of person/person_in_water to drowning or swimming.',
                           'Existing validation/test samples stay unchanged; this does not establish unseen source independence.',
                           'External dataset test/validation images are never imported into train.',
                           'Do not promote a research-only checkpoint via scripts/promote_model.py.']}
    output.mkdir(parents=True)
    stats, skipped, ledger = Counter(), Counter(), []
    seen_sha = set()
    seen_dhash = []
    holdout_dhash = []
    try:
        for idx, (r, img, label) in enumerate(base_rows):
            split = r['split']
            out_img, out_lbl = write_image(output, img, label, f'base_{idx:07d}', split)
            h = r['image_sha256']
            dh = dhash(img)
            seen_sha.add(h)
            seen_dhash.append(dh)
            if split != 'train':
                holdout_dhash.append(dh)
            stats[f'base_{split}'] += 1
            ledger.append({'split': split, 'origin': 'audited_surface_v4',
                           'source_group': r.get('source_group', ''), 'source_url': r.get('source_url', ''),
                           'path': out_img.relative_to(output).as_posix(), 'sha256': h,
                           'label_sha256': sha_file(out_lbl)})

        def add_new(image, labels, origin, group, url):
            try:
                h = sha_file(image)
                if h in seen_sha:
                    skipped['exact_duplicate'] += 1
                    return
                dh = dhash(image)
            except Exception:
                skipped['cannot_decode'] += 1
                return
            if any((dh ^ other).bit_count() <= args.dhash_threshold for other in holdout_dhash):
                skipped['near_frozen_holdout'] += 1
                return
            if any((dh ^ other).bit_count() <= args.dhash_threshold for other in seen_dhash):
                skipped['near_train_duplicate'] += 1
                return
            seen_sha.add(h)
            seen_dhash.append(dh)
            stem = f'extra_{len(ledger):07d}_{h[:12]}'
            dst_img, dst_lbl = write_image(output, image, labels, stem)
            ledger.append({'split': 'train', 'origin': origin, 'source_group': group,
                           'source_url': url, 'path': dst_img.relative_to(output).as_posix(),
                           'sha256': h, 'label_sha256': sha_file(dst_lbl),
                           'label_status': 'original_uploader_weak', 'rights_status': 'not_independently_verified'})
            stats[f'extra_{origin}'] += 1

        if pilot_path:
            for row in pilot_rows:
                image = safe(pilot_path, row['image'])
                label = safe(pilot_path, 'labels/train/' + image.stem + '.txt')
                if sha_file(image) != row['sha256'] or sha_file(label) != row['label_sha256']:
                    raise ValueError('Pilot image/label checksum mismatch')
                boxes, reason = parse_boxes(label, {0: 0, 1: 1})
                if boxes is None:
                    skipped['pilot_' + (reason or 'invalid')] += 1
                    continue
                add_new(image, boxes, 'lifeguard_pilot', row['source_group'], row['source_url'])
            report['source_dataset_origins'].append({'id': 'lifeguard_pilot', 'status': 'YouTube footage rights unverified',
                                                     'chosen_frames': len(pilot_rows)})

        for source_id, folder, image_root, images, names, mapping in sources:
            source_meta = source_info[source_id]
            report['source_dataset_origins'].append({'id': source_id, 'folder': str(folder), 'source_page': source_meta['source_url'],
                                                     'uploader_license_claim': source_meta['declared_license'], 'original_classes': names,
                                                     'direct_class_id_mapping': mapping, 'total_upstream_train_images': len(images),
                                                     'review_status': 'unreviewed_upstream_labels'})
            chosen = images[:args.max_per_source]
            for image in chosen:
                label = label_for(folder, image_root, image)
                if not label.is_file():
                    skipped[source_id + '_missing_label'] += 1
                    continue
                lines, reason = parse_boxes(label, mapping)
                if lines is None:
                    skipped[source_id + '_' + (reason or 'invalid')] += 1
                    continue
                add_new(image, lines, 'rf_' + source_id, 'rf_' + source_id + '_all_unknown_video_origins',
                        source_meta['source_url'])
            stats['upstream_examined_' + source_id] = len(chosen)

        total_new = sum(v for k, v in stats.items() if k.startswith('extra_'))
        if total_new == 0:
            raise ValueError('No valid new images survived label and duplicate checks')
        config = {'path': output.as_posix(), 'train': 'images/train', 'val': 'images/val',
                  'test': 'images/test', 'names': CLASSES}
        (output / 'data.yaml').write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
        (output / 'research_manifest.json').write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding='utf-8')
        report['counts'] = dict(stats)
        report['skips'] = dict(skipped)
        report['train_images'] = stats['base_train'] + total_new
        report['val_images'] = stats['base_val']
        report['test_images'] = stats['base_test']
        report['frozen_holdout_count'] = len(holdout_dhash)
        report['status'] = 'completed'
        (output / 'research_record.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'dataset': str(output), 'train': report['train_images'],
                          'val': report['val_images'], 'test': report['test_images'],
                          'added': total_new, 'skipped': dict(skipped), 'research_only': True}, indent=2))
    except Exception:
        # A partial output is not a valid research dataset. Keep it as evidence,
        # but do not create a completed record.
        (output / 'FAILED.txt').write_text('Build interrupted; do not train using this directory.\n', encoding='utf-8')
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', required=True, type=Path)
    p.add_argument('--catalog', type=Path, default=Path(__file__).resolve().parents[1] / 'catalog' / 'datasets.csv')
    p.add_argument('--sources-root', required=True, type=Path)
    p.add_argument('--ids', nargs='*', default=[])
    p.add_argument('--pilot', type=Path, help='Optional previous pilot research dataset (adds only 147 sampled Lifeguard frames)')
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--max-per-source', type=int, default=400)
    p.add_argument('--dhash-threshold', type=int, default=3)
    args = p.parse_args()
    if args.max_per_source <= 0 or not 0 <= args.dhash_threshold <= 8:
        p.error('Invalid selection/dedup parameters')
    build(args)


if __name__ == '__main__':
    main()
