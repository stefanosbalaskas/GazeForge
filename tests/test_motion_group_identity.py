import numpy as np
import pandas as pd
import pytest

from gazeforge.exceptions import SchemaError
from gazeforge.quality_gating import (
    MotionQualityGateSpec,
    apply_accelerometer_quality_gate,
    build_motion_quality_certificate,
    derive_accelerometer_motion_index,
    summarize_motion_quality,
)


def _motion_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1", "P1", "P2", "P2"],
            "trial_id": ["T1", "T1", "T1", "T1"],
            "timestamp_ms": [0.0, 100.0, 0.0, 100.0],
            "acc_x": [0.0, 1.0, 0.0, 1.0],
            "acc_y": [0.0, 0.0, 0.0, 0.0],
            "acc_z": [1.0, 1.0, 1.0, 1.0],
            "pupil": [3.0, 3.1, 3.2, 3.3],
        }
    )


@pytest.mark.parametrize("column", ["participant_id", "trial_id"])
def test_motion_index_rejects_missing_group_identity(column: str) -> None:
    data = _motion_rows()
    data.loc[[0, 1], column] = np.nan

    with pytest.raises(SchemaError, match="Missing grouping identifiers"):
        derive_accelerometer_motion_index(data)


def test_combined_gate_and_certificate_reject_missing_group_identity() -> None:
    data = _motion_rows()
    data.loc[2, "participant_id"] = None
    spec = MotionQualityGateSpec(clean_threshold=1.0, severe_threshold=20.0)

    with pytest.raises(SchemaError, match="participant_id"):
        apply_accelerometer_quality_gate(
            data,
            spec=spec,
            modality="pupil",
            signal_cols=("pupil",),
        )

    with pytest.raises(SchemaError, match="participant_id"):
        build_motion_quality_certificate(
            data,
            spec=spec,
            modality="pupil",
            signal_cols=("pupil",),
        )


def test_summary_rejects_missing_group_identity_instead_of_coalescing_unknowns() -> None:
    data = pd.DataFrame(
        {
            "participant_id": [None, None],
            "trial_id": ["T1", "T1"],
            "quality_modality": ["pupil", "pupil"],
            "quality_weight": [1.0, 0.5],
            "quality_state": ["clean", "downweighted"],
        }
    )

    with pytest.raises(SchemaError, match="participant_id"):
        summarize_motion_quality(data)


def test_summary_rejects_missing_modality_group_identity() -> None:
    data = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "quality_modality": ["pupil", None],
            "quality_weight": [1.0, 0.5],
            "quality_state": ["clean", "downweighted"],
        }
    )

    with pytest.raises(SchemaError, match="quality_modality"):
        summarize_motion_quality(data)


def test_ungrouped_motion_index_remains_supported() -> None:
    data = _motion_rows().drop(columns=["participant_id", "trial_id"]).copy()
    data["timestamp_ms"] = [0.0, 100.0, 200.0, 300.0]
    data["acc_x"] = [0.0, 1.0, 2.0, 3.0]
    out = derive_accelerometer_motion_index(
        data,
        group_cols=(),
        smoothing_window_ms=100.0,
    )

    assert np.isnan(out.loc[0, "motion_jerk"])
    assert out.loc[1, "motion_jerk"] == pytest.approx(10.0)
    assert out.loc[2, "motion_jerk"] == pytest.approx(10.0)
    assert out.loc[3, "motion_jerk"] == pytest.approx(10.0)
