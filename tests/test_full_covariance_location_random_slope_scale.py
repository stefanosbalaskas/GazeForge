from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.full_covariance_location_random_slope_scale as full_covariance_module
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.full_covariance_location_random_slope_scale import (
    FullCovarianceLocationRandomSlopeScaleSpec,
    _correlation_matrix_from_coordinates,
    _covariance_parameters_from_matrix,
    _group_log_integrand,
    _population_covariance,
    build_full_covariance_location_random_slope_scale_certificate,
    fit_full_covariance_location_random_slope_scale,
    freeze_full_covariance_location_random_slope_scale_certificate,
    full_covariance_location_random_slope_scale_diagnostics,
    predict_full_covariance_location_random_slope_scale,
    transform_full_covariance_for_predictor_shift,
    validate_full_covariance_location_random_slope_scale_certificate,
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
def fitted() -> tuple[pd.DataFrame, object]:
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


def _resign(certificate: dict) -> None:
    certificate["model_fingerprint_sha256"] = benchmark_fingerprint(certificate["model"])
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_vine_parameterization_is_positive_definite_and_exact() -> None:
    r01 = 0.55
    r02 = -0.30
    partial = 0.40
    correlation, r12 = _correlation_matrix_from_coordinates(r01, r02, partial)
    assert correlation == pytest.approx(correlation.T, abs=1e-12)
    assert np.diag(correlation) == pytest.approx(np.ones(3), abs=1e-12)
    assert np.min(np.linalg.eigvalsh(correlation)) > 0.0
    expected_r12 = r01 * r02 + np.sqrt(1.0 - r01**2) * np.sqrt(
        1.0 - r02**2
    ) * partial
    assert r12 == pytest.approx(expected_r12, abs=1e-12)
    assert correlation[1, 2] == pytest.approx(expected_r12, abs=1e-12)


def test_covariance_parameter_roundtrip_is_exact() -> None:
    covariance, _, _, r12 = _population_covariance(
        0.65,
        0.31,
        0.22,
        0.45,
        -0.28,
        0.36,
    )
    tau0, tau1, tau2, r01, r02, recovered_r12, partial = (
        _covariance_parameters_from_matrix(covariance)
    )
    reconstructed, _, _, second_r12 = _population_covariance(
        tau0,
        tau1,
        tau2,
        r01,
        r02,
        partial,
    )
    assert reconstructed == pytest.approx(covariance, abs=1e-12)
    assert recovered_r12 == pytest.approx(r12, abs=1e-12)
    assert second_r12 == pytest.approx(r12, abs=1e-12)


def test_full_covariance_is_closed_under_predictor_zero_point_shift() -> None:
    covariance, _, _, _ = _population_covariance(
        0.60,
        0.27,
        0.20,
        0.42,
        0.25,
        -0.30,
    )
    shift = 2.4
    shifted = transform_full_covariance_for_predictor_shift(covariance, shift=shift)
    transform = np.array([[1.0, shift, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    assert shifted == pytest.approx(transform @ covariance @ transform.T, abs=1e-12)
    assert np.min(np.linalg.eigvalsh(shifted)) > 0.0
    params = _covariance_parameters_from_matrix(shifted)
    assert all(np.isfinite(params))


def test_group_integrand_is_exactly_zero_point_invariant() -> None:
    x = np.linspace(-1.0, 1.0, 7)
    location_design = np.column_stack([np.ones(len(x)), x])
    scale_design = np.column_stack([np.ones(len(x)), x])
    beta = np.array([1.1, 0.65])
    gamma = np.array([-0.35, 0.09])
    effects = np.array([0.22, -0.12, 0.16])
    y = location_design @ beta + effects[0] + effects[1] * x + np.linspace(-0.2, 0.2, 7)
    covariance, precision, logdet, _ = _population_covariance(
        0.55,
        0.25,
        0.18,
        0.35,
        0.28,
        -0.22,
    )
    original, _, _ = _group_log_integrand(
        effects,
        y,
        location_design,
        scale_design,
        x,
        beta,
        gamma,
        precision,
        logdet,
    )

    shift = 1.75
    shifted_x = x - shift
    shifted_location_design = np.column_stack([np.ones(len(x)), shifted_x])
    shifted_scale_design = np.column_stack([np.ones(len(x)), shifted_x])
    shifted_beta = np.array([beta[0] + beta[1] * shift, beta[1]])
    shifted_gamma = np.array([gamma[0] + gamma[1] * shift, gamma[1]])
    transform = np.array([[1.0, shift, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    shifted_effects = transform @ effects
    shifted_covariance = transform_full_covariance_for_predictor_shift(
        covariance, shift=shift
    )
    sign, shifted_logdet = np.linalg.slogdet(shifted_covariance)
    assert sign > 0
    shifted_precision = np.linalg.inv(shifted_covariance)
    shifted, _, _ = _group_log_integrand(
        shifted_effects,
        y,
        shifted_location_design,
        shifted_scale_design,
        shifted_x,
        shifted_beta,
        shifted_gamma,
        shifted_precision,
        float(shifted_logdet),
    )
    assert shifted == pytest.approx(original, abs=1e-10)


def test_known_truth_fit_returns_certifiable_full_covariance(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    assert result.converged
    assert result.location_terms == ("Intercept", "condition")
    assert result.scale_terms == ("Intercept", "condition")
    assert result.location_coef[1] > 0.20
    assert result.tau_location_intercept > full_covariance_module._MIN_RANDOM_EFFECT_SD
    assert result.tau_location_slope > full_covariance_module._MIN_RANDOM_EFFECT_SD
    assert result.tau_scale > full_covariance_module._MIN_RANDOM_EFFECT_SD
    correlation = result.random_effect_correlation_matrix()
    covariance = result.random_effect_covariance_matrix()
    assert correlation.shape == (3, 3)
    assert covariance.shape == (3, 3)
    assert np.min(np.linalg.eigvalsh(correlation)) > 0.0
    assert np.min(np.linalg.eigvalsh(covariance)) > 0.0
    assert correlation[0, 1] == pytest.approx(result.rho_location_intercept_slope)
    assert correlation[0, 2] == pytest.approx(result.rho_location_intercept_log_scale)
    assert correlation[1, 2] == pytest.approx(result.rho_location_slope_log_scale)
    assert len(result.group_effects) == 20


def test_prediction_and_diagnostics_preserve_known_and_unseen_semantics(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    data, result = fitted
    known = data.iloc[[0]].copy()
    conditional = predict_full_covariance_location_random_slope_scale(result, known)
    population = predict_full_covariance_location_random_slope_scale(
        result, known, include_group_effects=False
    )
    assert bool(conditional["group_effect_used"].iloc[0])
    assert not np.isclose(
        conditional["location_mean"].iloc[0], population["location_mean"].iloc[0]
    )

    unseen = known.copy()
    unseen["participant_id"] = "NEW"
    predicted = predict_full_covariance_location_random_slope_scale(result, unseen)
    assert not bool(predicted["group_effect_used"].iloc[0])
    with pytest.raises(SchemaError, match="unseen groups"):
        predict_full_covariance_location_random_slope_scale(
            result, unseen, allow_new_groups=False
        )

    diagnostics = full_covariance_location_random_slope_scale_diagnostics(result, data)
    assert np.isfinite(diagnostics["standardized_residual"]).all()
    assert (diagnostics["sigma"] > 0).all()


def test_spec_reuses_random_slope_identifiability_contract() -> None:
    with pytest.raises(ValueError, match="must also appear"):
        FullCovarianceLocationRandomSlopeScaleSpec(
            outcome_col="outcome",
            group_col="participant_id",
            random_slope_predictor="condition",
            location_predictors=(),
        )

    data = _synthetic()
    data.loc[data["participant_id"] == "P00", "condition"] = 0.0
    spec = FullCovarianceLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        quadrature_points=3,
    )
    with pytest.raises(SchemaError, match="numerically rank deficient"):
        fit_full_covariance_location_random_slope_scale(data, spec=spec)


@pytest.mark.parametrize("eta_index", [-3, -2, -1])
@pytest.mark.parametrize("eta_value", [-4.0, 4.0])
def test_fit_rejects_successful_outer_optimizer_at_any_correlation_bound(
    monkeypatch: pytest.MonkeyPatch,
    eta_index: int,
    eta_value: float,
) -> None:
    data = _synthetic().groupby("participant_id", sort=False).head(4).reset_index(drop=True)
    spec = FullCovarianceLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=10,
    )

    def fake_minimize(fun, x0, *, method, **kwargs):
        assert method == "L-BFGS-B"
        forced = np.asarray(x0, dtype=float).copy()
        forced[eta_index] = eta_value
        return SimpleNamespace(
            x=forced,
            success=True,
            status=0,
            message="CONVERGENCE: forced correlation boundary regression",
            nit=1,
            fun=0.0,
        )

    monkeypatch.setattr(full_covariance_module, "minimize", fake_minimize)
    with pytest.raises(RuntimeError, match="optimizer bound"):
        fit_full_covariance_location_random_slope_scale(data, spec=spec)


@pytest.mark.parametrize(
    ("theta_index", "boundary"),
    [
        (-6, np.log(full_covariance_module._MIN_RANDOM_EFFECT_SD)),
        (-5, np.log(full_covariance_module._MIN_RANDOM_EFFECT_SD)),
        (-4, np.log(full_covariance_module._MIN_RANDOM_EFFECT_SD)),
    ],
)
def test_fit_rejects_successful_outer_optimizer_at_variance_boundary(
    monkeypatch: pytest.MonkeyPatch,
    theta_index: int,
    boundary: float,
) -> None:
    data = _synthetic().groupby("participant_id", sort=False).head(4).reset_index(drop=True)
    spec = FullCovarianceLocationRandomSlopeScaleSpec(
        outcome_col="outcome",
        group_col="participant_id",
        random_slope_predictor="condition",
        location_predictors=("condition",),
        quadrature_points=3,
        min_group_size=4,
        max_iter=10,
    )

    def fake_minimize(fun, x0, *, method, **kwargs):
        assert method == "L-BFGS-B"
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

    monkeypatch.setattr(full_covariance_module, "minimize", fake_minimize)
    with pytest.raises(RuntimeError, match="standard deviation"):
        fit_full_covariance_location_random_slope_scale(data, spec=spec)


def test_certificate_roundtrip_and_canonical_schema(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_full_covariance_location_random_slope_scale_certificate(result)
    validate_full_covariance_location_random_slope_scale_certificate(certificate)
    model = certificate["model"]
    assert model["rho_location_intercept_slope"] == pytest.approx(
        result.rho_location_intercept_slope
    )
    assert model["rho_location_intercept_log_scale"] == pytest.approx(
        result.rho_location_intercept_log_scale
    )
    assert model["rho_location_slope_log_scale"] == pytest.approx(
        result.rho_location_slope_log_scale
    )

    unknown = copy.deepcopy(certificate)
    unknown["model"]["device_specific_validity"] = True
    _resign(unknown)
    with pytest.raises(SchemaError, match="noncanonical schema"):
        validate_full_covariance_location_random_slope_scale_certificate(unknown)

    noncanonical = copy.deepcopy(certificate)
    noncanonical["model"]["rho_location_intercept_log_scale"] = "0.5"
    _resign(noncanonical)
    with pytest.raises(SchemaError, match="JSON numbers"):
        validate_full_covariance_location_random_slope_scale_certificate(noncanonical)


def test_certificate_rejects_resigned_inconsistent_vine_coordinates(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_full_covariance_location_random_slope_scale_certificate(result)
    forged = copy.deepcopy(certificate)
    forged["model"]["rho_location_slope_log_scale"] += 0.1
    _resign(forged)
    with pytest.raises(SchemaError, match="inconsistent"):
        validate_full_covariance_location_random_slope_scale_certificate(forged)


def test_certificate_rejects_resigned_boundary_and_claim_promotion(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    _, result = fitted
    certificate = build_full_covariance_location_random_slope_scale_certificate(result)

    boundary = copy.deepcopy(certificate)
    boundary["model"]["rho_location_intercept_slope"] = float(np.tanh(4.0))
    _resign(boundary)
    with pytest.raises(SchemaError, match="artificial optimizer boundary"):
        validate_full_covariance_location_random_slope_scale_certificate(boundary)

    promoted = copy.deepcopy(certificate)
    promoted["claim_boundary"]["scale_random_slopes_modelled"] = True
    body = {
        key: value
        for key, value in promoted.items()
        if key != "certificate_fingerprint_sha256"
    }
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_full_covariance_location_random_slope_scale_certificate(promoted)


def test_result_mutation_and_resigned_result_fail_closed(
    fitted: tuple[pd.DataFrame, object],
) -> None:
    data, result = fitted
    original = float(result.location_coef[0])
    result.location_coef[0] = original + 0.2
    try:
        with pytest.raises(SchemaError, match="identity"):
            predict_full_covariance_location_random_slope_scale(result, data.iloc[[0]])
    finally:
        result.location_coef[0] = original

    certificate = build_full_covariance_location_random_slope_scale_certificate(result)
    forged_model = copy.deepcopy(certificate["model"])
    forged_model["rho_location_intercept_slope"] = float(np.tanh(4.0))
    forged = replace(
        result,
        rho_location_intercept_slope=float(np.tanh(4.0)),
        model_fingerprint_sha256=benchmark_fingerprint(forged_model),
    )
    with pytest.raises(SchemaError, match="artificial optimizer boundary"):
        build_full_covariance_location_random_slope_scale_certificate(forged)


def test_freeze_roundtrip_and_overwrite_protection(
    fitted: tuple[pd.DataFrame, object],
    tmp_path: Path,
) -> None:
    _, result = fitted
    path = tmp_path / "full-covariance-random-slope.json"
    frozen = freeze_full_covariance_location_random_slope_scale_certificate(result, path)
    payload = json.loads(frozen.read_text(encoding="utf-8"))
    validate_full_covariance_location_random_slope_scale_certificate(payload)
    with pytest.raises(FileExistsError):
        freeze_full_covariance_location_random_slope_scale_certificate(result, path)
