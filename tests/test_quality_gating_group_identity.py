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


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1", "P1", "P1"],
            "trial_id": ["T1", "T1", "T1"],
            "timestamp_ms": [0.0, 100.0, 200.0],
            "acc_x": [0.0, 1.0, 2.0],
            "acc_y": [0.0, 0.0, 0.0],
            "acc_z": [1.0, 1.0, 1.0],
            "pupil": [3.0, 3.1, 3.2],
        }
    )


@pytest.mark.parametrize("missing_column", ["participant_id", "trial_id"])
def test_motion_index_rejects_missing_group_identifiers(missing_column: str) -> None:
    data = _frame()
    data.loc[[0, 1], missing_column] = None

    with pytest.raises(SchemaError, match="Missing grouping identifiers"):
        derive_accelerometer_motion_index(data, smoothing_window_ms=100.0)


def test_combined_gate_and_certificate_inherit_group_identity_guard() -> None:
    data = _frame()
    data.loc[1, "trial_id"] = np.nan
    spec = MotionQualityGateSpec(clean_threshold=2.0, severe_threshold=12.0)

    with pytest.raises(SchemaError, match="Missing grouping identifiers"):
        apply_accelerometer_quality_gate(
            data,
            spec=spec,
            modality="pupil",
            signal_cols=("pupil",),
        )

    with pytest.raises(SchemaError, match="Missing grouping identifiers"):
        build_motion_quality_certificate(
            data,
            spec=spec,
            modality="pupil",
            signal_cols=("pupil",),
        )


def test_summary_rejects_missing_group_or_modality_identity() -> None:
    data = pd.DataFrame(
        {
            "participant_id": ["P1", None],
            "trial_id": ["T1", "T1"],
            "quality_modality": ["pupil", "pupil"],
            "quality_weight": [1.0, 0.5],
            "quality_state": ["clean", "downweighted"],
        }
    )
    with pytest.raises(SchemaError, match="Missing grouping identifiers"):
        summarize_motion_quality(data)

    data["participant_id"] = ["P1", "P1"]
    data.loc[1, "quality_modality"] = None
    with pytest.raises(SchemaError, match="Missing grouping identifiers"):
        summarize_motion_quality(data)


def test_explicit_ungrouped_motion_index_remains_supported() -> None:
    data = _frame().drop(columns=["participant_id", "trial_id"])
    out = derive_accelerometer_motion_index(
        data,
        group_cols=(),
        smoothing_window_ms=100.0,
    )

    assert np.isnan(out.loc[0, "motion_jerk"])
    assert out.loc[1, "motion_jerk"] == pytest.approx(10.0)
    assert out.loc[2, "motion_jerk"] == pytest.approx(10.0)
