import numpy as np
from scipy.io import savemat

from gazeforge import load_lund2013_mat


def _write_lund_file(path):
    pos = np.zeros((7, 6), dtype=float)
    pos[:, 3] = [100, 110, 120, 0, 140, 150, 160]
    pos[:, 4] = [200, 210, 220, 0, 240, 250, 260]
    pos[:, 5] = [1, 2, 3, 4, 5, 6, 0]
    savemat(
        path,
        {
            "ETdata": {
                "pos": pos,
                "sampFreq": np.array([[500.0]]),
                "screenRes": np.array([[1920.0, 1080.0]]),
                "screenDim": np.array([[530.0, 300.0]]),
                "viewDist": np.array([[650.0]]),
            }
        },
    )


def test_lund2013_loader_maps_schema_labels_and_metadata(tmp_path):
    path = tmp_path / "TH34_img_Europe_labelled_RA.mat"
    _write_lund_file(path)
    gaze = load_lund2013_mat(path)
    assert gaze.sampling_rate_hz == 500
    assert gaze.screen_size_px == (1920, 1080)
    assert gaze.data["participant_id"].iloc[0] == "TH34"
    assert gaze.data["annotator"].iloc[0] == "RA"
    assert gaze.data["stimulus_type"].iloc[0] == "image"
    assert gaze.data["event_label"].tolist() == [
        "fixation",
        "saccade",
        "pso",
        "pursuit",
        "blink",
        "undefined",
        "unlabelled",
    ]
    assert gaze.metadata["source_dataset"] == "Lund2013"
    assert gaze.metadata["visual_angle_geometry_available"] is True
    assert set(
        [
            "screen_width_px",
            "screen_height_px",
            "screen_width_physical",
            "screen_height_physical",
            "view_distance_physical",
        ]
    ).issubset(gaze.data.columns)


def test_lund2013_loader_converts_zero_zero_gaze_to_missing(tmp_path):
    path = tmp_path / "UL39_trial1_labelled_MN.mat"
    _write_lund_file(path)
    gaze = load_lund2013_mat(path)
    assert np.isnan(gaze.data.loc[3, "x_px"])
    assert np.isnan(gaze.data.loc[3, "y_px"])
    assert gaze.data["stimulus_type"].iloc[0] == "moving_dot"


def test_lund2013_loader_can_override_file_metadata(tmp_path):
    path = tmp_path / "unknown.mat"
    _write_lund_file(path)
    gaze = load_lund2013_mat(
        path,
        participant_id="P99",
        trial_id="custom",
        annotator="EXPERT",
        stimulus_type="video",
    )
    assert gaze.data["participant_id"].iloc[0] == "P99"
    assert gaze.data["trial_id"].iloc[0] == "custom"
    assert gaze.data["annotator"].iloc[0] == "EXPERT"
    assert gaze.data["stimulus_type"].iloc[0] == "video"


def test_lund2013_directory_loader_filters_annotator(tmp_path):
    image_dir = tmp_path / "img"
    image_dir.mkdir()
    _write_lund_file(image_dir / "TH34_img_Europe_labelled_RA.mat")
    _write_lund_file(image_dir / "TH34_img_Europe_labelled_MN.mat")
    _write_lund_file(image_dir / "UL31_img_test_labelled_RA.mat")
    from gazeforge import load_lund2013_directory

    gaze = load_lund2013_directory(tmp_path, annotator="RA")
    assert gaze.metadata["n_source_files"] == 2
    assert set(gaze.data["annotator"]) == {"RA"}
    assert set(gaze.data["source_file"]) == {
        "TH34_img_Europe_labelled_RA.mat",
        "UL31_img_test_labelled_RA.mat",
    }
