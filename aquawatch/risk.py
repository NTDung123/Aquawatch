import math
from dataclasses import dataclass


def iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = lambda x: max(0, x[2] - x[0]) * max(0, x[3] - x[1])
    return intersection / max(1e-9, area(a) + area(b) - intersection)


def inside(point, polygon):
    if len(polygon) < 3:
        return False
    x, y = point
    hit = False
    j = len(polygon) - 1
    for k, (px, py) in enumerate(polygon):
        qx, qy = polygon[j]
        if (py > y) != (qy > y) and x < (qx - px) * (y - py) / (qy - py) + px:
            hit = not hit
        j = k
    return hit


@dataclass
class Track:
    id: int
    box: list
    first: float
    seen: float
    last_update: float
    evidence: float = 0
    clear: float = 0
    level: int = 0
    confidence: float = 0
    label: str = "swimming"


class RiskEngine:
    """Engineering baseline. Thresholds require calibration on labeled target footage."""

    def __init__(self, polygon=None, sample_fps=5):
        self.tracks = {}
        self.counter = 0
        self.polygon = polygon or []
        self.step = 1 / sample_fps
        self.visibility_valid = True

    def update(self, time, detections, camera_moving=False, scene_cut=False, motion_known=True):
        if camera_moving or scene_cut:
            self.visibility_valid = False
            self.tracks.clear()
        matched = set()
        output = []
        for detection in sorted(detections, key=lambda d: d["confidence"], reverse=True):
            candidates = []
            for track in self.tracks.values():
                gap = time - track.seen
                if track.id in matched or gap > 12:
                    continue
                overlap = iou(track.box, detection["box"])
                ac = [(track.box[0] + track.box[2]) / 2, (track.box[1] + track.box[3]) / 2]
                bc = [(detection["box"][0] + detection["box"][2]) / 2, (detection["box"][1] + detection["box"][3]) / 2]
                distance = math.dist(ac, bc)
                if (gap <= 1 and (overlap > .15 or distance < .06)) or (gap > 1 and overlap > .5 and distance < .03):
                    candidates.append((overlap - distance, track))
            if candidates:
                track = max(candidates, key=lambda x: x[0])[1]
            else:
                self.counter += 1
                track = Track(self.counter, detection["box"], time, time, time - self.step)
                self.tracks[track.id] = track
            dt = min(self.step, max(0, time - track.last_update))
            dangerous = detection["label"] == "drowning"
            if dangerous:
                track.evidence = min(12, track.evidence + dt)
                track.clear = 0
            else:
                track.evidence = max(0, track.evidence - dt * .65)
                track.clear += dt
            target = 3 if track.evidence >= 6 else 2 if track.evidence >= 2 else 1 if track.evidence >= .6 else 0
            if target >= track.level or track.clear >= 2:
                track.level = target
            track.box = detection["box"]
            track.seen = track.last_update = time
            track.confidence = detection["confidence"]
            track.label = detection["label"]
            matched.add(track.id)
            reasons = []
            if track.level:
                reasons.append(f"Mô hình gán nhãn nghi nguy cơ; tích lũy {track.evidence:.1f}s")
            output.append({**detection, "track_id": track.id, "level": track.level, "reasons": reasons, "inferred": False})
        for track in list(self.tracks.values()):
            if track.id in matched:
                continue
            missing = time - track.seen
            center = ((track.box[0] + track.box[2]) / 2, (track.box[1] + track.box[3]) / 2)
            edge = min(center[0], center[1], 1 - center[0], 1 - center[1]) < .06
            occluded = any(iou(track.box, d["box"]) > .1 for d in detections)
            eligible = self.visibility_valid and motion_known and not camera_moving and not scene_cut and not edge and not occluded
            unresolved = inside(center, self.polygon) and track.seen - track.first >= 2
            if eligible and unresolved and missing >= 3:
                level = (3 if missing >= 7 else 2) if track.level >= 2 else 1
                if missing > 12:
                    level = max(1, min(2, track.level))
                output.append({"track_id": track.id, "box": track.box, "label": "missing", "confidence": None,
                               "level": level, "inferred": True,
                               "reasons": [f"Mất dấu {missing:.1f}s trong vùng nước; vị trí cuối, chưa xác nhận chìm"]})
            if missing > 12 and not (self.visibility_valid and unresolved and not edge):
                del self.tracks[track.id]
        return output
