from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.full_covariance_location_random_slope_scale import (
    FullCovarianceLocationRandomSlopeScaleSpec,
    build_full_covariance_location_random_slope_scale_certificate,
    fit_full_covariance_location_random_slope_scale,
)
from gazeforge.location_scale_hierarchical_bootstrap import (
    LocationScaleHierarchicalBootstrapSpec,
    _draw_population_effects,
    bootstrap_location_scale_hierarchy,
    build_location_scale_hierarchical_bootstrap_certificate,
    validate_location_scale_hierarchical_bootstrap_certificate,
)
from gazeforge.location_scale_residual_calibration import (
    LocationScaleResidualCalibrationSpec,
    build_location_scale_residual_calibration_certificate,
    calibrate_location_scale_residuals,
    validate_location_scale_residual_calibration_certificate,
)


def _synthetic(seed: int = 911) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tau0 = 0.52
    tau1 = 0.30
    tau_scale = 0.24
    correlation = np.array(
        [
            [1.0, 0.55, 0.45],
            [0.55, 1.0, 0.35],
            [0.45, 0.35, 1.0],
        ]
    )
    covariance = np.diag([tau0, tau1, tau_scale]) @ correlation @ np.diag(
        [tau0, tau1, tau_scale]
    )
    effects = rng.multivariate_normal(np.zeros(3), covariance, size=20)
    x_grid = np.linspace(-1.35, 1.35, 9)
    rows: list[dict[str, float | str]] = []
    for group_index, (b0, b1, c) in enumerate(effects):
        for trial_index, x in enumerate(x_grid):
            log_sigma = -0.55 + 0.08 * x + c
            mean = 1.35 + 0.72 * x + b0 + b1 * x
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "trial_index": float(trial_index),
                    "condition": float(x),
                    "outcome": float(rng.normal(mean, np.exp(log_sigma))),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def full_covariance_fit():
    data = _synthetic()
    spec = FullCovarianceLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=500,
        tolerance=1e-5,
    )
    return data, fit_full_covariance_location_random_slope_scale(data, spec=spec)


def _calibration_spec(seed: int = 1901) -> LocationScaleResidualCalibrationSpec:
    return LocationScaleResidualCalibrationSpec(
        n_simulations=60,
        seed=seed,
        envelope_level=0.90,
        max_simulated_residual_draws=50_000,
    )


def _bootstrap_spec(seed: int = 1905) -> LocationScaleHierarchicalBootstrapSpec:
    return LocationScaleHierarchicalBootstrapSpec(
        n_simulations=2,
        seed=seed,
        interval_level=0.90,
        max_refit_rows=1_000,
    )


@pytest.fixture(scope="module")
def full_covariance_bootstrap(full_covariance_fit):
    data, fitted = full_covariance_fit
    return bootstrap_location_scale_hierarchy(
        fitted,
        data,
        spec=_bootstrap_spec(),
    )


def test_full_covariance_fixed_fit_residual_calibration_is_certifiable_and_deterministic(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    first = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )
    second = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )

    assert first.model_family == "full_covariance_location_random_slope_scale"
    assert first.model_fingerprint_sha256 == fitted.model_fingerprint_sha256
    assert first.n_obs == len(data)
    assert first.n_groups == data["participant_id"].nunique()
    assert first.diagnostic_fingerprint_sha256 == second.diagnostic_fingerprint_sha256
    pd.testing.assert_frame_equal(first.summary, second.summary)

    base_certificate = build_full_covariance_location_random_slope_scale_certificate(fitted)
    assert (
        first.base_model_certificate_fingerprint_sha256
        == base_certificate["certificate_fingerprint_sha256"]
    )
    certificate = build_location_scale_residual_calibration_certificate(first)
    validate_location_scale_residual_calibration_certificate(certificate)


def test_full_covariance_residual_calibration_requires_exact_fitted_input(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    changed = data.copy()
    changed.loc[0, "outcome"] += 0.01
    with pytest.raises(SchemaError, match="exact fitted modelling input"):
        calibrate_location_scale_residuals(
            fitted,
            changed,
            spec=_calibration_spec(seed=1902),
        )


def test_residual_certificate_rejects_resigned_full_covariance_family_tamper(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    result = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(seed=1903),
    )
    certificate = build_location_scale_residual_calibration_certificate(result)
    tampered = copy.deepcopy(certificate)
    tampered["diagnostic"]["model_family"] = "invented_full_covariance_family"
    tampered["diagnostic_fingerprint_sha256"] = benchmark_fingerprint(
        tampered["diagnostic"]
    )
    body = {
        key: value
        for key, value in tampered.items()
        if key != "certificate_fingerprint_sha256"
    }
    tampered["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="model family is invalid"):
        validate_location_scale_residual_calibration_certificate(tampered)


def test_full_covariance_population_draws_use_fitted_three_by_three_covariance(
    full_covariance_fit,
) -> None:
    _, fitted = full_covariance_fit
    group_levels = tuple(f"g{index:02d}" for index in range(12))
    seed = 1910
    observed = _draw_population_effects(
        fitted,
        group_levels,
        np.random.default_rng(seed),
    )

    covariance = fitted.random_effect_covariance_matrix()
    cholesky = np.linalg.cholesky(covariance)
    expected_z = np.random.default_rng(seed).standard_normal((len(group_levels), 3))
    expected = expected_z @ cholesky.T

    assert observed["participant_id"].tolist() == list(group_levels)
    np.testing.assert_allclose(
        observed[
            ["location_intercept", "location_slope", "log_scale_intercept"]
        ].to_numpy(),
        expected,
    )


def test_full_covariance_hierarchical_bootstrap_is_certifiable_with_complete_inventory(
    full_covariance_fit,
    full_covariance_bootstrap,
) -> None:
    data, fitted = full_covariance_fit
    bootstrap = full_covariance_bootstrap

    assert bootstrap.model_family == "full_covariance_location_random_slope_scale"
    assert bootstrap.model_fingerprint_sha256 == fitted.model_fingerprint_sha256
    assert bootstrap.input_fingerprint_sha256 == fitted.input_fingerprint_sha256
    assert bootstrap.n_obs == len(data)
    assert bootstrap.n_groups == data["participant_id"].nunique()
    assert len(bootstrap.refit_ledger) == 2

    parameter_ids = {row["parameter_id"] for row in bootstrap.parameter_inventory}
    assert {
        "random_sd::location_intercept",
        "random_sd::location_slope",
        "random_sd::log_scale_intercept",
        "random_correlation::location_intercept_slope",
        "random_correlation::location_intercept_log_scale",
        "random_correlation::location_slope_log_scale",
    } <= parameter_ids
    assert not any("partial" in parameter_id for parameter_id in parameter_ids)

    for row in bootstrap.refit_ledger:
        assert len(row["population_random_effects_fingerprint_sha256"]) == 64
        assert len(row["simulated_input_fingerprint_sha256"]) == 64
        assert set(row["parameter_estimates"]) == parameter_ids

    certificate = build_location_scale_hierarchical_bootstrap_certificate(bootstrap)
    validate_location_scale_hierarchical_bootstrap_certificate(certificate)
    assert certificate["claim_boundary"]["population_random_effects_resampled"] is True
    assert certificate["claim_boundary"]["empirical_bayes_random_effects_reused"] is False


def test_full_covariance_hierarchical_bootstrap_requires_exact_fitted_input(
    full_covariance_fit,
) -> None:
    data, fitted = full_covariance_fit
    changed = data.copy()
    changed.loc[0, "outcome"] += 0.01
    with pytest.raises(SchemaError, match="exact fitted modelling input"):
        bootstrap_location_scale_hierarchy(
            fitted,
            changed,
            spec=_bootstrap_spec(seed=1911),
        )


def test_hierarchical_bootstrap_certificate_rejects_resigned_full_covariance_family_tamper(
    full_covariance_bootstrap,
) -> None:
    certificate = build_location_scale_hierarchical_bootstrap_certificate(
        full_covariance_bootstrap
    )
    tampered = copy.deepcopy(certificate)
    tampered["bootstrap"]["model_family"] = "invented_full_covariance_bootstrap_family"
    tampered["bootstrap_fingerprint_sha256"] = benchmark_fingerprint(
        tampered["bootstrap"]
    )
    body = {
        key: value
        for key, value in tampered.items()
        if key != "certificate_fingerprint_sha256"
    }
    tampered["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="model family is invalid"):
        validate_location_scale_hierarchical_bootstrap_certificate(tampered)
