from scripts.calibrate_detector import score


def test_detection_matching_counts_duplicate_predictions_as_false_positives():
    records = [{"truth": [{"class_id": 0, "box": [.1, .1, .3, .4]}],
                "predictions": [{"class_id": 0, "confidence": .9, "box": [.1, .1, .3, .4]},
                                {"class_id": 0, "confidence": .5, "box": [.1, .1, .3, .4]}]}]
    assert score(records, .4, 0)["tp"] == 1
    assert score(records, .4, 0)["fp"] == 1
    assert score(records, .7, 0)["fp"] == 0


def test_classification_error_does_not_count_as_correct_person_detection():
    records = [{"truth": [{"class_id": 0, "box": [.1, .1, .3, .4]}],
                "predictions": [{"class_id": 1, "confidence": .9, "box": [.1, .1, .3, .4]}]}]
    assert score(records, .4, 0)["fn"] == 1
    assert score(records, .4, 0)["tp"] == 0
    assert score(records, .4, 1)["fp"] == 1
