from scripts.evaluate_events import evaluate


def test_one_to_one_matching_and_signed_latency():
    predictions = [{"id": "a", "track_id": 1, "start": 12, "end": 19, "level": 2},
                   {"id": "b", "track_id": 1, "start": 13, "end": 18, "level": 2}]
    truth = [{"id": "gt", "start": 10, "end": 20, "accepted_track_ids": [1]}]
    result = evaluate(predictions, truth, 3600)
    assert (result["tp"], result["fp"], result["fn"]) == (1, 1, 0)
    assert result["precision"] == .5 and result["recall"] == 1
    assert result["mean_latency_seconds_signed"] == 2
    assert result["false_alarms_per_hour"] == 1


def test_wrong_person_is_a_miss():
    result = evaluate([{"id": "p", "track_id": 2, "start": 10, "end": 20, "level": 2}],
                      [{"id": "g", "start": 10, "end": 20, "accepted_track_ids": [1]}], 60)
    assert (result["tp"], result["fp"], result["fn"]) == (0, 1, 1)
