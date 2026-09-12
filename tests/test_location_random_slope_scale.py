from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from numpy.polynomial.hermite import hermgauss
from scipy.special import logsumexp

import gazeforge.location_random_slope_scale as random_slope_module
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.location_random_slope_scale import (
    LocationRandomSlopeScaleSpec,
    _adaptive_group_quadrature,
    build_location_random_slope_scale_certificate,
    fit_location_random_slope_scale,
    freeze_location_random_slope_scale_certificate,
    location_random_slope_scale_diagnostics,
    predict_location_random_slope_scale,
    validate_location_random_slope_scale_certificate,
)


def _synthetic(seed: int = 212) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    x_grid = np.linspace(-1.0, 1.0, 10)
    for group_index in range(10):
        b0 = rng.normal(0.0, 0.45)
        b1 = rng.normal(0.0, 0.55)
        c = rng.normal(0.0, 0.40)
        for trial_index, x in enumerate(x_grid):
            sigma = np.exp(np.log(0.65) + 0.12 * x + c)
            mean = 2.2 + 1.1 * x + b0 + b1 * x
            rows.append(
                {
                    "participant_id": f"P{group_index:02d}",
                    "trial_index": float(trial_index),
                    "condition": float(x),
                    "outcome": float(rng.normal(mean, sigma)),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def fitted() -> tuple[pd.DataFrame, object]:
    data = _synthetic()
    spec = LocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=300,
    )
    result = fit_location_random_slope_scale(data, spec=spec)
    return data, result


def test_known_truth_random_slope_fit_recovers_main_direction(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    assert result.converged
    assert result.location_terms == ("Intercept", "condition")
    assert result.scale_terms == ("Intercept", "condition")
    assert result.location_coef[1] > 0.4
    assert abs(result.location_coef[1] - 1.1) < 0.7
    assert result.tau_location_intercept > 0.05
    assert result.tau_location_slope > 0.05
    assert result.tau_scale > 0.05
    assert len(result.group_effects) == 10
    assert np.std(result.group_effects["location_slope_random_mean"]) > 0.05


def test_known_and_unseen_group_prediction_semantics(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    data, result = fitted
    known = data.iloc[[0]].copy()
    known_prediction = predict_location_random_slope_scale(result, known)
    population_prediction = predict_location_random_slope_scale(
        result, known, include_group_effects=False
    )
    assert bool(known_prediction["group_effect_used"].iloc[0])
    assert not np.isclose(
        known_prediction["location_mean"].iloc[0],
        population_prediction["location_mean"].iloc[0],
    )

    unseen = known.copy()
    unseen["participant_id"] = "NEW"
    predicted = predict_location_random_slope_scale(result, unseen)
    assert not bool(predicted["group_effect_used"].iloc[0])
    with pytest.raises(SchemaError, match="unseen groups"):
        predict_location_random_slope_scale(
            result,
            unseen,
            allow_new_groups=False,
        )


def test_one_row_prediction_does_not_repeat_fitting_rank_check(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    data, result = fitted
    row = data.iloc[[3]].copy()
    prediction = predict_location_random_slope_scale(result, row)
    assert len(prediction) == 1
    assert np.isfinite(prediction[["location_mean", "sigma"]].to_numpy()).all()


def test_diagnostics_are_finite_and_standardized(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    data, result = fitted
    diagnostics = location_random_slope_scale_diagnostics(result, data)
    assert list(diagnostics.columns) == [
        "location_mean",
        "log_scale",
        "sigma",
        "group_effect_used",
        "residual",
        "standardized_residual",
    ]
    assert np.isfinite(diagnostics["standardized_residual"]).all()
    assert (diagnostics["sigma"] > 0).all()


def test_spec_and_group_slope_information_fail_closed() -> None:
    with pytest.raises(ValueError, match="must also appear"):
        LocationRandomSlopeScaleSpec(
            outcome_col="outcome",
            group_col="participant_id",
            random_slope_predictor="condition",
            location_predictors=(),
        )
    with pytest.raises(ValueError, match="distinct"):
        LocationRandomSlopeScaleSpec(
            outcome_col="outcome",
            group_col="participant_id",
            random_slope_predictor="outcome",
            location_predictors=("outcome",),
        )
    with pytest.raises(ValueError, match="3 through 9"):
        LocationRandomSlopeScaleSpec(
            outcome_col="outcome",
            group_col="participant_id",
            random_slope_predictor="condition",
            location_predictors=("condition",),
            quadrature_points=11,
        )

    data = _synthetic()
    data.loc[data["participant_id"] == "P00", "condition"] = 0.0
    spec = LocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        quadrature_points=3,
    )
    with pytest.raises(SchemaError, match="numerically rank deficient"):
        fit_location_random_slope_scale(data, spec=spec)


def test_result_mutation_detected_before_prediction_or_certificate(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    data, result = fitted
    original = float(result.location_coef[0])
    result.location_coef[0] = original + 0.5
    try:
        with pytest.raises(SchemaError, match="identity"):
            build_location_random_slope_scale_certificate(result)
        with pytest.raises(SchemaError, match="identity"):
            predict_location_random_slope_scale(result, data.iloc[[0]])
    finally:
        result.location_coef[0] = original


@pytest.mark.parametrize(
    ("theta_index", "boundary"),
    [
        (-3, np.log(random_slope_module._MIN_RANDOM_EFFECT_SD)),
        (-3, np.log(random_slope_module._MAX_LOCATION_RANDOM_EFFECT_SD)),
        (-2, np.log(random_slope_module._MIN_RANDOM_EFFECT_SD)),
        (-2, np.log(random_slope_module._MAX_LOCATION_RANDOM_EFFECT_SD)),
        (-1, np.log(random_slope_module._MIN_RANDOM_EFFECT_SD)),
        (-1, np.log(random_slope_module._MAX_LOG_SCALE_RANDOM_EFFECT_SD)),
    ],
)
def test_fit_rejects_successful_outer_optimizer_at_variance_component_boundary(
    monkeypatch: pytest.MonkeyPatch,
    theta_index: int,
    boundary: float,
) -> None:
    data = (
        _synthetic()
        .groupby("participant_id", sort=False)
        .head(4)
        .reset_index(drop=True)
    )
    spec = LocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        scale_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=10,
    )

    original_minimize = random_slope_module.minimize

    def fake_minimize(fun, x0, *, method, **kwargs):
        if method != "L-BFGS-B":
            return original_minimize(fun, x0, method=method, **kwargs)
        forced = np.asarray(x0, dtype=float).copy()
        forced[theta_index] = boundary
        return SimpleNamespace(
            x=forced,
            success=True,
            status=0,
            message="CONVERGENCE: forced variance boundary regression",
            nit=1,
            fun=0.0,
        )

    monkeypatch.setattr(random_slope_module, "minimize", fake_minimize)
    with pytest.raises(RuntimeError, match="variance component is boundary-censored"):
        fit_location_random_slope_scale(data, spec=spec)


def test_resigned_variance_boundary_certificate_fails_closed(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_location_random_slope_scale_certificate(result)
    forged = copy.deepcopy(certificate)
    forged["model"]["tau_log_scale"] = random_slope_module._MAX_LOG_SCALE_RANDOM_EFFECT_SD
    forged["model_fingerprint_sha256"] = benchmark_fingerprint(forged["model"])
    body = {
        key: value
        for key, value in forged.items()
        if key != "certificate_fingerprint_sha256"
    }
    forged["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="artificial numerical boundary"):
        validate_location_random_slope_scale_certificate(forged)


def test_resigned_variance_boundary_result_fails_closed(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_location_random_slope_scale_certificate(result)
    forged_model = copy.deepcopy(certificate["model"])
    forged_model["tau_location_slope"] = random_slope_module._MAX_LOCATION_RANDOM_EFFECT_SD
    forged = replace(
        result,
        tau_location_slope=random_slope_module._MAX_LOCATION_RANDOM_EFFECT_SD,
        model_fingerprint_sha256=benchmark_fingerprint(forged_model),
    )
    with pytest.raises(SchemaError, match="artificial numerical boundary"):
        build_location_random_slope_scale_certificate(forged)


def test_certificate_rejects_resigned_claim_promotion(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_location_random_slope_scale_certificate(result)
    validate_location_random_slope_scale_certificate(certificate)
    attacked = copy.deepcopy(certificate)
    attacked["claim_boundary"]["population_random_effect_correlations_modelled"] = True
    body = {
        key: value
        for key, value in attacked.items()
        if key != "certificate_fingerprint_sha256"
    }
    attacked["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_location_random_slope_scale_certificate(attacked)


def test_certificate_fixed_effect_dict_order_is_irrelevant(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_location_random_slope_scale_certificate(result)
    reordered = copy.deepcopy(certificate)
    model = reordered["model"]
    model["location_fixed_effects"] = dict(
        reversed(list(model["location_fixed_effects"].items()))
    )
    model["scale_fixed_effects"] = dict(
        reversed(list(model["scale_fixed_effects"].items()))
    )
    model["group_effects_fingerprint_sha256"] = str(
        model["group_effects_fingerprint_sha256"]
    )
    reordered["model_fingerprint_sha256"] = benchmark_fingerprint(model)
    body = {
        key: value
        for key, value in reordered.items()
        if key != "certificate_fingerprint_sha256"
    }
    reordered["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    validate_location_random_slope_scale_certificate(reordered)


def test_freeze_roundtrip_and_overwrite_protection(
    fitted: tuple[pd.DataFrame, object],
    tmp_path: Path,
) -> None:
    _, result = fitted
    path = tmp_path / "random-slope.json"
    frozen = freeze_location_random_slope_scale_certificate(result, path)
    payload = json.loads(frozen.read_text(encoding="utf-8"))
    validate_location_random_slope_scale_certificate(payload)
    with pytest.raises(FileExistsError):
        freeze_location_random_slope_scale_certificate(result, path)


def test_adaptive_group_integral_matches_high_order_fixed_ghq() -> None:
    y = np.array([0.8, 1.3, 1.6, 2.2, 2.5, 2.8], dtype=float)
    w = np.linspace(-1.0, 1.0, len(y))
    location_design = np.column_stack([np.ones(len(y)), w])
    scale_design = np.ones((len(y), 1), dtype=float)
    beta = np.array([1.8, 0.7], dtype=float)
    gamma = np.array([np.log(0.75)], dtype=float)
    tau_intercept = 0.45
    tau_slope = 0.35
    tau_scale = 0.20

    adaptive_nodes, adaptive_weights = hermgauss(5)
    adaptive_log_weights = (
        np.log(adaptive_weights)[:, None, None]
        + np.log(adaptive_weights)[None, :, None]
        + np.log(adaptive_weights)[None, None, :]
    ).ravel()
    adaptive, _, _, _ = _adaptive_group_quadrature(
        y,
        location_design,
        scale_design,
        w,
        beta,
        gamma,
        tau_intercept,
        tau_slope,
        tau_scale,
        adaptive_nodes,
        adaptive_log_weights,
    )

    fixed_nodes, fixed_weights = hermgauss(25)
    log_terms: list[float] = []
    for first_index, first in enumerate(fixed_nodes):
        for second_index, second in enumerate(fixed_nodes):
            for third_index, third in enumerate(fixed_nodes):
                b0 = np.sqrt(2.0) * tau_intercept * first
                b1 = np.sqrt(2.0) * tau_slope * second
                c = np.sqrt(2.0) * tau_scale * third
                residual = y - (location_design @ beta + b0 + b1 * w)
                log_scale = scale_design[:, 0] * gamma[0] + c
                log_likelihood = float(
                    np.sum(
                        -0.5 * np.log(2.0 * np.pi)
                        - log_scale
                        - 0.5 * residual**2 * np.exp(-2.0 * log_scale)
                    )
                )
                log_terms.append(
                    np.log(fixed_weights[first_index])
                    + np.log(fixed_weights[second_index])
                    + np.log(fixed_weights[third_index])
                    - 1.5 * np.log(np.pi)
                    + log_likelihood
                )
    fixed = float(logsumexp(np.asarray(log_terms)))
    assert np.isfinite(adaptive)
    assert abs(adaptive - fixed) < 5e-4
