import numpy as np
import pandas as pd
import pytest

import gazeforge.correlated_location_random_slope_scale as correlated_slope_module
from gazeforge.correlated_location_random_slope_scale import (
    CorrelatedLocationRandomSlopeScaleSpec,
)


def _design() -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    x_values = np.array([-1.2, -0.35, 0.45, 1.1], dtype=float)
    for group_index in range(4):
        group_offset = 0.12 * (group_index - 1.5)
        for x in x_values:
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "condition": float(x),
                    "outcome": float(1.1 + 0.65 * x + group_offset),
                }
            )
    return pd.DataFrame(rows)


def test_marginal_likelihood_is_invariant_to_random_slope_zero_point_shift() -> None:
    data = _design()
    shift = 1.75
    shifted = data.copy()
    shifted["condition_shifted"] = shifted["condition"] - shift

    original_spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
    )
    shifted_spec = CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition_shifted",
        location_predictors=("condition_shifted",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
    )

    original_prepared = correlated_slope_module._prepare_model(data, original_spec)
    shifted_prepared = correlated_slope_module._prepare_model(shifted, shifted_spec)
    nodes, log_weight_grid = correlated_slope_module._quadrature(original_spec)

    beta_intercept = 1.25
    beta_slope = 0.72
    gamma = np.array([-0.32, 0.08], dtype=float)
    tau0 = 0.62
    tau1 = 0.31
    tau_scale = 0.24
    rho = 0.28

    original_theta = np.concatenate(
        [
            np.array([beta_intercept, beta_slope], dtype=float),
            gamma,
            np.log([tau0, tau1, tau_scale]),
            [np.arctanh(rho)],
        ]
    )

    covariance01 = rho * tau0 * tau1
    shifted_tau0_sq = tau0**2 + 2.0 * shift * covariance01 + shift**2 * tau1**2
    shifted_tau0 = float(np.sqrt(shifted_tau0_sq))
    shifted_covariance01 = covariance01 + shift * tau1**2
    shifted_rho = float(shifted_covariance01 / (shifted_tau0 * tau1))
    assert abs(shifted_rho) < 1.0

    shifted_theta = np.concatenate(
        [
            np.array(
                [beta_intercept + shift * beta_slope, beta_slope],
                dtype=float,
            ),
            gamma,
            np.log([shifted_tau0, tau1, tau_scale]),
            [np.arctanh(shifted_rho)],
        ]
    )

    original_objective = correlated_slope_module._objective_factory(
        original_prepared,
        nodes,
        log_weight_grid,
    )
    shifted_objective = correlated_slope_module._objective_factory(
        shifted_prepared,
        nodes,
        log_weight_grid,
    )

    original_value = original_objective(original_theta)
    shifted_value = shifted_objective(shifted_theta)

    assert np.isfinite(original_value)
    assert np.isfinite(shifted_value)
    assert shifted_value == pytest.approx(original_value, rel=1e-10, abs=1e-10)
