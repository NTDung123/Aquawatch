"""Create contact sheets for manual above-water / camera-view review."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("video", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--step", type=float, default=3)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
cap = cv2.VideoCapture(str(args.video))
fps, frames = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
duration = frames / fps
tiles, pages = [], []
for i in range(int(duration / args.step) + 1):
    timestamp = i * args.step
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    ok, image = cap.read()
    if not ok:
        break
    image = cv2.resize(image, (320, 180))
    cv2.rectangle(image, (0, 0), (125, 25), (0, 0, 0), -1)
    cv2.putText(image, f"{timestamp:.1f}s", (8, 19), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
    tiles.append(image)
    if len(tiles) == 16:
        sheet = np.vstack([np.hstack(tiles[j:j+4]) for j in range(0, 16, 4)])
        path = args.output / f"page_{len(pages)+1}.jpg"
        cv2.imwrite(str(path), sheet)
        pages.append(str(path))
        tiles = []
if tiles:
    tiles += [np.zeros((180, 320, 3), np.uint8)] * (16 - len(tiles))
    path = args.output / f"page_{len(pages)+1}.jpg"
    cv2.imwrite(str(path), np.vstack([np.hstack(tiles[j:j+4]) for j in range(0, 16, 4)]))
    pages.append(str(path))
cap.release()
print(json.dumps({"duration": duration, "pages": pages}))
