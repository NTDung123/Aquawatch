#!/usr/bin/env python3
"""Render visual contact sheets of external YOLO exports before choosing sources."""
import argparse
import json
from collections import Counter
from pathlib import Path

from prepare_multisource import scan_source, label_for, parse_boxes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources-root', required=True, type=Path)
    parser.add_argument('--ids', required=True, nargs='+')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--per-source', type=int, default=48)
    args = parser.parse_args()
    if not 1 <= args.per_source <= 200:
        parser.error('per-source must be in 1..200')
    from PIL import Image, ImageDraw, ImageFont
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = {}
    tile_w, tile_h, cols, rows = 250, 205, 6, 4
    for sid in args.ids:
        source, image_root, images, names, mapping = scan_source(args.sources_root / sid, sid)
        selected = [images[i * len(images) // min(len(images), args.per_source)]
                    for i in range(min(len(images), args.per_source))]
        pages, reasons = [], Counter()
        for page_idx in range((len(selected) + cols * rows - 1) // (cols * rows)):
            sheet = Image.new('RGB', (tile_w * cols, tile_h * rows), '#26333c')
            draw = ImageDraw.Draw(sheet)
            for slot, img_path in enumerate(selected[page_idx * cols * rows:(page_idx + 1) * cols * rows]):
                gx, gy = slot % cols * tile_w, slot // cols * tile_h
                lbl = label_for(source, image_root, img_path)
                labels, reason = parse_boxes(lbl, mapping) if lbl.exists() else (None, 'missing_label')
                if reason:
                    reasons[reason] += 1
                try:
                    with Image.open(img_path) as original:
                        img = original.convert('RGB').resize((tile_w - 8, tile_h - 40))
                    painter = ImageDraw.Draw(img)
                    if labels:
                        for line in labels:
                            cl, xc, yc, w, h = map(float, line.split())
                            x1 = (xc - w / 2) * img.width
                            y1 = (yc - h / 2) * img.height
                            x2 = (xc + w / 2) * img.width
                            y2 = (yc + h / 2) * img.height
                            color = '#ff5151' if int(cl) == 0 else '#37c4ff'
                            painter.rectangle((x1, y1, x2, y2), outline=color, width=2)
                    sheet.paste(img, (gx + 4, gy + 4))
                except Exception as exc:
                    reasons['image_decode_error'] += 1
                    reason = 'decode error'
                draw.text((gx + 4, gy + tile_h - 34), img_path.name[:33], fill='white')
                draw.text((gx + 4, gy + tile_h - 18), reason or f'{len(labels)} boxes', fill='#ffba5e' if reason else '#a4d4bf')
            dest = output / f'{sid}_{page_idx:02d}.jpg'
            sheet.save(dest, quality=90)
            pages.append(dest.name)
        result[sid] = {'upstream_train_images': len(images), 'original_classes': names,
                       'mapping': mapping, 'contact_sheets': pages, 'sample_issues': dict(reasons),
                       'warning': 'Spot-check only; does not establish source rights, complete camera viewpoint, or behavior ground truth'}
        print(sid, 'pages', len(pages), 'samples', len(selected), 'issues', dict(reasons), flush=True)
    (output / 'summary.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Open previews at', output)


if __name__ == '__main__':
    main()
