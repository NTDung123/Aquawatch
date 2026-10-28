from aquawatch.risk import RiskEngine


def detection(label="drowning", box=None):
    return {"label": label, "confidence": .8, "box": box or [.4, .3, .5, .5]}


def feed(engine, start, stop, label="drowning", **kwargs):
    result = []
    for n in range(round(start * 5), round(stop * 5)):
        result = engine.update(n / 5, [detection(label)], **kwargs)
    return result


def test_temporal_escalation_and_hysteresis():
    engine = RiskEngine()
    assert feed(engine, 0, .4)[0]["level"] == 0
    assert feed(engine, .4, 1)[0]["level"] == 1
    assert feed(engine, 1, 3)[0]["level"] == 2
    assert feed(engine, 3, 7)[0]["level"] == 3
    assert feed(engine, 7, 7.6, "swimming")[0]["level"] == 3
    assert feed(engine, 7.6, 18, "swimming")[0]["level"] == 0


def test_swimming_is_not_dangerous_and_people_nearby_do_not_clear_danger():
    engine = RiskEngine()
    assert feed(engine, 0, 8, "swimming")[0]["level"] == 0
    feed(engine, 8, 12)
    result = engine.update(12, [detection(), detection("swimming", [.55, .3, .65, .5])])
    assert max(d["level"] for d in result) >= 2


def test_missing_requires_roi_and_known_stable_motion():
    engine = RiskEngine()
    feed(engine, 0, 4)
    assert engine.update(8, [], motion_known=True) == []
    engine = RiskEngine([[.1, .1], [.9, .1], [.9, .9], [.1, .9]])
    feed(engine, 0, 4)
    assert engine.update(8, [], motion_known=False) == []
    missing = engine.update(8, [], motion_known=True)
    assert missing[0]["inferred"] and missing[0]["confidence"] is None
    assert "chưa xác nhận" in missing[0]["reasons"][0]


def test_pan_and_cut_invalidate_roi_and_tracks():
    for flag in ("camera_moving", "scene_cut"):
        engine = RiskEngine([[.1, .1], [.9, .1], [.9, .9], [.1, .9]])
        feed(engine, 0, 4)
        assert engine.update(5, [], **{flag: True}) == []
        assert engine.update(10, []) == []
        assert not engine.visibility_valid


def test_border_exit_not_submersion():
    engine = RiskEngine([[0, 0], [1, 0], [1, 1], [0, 1]])
    for i in range(20):
        engine.update(i / 5, [detection(box=[0, .3, .04, .5])])
    assert engine.update(8, []) == []


def test_frame_rate_independent_duration():
    engine = RiskEngine(sample_fps=1)
    for i in range(7):
        result = engine.update(i, [detection()])
    assert result[0]["level"] == 3


def test_missing_timeout_never_means_safe():
    engine = RiskEngine([[.1, .1], [.9, .1], [.9, .9], [.1, .9]])
    feed(engine, 0, 4)
    assert engine.update(8, [])[0]["level"] >= 2
    assert engine.update(25, [])[0]["inferred"]
    assert engine.update(25, [])[0]["level"] >= 1


def test_reappearance_keeps_identity_and_does_not_clear_immediately():
    engine = RiskEngine([[.1, .1], [.9, .1], [.9, .9], [.1, .9]])
    previous = feed(engine, 0, 4)[0]
    engine.update(7, [])
    returned = engine.update(7.2, [detection("swimming")])[0]
    assert returned["track_id"] == previous["track_id"]
    assert returned["level"] >= 2
    assert not any(d["inferred"] for d in engine.update(7.4, [detection("swimming")]))
