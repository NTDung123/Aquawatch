"""Synthetic-only reproducibility tests; NOT training or video licensing review."""
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'


def h(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image(path, seed):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 255, size=(50, 65, 3), dtype=np.uint8)
    Image.fromarray(arr).save(path)


def test_prepare_multisource(tmp_path):
    base = tmp_path / 'base'
    source = tmp_path / 'roboflow' / 'first368'
    out = tmp_path / 'multi'
    (source / 'train/images').mkdir(parents=True)
    (source / 'train/labels').mkdir(parents=True)
    (source / 'valid/images').mkdir(parents=True)
    (source / 'data.yaml').write_text('names:\n  - swimming\n  - person-out-of-water\n  - drowning\n')
    audit = {'build_completed': True, 'errors': [], 'classes': ['drowning', 'swimming'],
             'split_counts': {'train': 1, 'val': 1, 'test': 1}}
    manifest = []
    for index, split in enumerate(('train', 'val', 'test'), 1):
        d = base / 'images' / split
        l = base / 'labels' / split
        d.mkdir(parents=True)
        l.mkdir(parents=True)
        img = d / f'{split}.jpg'
        label = l / f'{split}.txt'
        image(img, index)
        label.write_text('0 0.5 0.5 0.2 0.2\n')
        manifest.append({'split': split, 'curated_image': img.relative_to(base).as_posix(),
                         'image_sha256': h(img), 'label_sha256': h(label),
                         'source_group': 'base_' + split, 'source_url': 'https://example.org'})
    (base / 'audit.json').write_text(json.dumps(audit))
    (base / 'manifest.json').write_text(json.dumps(manifest))
    (base / 'data.yaml').write_text(json.dumps({'path': str(base), 'names': ['drowning', 'swimming'],
                                               'train': 'images/train', 'val': 'images/val', 'test': 'images/test'}))
    # Three valid new source images, one with a foreign class should be skipped.
    for name, cls, seed in [('a', 0, 30), ('b', 2, 31), ('c', 1, 32), ('duplicate', 2, 1)]:
        img = source / 'train/images' / (name + '.jpg')
        if name == 'duplicate':
            img.write_bytes((base / 'images/train/train.jpg').read_bytes())
        else:
            image(img, seed)
        (source / 'train/labels' / (name + '.txt')).write_text(f'{cls} 0.5 0.5 0.2 0.2\n')
    before = {r['curated_image']: r['image_sha256'] for r in manifest}
    call = [sys.executable, str(SCRIPTS / 'prepare_multisource.py'), '--base', str(base),
            '--sources-root', str(tmp_path / 'roboflow'), '--ids', 'first368',
            '--output', str(out), '--max-per-source', '10']
    result = subprocess.run(call, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    rec = json.loads((out / 'research_record.json').read_text())
    assert rec['train_images'] == 3
    assert rec['val_images'] == 1 and rec['test_images'] == 1
    assert rec['skips']['first368_unsupported_class'] == 1
    assert rec['skips']['exact_duplicate'] >= 1
    assert (out / 'images/val/base_0000001.jpg').read_bytes() == (base / 'images/val/val.jpg').read_bytes()
    assert before == {r['curated_image']: r['image_sha256'] for r in manifest}
    assert subprocess.run(call, capture_output=True).returncode != 0  # no overwrite


def test_mobdrone_example_catalog(tmp_path):
    app = tmp_path / 'httm'
    clips = app / 'data/library/clips'
    clips.mkdir(parents=True)
    # One pre-existing reviewed clip, left unchanged by installer.
    original = clips / 'existing.mp4'
    original.write_bytes(b'tiny original metadata fixture')
    catalog = app / 'data/video_library.json'
    catalog.write_text(json.dumps({'sources': [], 'videos': [{'id': 'existing', 'name': 'Existing',
                     'path': str(original)}]}))
    # Create an actual small video in order to exercise FFmpeg and OpenCV.
    source = tmp_path / 'clip.mp4'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'mp4v'), 10, (80, 64))
    assert writer.isOpened()
    rng = np.random.default_rng(4321)
    for i in range(50):
        writer.write(rng.integers(0, 255, (64, 80, 3), dtype=np.uint8))
    writer.release()
    archive = tmp_path / 'test.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.write(source, 'videos/DJI_1234.mp4')
    command = [sys.executable, str(SCRIPTS / 'install_mobdrone_examples.py'), '--app-root', str(app),
               '--archive', str(archive), '--target', '2', '--seconds', '3', '--skip-checksum']
    plan = subprocess.run(command, capture_output=True, text=True)
    assert plan.returncode == 0, plan.stderr
    assert len(json.loads(catalog.read_text())['videos']) == 1
    install = subprocess.run(command + ['--install'], capture_output=True, text=True)
    assert install.returncode == 0, install.stderr
    after = json.loads(catalog.read_text())
    assert len(after['videos']) == 2
    new = next(v for v in after['videos'] if v['id'] != 'existing')
    assert Path(new['path']).is_file() and new['url'].startswith('/media/library/clips/')
    assert new['split'] == 'video_library_holdout_do_not_train'
    assert not new['annotations']
    assert original.read_bytes() == b'tiny original metadata fixture'
    assert (app / 'data/video_library.pre_mobdrone.json').is_file()


def test_inspect_multisource(tmp_path):
    root = tmp_path / 'exports' / 'first368'
    (root / 'train/images').mkdir(parents=True)
    (root / 'train/labels').mkdir(parents=True)
    (root / 'data.yaml').write_text('names: [drowning, swimming]\n', encoding='utf-8')
    image(root / 'train/images/sample.jpg', 99)
    (root / 'train/labels/sample.txt').write_text('0 0.5 0.5 0.4 0.3\n')
    output = tmp_path / 'contact_sheets'
    r = subprocess.run([sys.executable, str(SCRIPTS / 'inspect_multisource.py'),
                        '--sources-root', str(tmp_path / 'exports'), '--ids', 'first368',
                        '--output', str(output), '--per-source', '1'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (output / 'first368_00.jpg').is_file()
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['first368']['upstream_train_images'] == 1
    assert summary['first368']['sample_issues'] == {}
