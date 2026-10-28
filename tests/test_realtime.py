import copy
import hashlib
from types import SimpleNamespace
import numpy as np
import pytest
from aquawatch import jobs, store


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, value):
        self.value += value


def test_pacing_waits_for_source_time_and_can_cancel(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(jobs, "CANCELLED", set())
    assert jobs.pace_sample("job", 2, 0, clock, clock.sleep)
    assert clock.value == pytest.approx(2)
    jobs.CANCELLED.add("job")
    assert not jobs.pace_sample("job", 3, 0, clock, clock.sleep)


@pytest.mark.parametrize("mode,decoded_frames", [("realtime", 15), ("batch", 15), ("batch", 0), ("batch", 7)])
def test_incremental_pipeline_has_no_future_and_persists_final_state(tmp_path, monkeypatch, mode, decoded_frames):
    clock = Clock()
    model_path = tmp_path / "fake-model-for-pipeline-test.pt"
    model_path.write_bytes(b"unit test only; never a real inference checkpoint")
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(jobs, "RESULTS", results)
    monkeypatch.setattr(store, "DB", tmp_path / "test.sqlite3")
    monkeypatch.setattr(jobs, "CANCELLED", set())
    monkeypatch.setattr(jobs, "selected_model", lambda: model_path)

    class Detector:
        path = model_path
        sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()
        inference_ms = []
        rejected = 0
        device = "unit-test"

        def predict(self, frame, confidence):
            clock.sleep(.03)
            self.inference_ms.append(30)
            return [{"box": [.3, .3, .5, .6], "label": "drowning", "confidence": .8}]

    class Capture:
        index = -1

        def isOpened(self):
            return True

        def grab(self):
            self.index += 1
            return self.index < decoded_frames

        def retrieve(self):
            return True, np.zeros((30, 40, 3), dtype=np.uint8)

        def release(self):
            pass

    monkeypatch.setattr(jobs, "ENGINE", Detector())
    monkeypatch.setattr(jobs.cv2, "VideoCapture", lambda path: Capture())
    movement = {"camera_moving": False, "scene_cut": False, "motion_known": True, "displacement_px": 0}
    monkeypatch.setattr(jobs, "CameraMotion", lambda polygon: SimpleNamespace(update=lambda *args: movement))
    snapshots = []
    real_writer = jobs.write_analysis

    def recording_writer(folder, content):
        snapshots.append(copy.deepcopy(content))
        real_writer(folder, content)

    monkeypatch.setattr(jobs, "write_analysis", recording_writer)
    job = {"id": "a" * 32, "status": "queued", "progress": 0,
           "config": {"mode": mode, "water_polygon": [], "sample_fps": 5, "confidence": .4},
           "video": {"path": "unit-test-transport-only", "duration": 3, "fps": 5, "frames": 15}}
    jobs.run(job, clock, clock.sleep)
    if decoded_frames < 15:
        assert job["status"] == "failed"
        assert snapshots[-1]["partial"] is True
        assert len(snapshots[-1]["samples"]) == decoded_frames
        assert job["processed_until"] == snapshots[-1]["processed_until"]
        assert store.get("jobs", job["id"])["progress"] < 1
        return
    assert job["status"] == "completed"
    assert store.get("jobs", job["id"])["status"] == "completed"
    assert snapshots[0]["samples"] == []
    assert len(snapshots) >= 3
    assert snapshots[-1]["partial"] is False
    assert len(snapshots[-1]["samples"]) == 15
    assert snapshots[-1]["processed_until"] == pytest.approx(2.8)
    for snapshot in snapshots:
        assert all(e["start"] <= snapshot["processed_until"] for e in snapshot["events"])
        if mode == "realtime" and snapshot["processed_until"] is not None:
            assert snapshot["processed_until"] <= snapshot["source_elapsed_seconds"] + .001
    assert (clock.value >= 2.8) if mode == "realtime" else (clock.value < 1)
