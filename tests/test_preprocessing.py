from types import SimpleNamespace

import numpy as np
import pytest
import torch

from aquawatch.vision import VisionEngine


@pytest.mark.parametrize("policy", ["letterbox", "stretch640"])
def test_inference_boxes_stay_normalized_after_preprocessing(policy):
    class Model:
        def predict(self, image, **options):
            h, w = image.shape[:2]
            box = SimpleNamespace(cls=torch.tensor(0), conf=torch.tensor(.8),
                                  xyxy=torch.tensor([[w * .25, h * .2, w * .5, h * .8]]))
            return [SimpleNamespace(boxes=[box])]

    engine = VisionEngine.__new__(VisionEngine)
    engine.model, engine.names, engine.device = Model(), {0: "drowning"}, "cpu"
    engine.preprocessing, engine.inference_ms, engine.rejected = policy, [], 0
    detections = engine.predict(np.zeros((360, 1280, 3), dtype=np.uint8), .4)
    assert detections[0]["box"] == pytest.approx([.25, .2, .5, .8])
