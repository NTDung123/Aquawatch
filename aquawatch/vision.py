import hashlib
import json
import time
import cv2
import numpy as np
from .settings import DATA, MODEL, MODEL_SHA256, selected_model


class VisionEngine:
    def __init__(self):
        import torch
        from ultralytics import YOLO
        # Prefer the locally fine-tuned checkpoint only when its training record exists.
        self.path = selected_model()
        self.sha256 = hashlib.sha256(self.path.read_bytes()).hexdigest()
        record_path = DATA / "training_record.json"
        record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
        self.deployment = record.get("deployment", {}) if record.get("best_model_sha256") == self.sha256 else {}
        self.preprocessing = self.deployment.get("preprocessing", "letterbox")
        if self.path == MODEL and hashlib.sha256(MODEL.read_bytes()).hexdigest() != MODEL_SHA256:
            raise RuntimeError("Checkpoint checksum không khớp. Chạy scripts/fetch_assets.py.")
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(str(self.path))
        self.names = self.model.names
        if set(self.names.values()) != {"drowning", "swimming"}:
            raise RuntimeError("Model không có đúng taxonomy drowning/swimming")
        self.rejected = 0
        self.inference_ms = []
        started = time.perf_counter()
        # Initialize kernels before the source clock starts; warmup outputs are never published.
        self.model.predict(np.zeros((640, 640, 3), dtype=np.uint8), conf=.99, imgsz=640,
                           device=self.device, agnostic_nms=True, verbose=False)
        self.warmup_seconds = time.perf_counter() - started

    def predict(self, frame, confidence):
        begin = time.perf_counter()
        image = cv2.resize(frame, (640, 640)) if self.preprocessing == "stretch640" else frame
        result = self.model.predict(image, conf=confidence, imgsz=640, device=self.device, agnostic_nms=True, verbose=False)[0]
        self.inference_ms.append((time.perf_counter() - begin) * 1000)
        h, w = image.shape[:2]
        detections = []
        for box in result.boxes:
            name = self.names[int(box.cls.item())].lower()
            if name not in ("drowning", "swimming"):
                continue
            coords = box.xyxy[0].cpu().tolist()
            coords = [float(np.clip(v / (w if i % 2 == 0 else h), 0, 1)) for i, v in enumerate(coords)]
            area = (coords[2] - coords[0]) * (coords[3] - coords[1])
            if area > .85 or area < .00002:
                self.rejected += 1
                continue
            detections.append({"box": coords, "label": name, "confidence": round(float(box.conf.item()), 4)})
        return detections


class CameraMotion:
    def __init__(self, water_polygon=None):
        self.previous = None
        self.histogram = None
        self.water_polygon = water_polygon or []

    def update(self, frame, previous_boxes):
        gray = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
        cv2.normalize(hist, hist)
        cut = self.histogram is not None and cv2.compareHist(self.histogram, hist, cv2.HISTCMP_BHATTACHARYYA) > .65
        known, moving, displacement = False, False, 0.0
        if self.previous is not None and not cut:
            mask = np.full_like(gray, 255)
            if len(self.water_polygon) >= 3:
                points = np.array([[int(x * 320), int(y * 180)] for x, y in self.water_polygon], dtype=np.int32)
                cv2.fillPoly(mask, [points], 0)
            for box in previous_boxes:
                x1, y1, x2, y2 = [int(v * (320 if i % 2 == 0 else 180)) for i, v in enumerate(box)]
                cv2.rectangle(mask, (x1, y1), (x2, y2), 0, -1)
            points = cv2.goodFeaturesToTrack(self.previous, 150, .03, 7, mask=mask)
            if points is not None and len(points) >= 12:
                new, status, _ = cv2.calcOpticalFlowPyrLK(self.previous, gray, points, None)
                good = status.reshape(-1) == 1
                if int(good.sum()) >= 10:
                    affine, inliers = cv2.estimateAffinePartial2D(points[good], new[good], method=cv2.RANSAC, ransacReprojThreshold=2)
                    if affine is not None and inliers is not None and float(inliers.mean()) >= .55:
                        displacement = float(np.linalg.norm(affine[:, 2]))
                        rotation = abs(float(np.arctan2(affine[1, 0], affine[0, 0])))
                        known = True
                        moving = displacement > 2.5 or rotation > .015
        self.previous, self.histogram = gray, hist
        return {"camera_moving": moving or cut, "scene_cut": bool(cut), "motion_known": known, "displacement_px": round(displacement, 2)}
