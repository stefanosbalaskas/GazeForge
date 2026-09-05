from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from gazeforge.exceptions import SchemaError
from gazeforge.gaze_in_wild import load_gaze_in_wild_directory, load_gaze_in_wild_mat


def _write_pair(root: Path, recording="P01_task", labeller=2, n=6, confidence=None):
    label_root = root / "LabelData"
    process_root = root / "ProcessData"
    label_root.mkdir(parents=True, exist_ok=True)
    process_root.mkdir(parents=True, exist_ok=True)
    times = np.arange(n, dtype=float) / 120.0
    labels = np.array([1, 2, 3, 4, 5, 0][:n], dtype=int)
    label = label_root / f"{recording}_Lbr_{labeller}.mat"
    process = process_root / f"{recording}.mat"
    savemat(label, {"LabelData": {"T": times, "Labels": labels, "LbrIdx": labeller}})
    por = np.vstack(
        [
            np.linspace(0.10, 0.60, n, dtype=float),
            np.linspace(0.20, 0.70, n, dtype=float),
        ]
    )
    if confidence is None:
        confidence = np.ones(n, dtype=float)
    savemat(
        process,
        {
            "ProcessData": {
                "ETG": {
                    "POR": por,
                    "Confidence": confidence,
                    "SceneResolution": np.array([1920, 1080], dtype=float),
                }
            }
        },
    )
    return label, process, label_root, process_root


def test_load_infers_rate_maps_labels_and_applies_trackloss(tmp_path):
    confidence = np.array([1.0, 0.2, 0.9, 0.8, 0.7, 0.6])
    label, process, _, _ = _write_pair(tmp_path, confidence=confidence)
    frame = load_gaze_in_wild_mat(label, process_path=process)
    assert frame.sampling_rate_hz == pytest.approx(120.0)
    assert frame.data["event_label"].tolist() == [
        "fixation",
        "pursuit",
        "saccade",
        "blink",
        "vor",
        "unlabelled",
    ]
    assert frame.data.loc[0, "x_px"] == pytest.approx(192.0)
    assert frame.data.loc[0, "y_px"] == pytest.approx(216.0)
    assert np.isnan(frame.data.loc[1, "x_px"])
    assert not bool(frame.data.loc[1, "validity"])
    assert frame.screen_size_px == (1920, 1080)
    assert frame.metadata["coordinate_source_unit"].startswith("normalized Pupil")
    assert frame.metadata["coordinate_output_unit"] == "pixels"
    assert frame.metadata["coordinate_unit_verified"] is True
    assert frame.metadata["official_processed_target_rate_hz"] == 300.0
    assert frame.metadata["participant_identity_resolved"] is False


def test_label_only_loading_is_supported(tmp_path):
    label, _, _, _ = _write_pair(tmp_path)
    frame = load_gaze_in_wild_mat(label, participant_id="P01")
    assert frame.data["x_px"].isna().all()
    assert frame.data["y_px"].isna().all()
    assert not frame.data["validity"].any()
    assert frame.screen_size_px is None
    assert frame.metadata["coordinate_unit_verified"] is False
    assert frame.metadata["participant_identity_resolved"] is True


def test_mismatched_labeller_is_rejected(tmp_path):
    label, _, _, _ = _write_pair(tmp_path, labeller=2)
    savemat(
        label,
        {"LabelData": {"T": np.arange(4) / 120, "Labels": [1, 1, 3, 3], "LbrIdx": 3}},
    )
    with pytest.raises(SchemaError, match="labeller index disagrees"):
        load_gaze_in_wild_mat(label)


def test_process_length_mismatch_is_rejected(tmp_path):
    label, process, _, _ = _write_pair(tmp_path)
    savemat(
        process,
        {
            "ProcessData": {
                "ETG": {
                    "POR": np.ones((2, 5)),
                    "Confidence": np.ones(5),
                    "SceneResolution": [1920, 1080],
                }
            }
        },
    )
    with pytest.raises(SchemaError, match="POR shape"):
        load_gaze_in_wild_mat(label, process_path=process)


def test_process_requires_scene_resolution_for_pixel_conversion(tmp_path):
    label, process, _, _ = _write_pair(tmp_path)
    savemat(
        process,
        {
            "ProcessData": {
                "ETG": {
                    "POR": np.ones((2, 6)) * 0.5,
                    "Confidence": np.ones(6),
                }
            }
        },
    )
    with pytest.raises(SchemaError, match="SceneResolution"):
        load_gaze_in_wild_mat(label, process_path=process)


def test_invalid_scene_resolution_is_rejected(tmp_path):
    label, process, _, _ = _write_pair(tmp_path)
    savemat(
        process,
        {
            "ProcessData": {
                "ETG": {
                    "POR": np.ones((2, 6)) * 0.5,
                    "Confidence": np.ones(6),
                    "SceneResolution": [1920.5, 1080],
                }
            }
        },
    )
    with pytest.raises(SchemaError, match="positive integer pixels"):
        load_gaze_in_wild_mat(label, process_path=process)


def test_non_increasing_timestamps_are_rejected(tmp_path):
    label, _, _, _ = _write_pair(tmp_path)
    savemat(
        label,
        {"LabelData": {"T": [0.0, 0.01, 0.01], "Labels": [1, 1, 3], "LbrIdx": 2}},
    )
    with pytest.raises(SchemaError, match="strictly increasing"):
        load_gaze_in_wild_mat(label)


def test_directory_loader_requires_explicit_identity_parser(tmp_path):
    _, _, label_root, process_root = _write_pair(tmp_path, recording="P01_task")
    frame = load_gaze_in_wild_directory(label_root, process_root=process_root)
    assert set(frame.data["participant_id"]) == {"__unresolved__"}
    assert frame.screen_size_px == (1920, 1080)
    assert frame.metadata["coordinate_unit_verified"] is True
    resolved = load_gaze_in_wild_directory(
        label_root,
        process_root=process_root,
        participant_parser=lambda path: path.stem.split("_", maxsplit=1)[0],
    )
    assert set(resolved.data["participant_id"]) == {"P01"}
    assert resolved.metadata["participant_identity_resolved"] is True


def test_directory_loader_rejects_mixed_labellers_without_selection(tmp_path):
    _, _, label_root, process_root = _write_pair(tmp_path, recording="P01_task", labeller=1)
    _write_pair(tmp_path, recording="P01_task", labeller=2)
    with pytest.raises(SchemaError, match="select one labeller explicitly"):
        load_gaze_in_wild_directory(label_root, process_root=process_root)
    selected = load_gaze_in_wild_directory(
        label_root,
        process_root=process_root,
        labeller=2,
        participant_parser=lambda _: "P01",
    )
    assert set(selected.data["annotator"]) == {"labeller_2"}
