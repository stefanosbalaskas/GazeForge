from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gazeforge.exceptions import SchemaError
from gazeforge.location_random_slope_scale import (
    LocationRandomSlopeScaleSpec,
    _prepare_model,
)


def _identifiability_frame() -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    ordinary = np.array([-1.0, -0.3, 0.4, 1.0], dtype=float)
    for group_index in range(3):
        if group_index == 0:
            condition = 1.0e12 + np.arange(4, dtype=float)
        else:
            condition = ordinary + 0.1 * group_index
        for trial_index, value in enumerate(condition):
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "trial_index": float(trial_index),
                    "condition": float(value),
                    "outcome": float(1.0 + 0.25 * trial_index + group_index),
                }
            )
    return pd.DataFrame(rows)


def test_distinct_but_rank_deficient_participant_slope_design_fails_closed() -> None:
    """Exact distinctness must not substitute for numerical slope identifiability."""
    data = _identifiability_frame()
    mask = data["participant_id"] == "P00"
    n_rows = int(mask.sum())

    # The values are distinct, so an exact-uniqueness check alone would pass,
    # but the actual participant random-effect design [Intercept, w] is
    # numerically rank deficient at this scale. Other participants keep the
    # global fixed-effect design full rank, isolating the participant-level gap.
    participant_w = data.loc[mask, "condition"].to_numpy(dtype=float)
    participant_design = np.column_stack(
        [np.ones(n_rows, dtype=float), participant_w]
    )
    assert np.unique(participant_w).size == n_rows
    assert np.linalg.matrix_rank(participant_design) == 1

    global_design = np.column_stack(
        [np.ones(len(data), dtype=float), data["condition"].to_numpy(dtype=float)]
    )
    assert np.linalg.matrix_rank(global_design) == 2

    spec = LocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=(),
        quadrature_points=3,
        min_group_size=4,
    )

    with pytest.raises(SchemaError, match="numerically rank deficient"):
        _prepare_model(data, spec)
