from pathlib import Path

import numpy as np
import pytest

from gazeforge.exceptions import SchemaError
from gazeforge.hollywood2 import load_hollywood2_arff, load_hollywood2_directory


def _write_arff(path: Path, *, final_labels=("FIX", "NOISE", "SACCADE", "SP")) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        (0, 100, 200, 1.0, "FIX", final_labels[0]),
        (2000, 0, 0, 0.0, "NOISE", final_labels[1]),
        (4000, 130, 210, 0.9, "SACCADE", final_labels[2]),
        (6000, 140, 220, 0.8, "SP", final_labels[3]),
    ]
    text = """@RELATION hollywood2
@ATTRIBUTE time NUMERIC
@ATTRIBUTE x NUMERIC
@ATTRIBUTE y NUMERIC
@ATTRIBUTE confidence NUMERIC
@ATTRIBUTE handlabeller_1 {FIX,SACCADE,SP,NOISE}
@ATTRIBUTE handlabeller_final {FIX,SACCADE,SP,NOISE}
@DATA
"""
    text += "\n".join(",".join(map(str, row)) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8")


def test_load_hollywood2_final_annotations_and_timing(tmp_path):
    path = tmp_path / "clip.arff"
    _write_arff(path)
    gaze = load_hollywood2_arff(path, participant_id="P01", trial_id="clip")
    assert gaze.sampling_rate_hz == pytest.approx(500.0)
    assert gaze.data["timestamp_ms"].tolist() == [0.0, 2.0, 4.0, 6.0]
    assert gaze.data["event_label"].tolist() == ["fixation", "noise", "saccade", "pursuit"]
    assert np.isnan(gaze.data.loc[1, "x_px"])
    assert not bool(gaze.data.loc[1, "validity"])
    assert gaze.metadata["participant_identity_resolved"] is True
    assert gaze.metadata["reference_strength"] == "expert-human-reference"


def test_load_hollywood2_student_annotations_are_explicit(tmp_path):
    path = tmp_path / "clip.arff"
    _write_arff(path, final_labels=("SP", "SP", "SP", "SP"))
    gaze = load_hollywood2_arff(path, annotator="student", participant_id="P01")
    assert gaze.data["event_label"].tolist() == ["fixation", "noise", "saccade", "pursuit"]
    assert gaze.metadata["annotation_column"] == "handlabeller_1"
    assert gaze.metadata["reference_strength"] == "human-reference"


def test_hollywood2_loader_rejects_wrong_sampling_rate(tmp_path):
    path = tmp_path / "clip.arff"
    _write_arff(path)
    with pytest.raises(SchemaError, match="sampling rate"):
        load_hollywood2_arff(path, expected_sampling_rate_hz=60.0)


def test_directory_loader_refuses_to_guess_participants(tmp_path):
    _write_arff(tmp_path / "ground_truth" / "test" / "p01_clip1.arff")
    _write_arff(tmp_path / "ground_truth" / "test" / "p02_clip1.arff")
    gaze = load_hollywood2_directory(tmp_path)
    assert set(gaze.data["participant_id"]) == {"__unresolved__"}
    assert gaze.metadata["participant_identity_resolved"] is False
    assert gaze.data["trial_id"].nunique() == 2


def test_directory_loader_uses_auditable_identity_parser(tmp_path):
    _write_arff(tmp_path / "ground_truth" / "test" / "p01_clip1.arff")
    _write_arff(tmp_path / "ground_truth" / "test" / "p02_clip1.arff")

    def parser(relative: Path) -> tuple[str, str]:
        participant, clip = relative.stem.split("_", maxsplit=1)
        return participant, clip

    gaze = load_hollywood2_directory(tmp_path, identity_parser=parser)
    assert set(gaze.data["participant_id"]) == {"p01", "p02"}
    assert set(gaze.data["trial_id"]) == {"clip1"}
    assert gaze.metadata["participant_identity_resolved"] is True


def test_hollywood2_missing_annotation_column_is_not_guessed(tmp_path):
    path = tmp_path / "clip.arff"
    _write_arff(path)
    with pytest.raises(SchemaError, match="annotation column"):
        load_hollywood2_arff(path, label_col="does_not_exist")


def test_hollywood2_coordinate_unit_is_unverified_by_default(tmp_path):
    path = tmp_path / "clip.arff"
    _write_arff(path)
    gaze = load_hollywood2_arff(path, participant_id="P01")
    assert gaze.metadata["coordinate_source_unit"] == "unverified"
    assert gaze.metadata["coordinate_unit_verified"] is False
    assert gaze.metadata["canonical_coordinate_alias_only"] is True
    assert set(gaze.data["coordinate_unit"]) == {"unverified"}


def test_hollywood2_coordinate_unit_can_be_explicitly_declared_pixels(tmp_path):
    path = tmp_path / "clip.arff"
    _write_arff(path)
    gaze = load_hollywood2_arff(path, participant_id="P01", coordinate_unit="pixels")
    assert gaze.metadata["coordinate_source_unit"] == "pixels"
    assert gaze.metadata["coordinate_unit_verified"] is True
    assert gaze.metadata["canonical_coordinate_alias_only"] is False
    assert bool(gaze.data["coordinate_unit_verified"].all())
