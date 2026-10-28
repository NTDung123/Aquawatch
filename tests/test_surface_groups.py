from scripts.prepare_surface_dataset import base_name, group_for


def test_old_evaluation_scenes_cannot_enter_train():
    for source in ("mibugi", "alanoud"):
        assert group_for(source, "train/images/video_2022-12-07_23-08-12_mp4-5_jpg.rf.x.jpg")[:2] == ("high_pool", "val")
        assert group_for(source, "train/images/Untitled-video-Made-with-Clipchamp-1-_mp4-5_jpg.rf.x.jpg")[:2] == ("indoor_pool", "test")


def test_competition_camera_boundary_names_998_and_999_are_test():
    for number in (998, 999, 1000, 1100):
        assert group_for("mibugi", f"train/images/{number}_jpg.rf.x.jpg")[:2] == ("competition_pool_cctv", "test")


def test_all_five_indoor_clips_share_one_group():
    groups = {group_for("mibugi", f"train/images/IMG_{number}_MOV-0001_jpg.rf.x.jpg")[:2] for number in range(3607, 3612)}
    assert groups == {("indoor_training_pool", "train")}


def test_stock_and_movie_names_are_never_candidates():
    for name in ("iStock_drowning.jpg", "Jennifer-Lawrence-drowning-Passengers-Movie_mp4-1_jpg.rf.x.jpg"):
        assert group_for("mibugi", name)[0] is None
    assert base_name("186_png_jpg.rf.x.jpg") == "186"
