import json
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from numpy.polynomial.hermite import hermgauss
from scipy.special import logsumexp

import gazeforge.correlated_location_scale as correlated_module
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.correlated_location_scale import (
    CorrelatedLocationScaleSpec,
    _adaptive_group_quadrature,
    _group_log_integrand,
    _quadrature,
    build_correlated_location_scale_certificate,
    correlated_location_scale_diagnostics,
    fit_correlated_location_scale,
    freeze_correlated_location_scale_certificate,
    predict_correlated_location_scale,
    validate_correlated_location_scale_certificate,
)
from gazeforge.exceptions import SchemaError


def _synthetic_correlated(seed=123, groups=32, n_per_group=12, rho=0.55):
    rng = np.random.default_rng(seed)
    tau_location = 0.60
    tau_scale = 0.28
    covariance = np.array(
        [
            [tau_location**2, rho * tau_location * tau_scale],
            [rho * tau_location * tau_scale, tau_scale**2],
        ]
    )
    effects = rng.multivariate_normal(np.zeros(2), covariance, size=groups)
    rows = []
    for group in range(groups):
        x = rng.normal(size=n_per_group)
        mu = 0.4 + 0.65 * x + effects[group, 0]
        log_sigma = -0.25 + 0.12 * x + effects[group, 1]
        y = rng.normal(mu, np.exp(log_sigma))
        rows.extend((f"p{group}", xx, yy) for xx, yy in zip(x, y, strict=True))
    return pd.DataFrame(rows, columns=["participant_id", "x", "y"])


@pytest.fixture(scope="module")
def fitted_model():
    data = _synthetic_correlated()
    spec = CorrelatedLocationScaleSpec(
        "y",
        "participant_id",
        ("x",),
        ("x",),
        quadrature_points=3,
        max_iter=220,
        tolerance=1e-7,
    )
    return data, fit_correlated_location_scale(data, spec=spec)


def test_known_truth_recovers_positive_location_scale_association(fitted_model):
    _, fitted = fitted_model
    assert fitted.converged
    assert fitted.rho_location_scale > 0.10
    assert fitted.rho_location_scale == pytest.approx(0.55, abs=0.35)
    assert fitted.location_coef[1] == pytest.approx(0.65, abs=0.22)
    assert fitted.scale_coef[1] == pytest.approx(0.12, abs=0.18)
    assert fitted.tau_location > 0.10
    assert fitted.tau_scale > 0.03
    assert fitted.random_effect_correlation() == fitted.rho_location_scale


def test_predictions_and_diagnostics_handle_known_and_unseen_groups(fitted_model):
    data, fitted = fitted_model
    known = predict_correlated_location_scale(fitted, data.iloc[:3])
    assert known["group_effect_used"].all()
    unseen = pd.DataFrame({"participant_id": ["new"], "x": [0.2]})
    population = predict_correlated_location_scale(fitted, unseen)
    assert not population["group_effect_used"].iloc[0]
    with pytest.raises(SchemaError, match="unseen groups"):
        predict_correlated_location_scale(fitted, unseen, allow_new_groups=False)
    diagnostics = correlated_location_scale_diagnostics(fitted, data)
    assert np.isfinite(diagnostics["standardized_residual"]).all()
    assert (diagnostics["sigma"] > 0).all()


def test_zero_correlation_integrand_matches_independent_prior_formula():
    rng = np.random.default_rng(9)
    y = rng.normal(size=7)
    x = rng.normal(size=7)
    design = np.column_stack([np.ones(7), x])
    beta = np.array([0.2, 0.4])
    gamma = np.array([-0.1, 0.15])
    effects = np.array([0.25, -0.08])
    tau_location = 0.55
    tau_scale = 0.22
    value, gradient, negative_hessian = _group_log_integrand(
        effects,
        y,
        design,
        design,
        beta,
        gamma,
        tau_location,
        tau_scale,
        0.0,
    )
    residual = y - (design @ beta + effects[0])
    log_scale = design @ gamma + effects[1]
    inverse_variance = np.exp(-2.0 * log_scale)
    expected = float(
        np.sum(
            -0.5 * np.log(2.0 * np.pi)
            - log_scale
            - 0.5 * residual**2 * inverse_variance
        )
        - np.log(2.0 * np.pi)
        - np.log(tau_location)
        - np.log(tau_scale)
        - 0.5 * (effects[0] / tau_location) ** 2
        - 0.5 * (effects[1] / tau_scale) ** 2
    )
    assert value == pytest.approx(expected)
    assert gradient[0] == pytest.approx(
        np.sum(residual * inverse_variance) - effects[0] / tau_location**2
    )
    assert gradient[1] == pytest.approx(
        np.sum(-1.0 + residual**2 * inverse_variance) - effects[1] / tau_scale**2
    )
    assert negative_hessian[0, 0] == pytest.approx(
        np.sum(inverse_variance) + 1.0 / tau_location**2
    )
    assert negative_hessian[1, 1] == pytest.approx(
        2.0 * np.sum(residual**2 * inverse_variance) + 1.0 / tau_scale**2
    )


def test_correlated_adaptive_likelihood_matches_fixed_quadrature_reference():
    rng = np.random.default_rng(17)
    x = rng.normal(size=6)
    y = rng.normal(0.3 + 0.4 * x, 0.8)
    design = np.column_stack([np.ones(6), x])
    beta = np.array([0.25, 0.35])
    gamma = np.array([-0.2, 0.1])
    tau_location = 0.5
    tau_scale = 0.2
    rho = 0.45
    spec = CorrelatedLocationScaleSpec("y", "g", ("x",), ("x",), quadrature_points=7)
    nodes, log_weights = _quadrature(spec)
    adaptive, _, _, _ = _adaptive_group_quadrature(
        y,
        design,
        design,
        beta,
        gamma,
        tau_location,
        tau_scale,
        rho,
        nodes,
        log_weights,
    )
    ref_nodes, ref_weights = hermgauss(31)
    covariance = np.array(
        [
            [tau_location**2, rho * tau_location * tau_scale],
            [rho * tau_location * tau_scale, tau_scale**2],
        ]
    )
    chol = np.linalg.cholesky(covariance)
    log_values = []
    log_node_weights = []
    for i, first in enumerate(ref_nodes):
        for j, second in enumerate(ref_nodes):
            random_effects = np.sqrt(2.0) * chol @ np.array([first, second])
            residual = y - (design @ beta + random_effects[0])
            log_scale = design @ gamma + random_effects[1]
            log_values.append(
                np.sum(
                    -0.5 * np.log(2.0 * np.pi)
                    - log_scale
                    - 0.5 * residual**2 * np.exp(-2.0 * log_scale)
                )
            )
            log_node_weights.append(np.log(ref_weights[i]) + np.log(ref_weights[j]))
    reference = float(
        logsumexp(np.asarray(log_values) + np.asarray(log_node_weights)) - np.log(np.pi)
    )
    assert adaptive == pytest.approx(reference, abs=3e-4)


@pytest.mark.parametrize("correlation_eta", [-4.0, 4.0])
def test_fit_rejects_successful_outer_optimizer_at_correlation_bound(
    monkeypatch, correlation_eta
):
    data = _synthetic_correlated(groups=3, n_per_group=4)
    spec = CorrelatedLocationScaleSpec(
        "y", "participant_id", quadrature_points=3, max_iter=10
    )

    def fake_minimize(fun, x0, *, method, **kwargs):
        assert method == "L-BFGS-B"
        forced = np.asarray(x0, dtype=float).copy()
        forced[-1] = correlation_eta
        return SimpleNamespace(
            x=forced,
            success=True,
            status=0,
            message="CONVERGENCE: forced boundary regression",
            nit=1,
            fun=0.0,
        )

    monkeypatch.setattr(correlated_module, "minimize", fake_minimize)
    with pytest.raises(RuntimeError, match="boundary-censored"):
        fit_correlated_location_scale(data, spec=spec)


def test_certificate_binds_correlation_and_rejects_resigned_tamper(fitted_model):
    _, fitted = fitted_model
    certificate = build_correlated_location_scale_certificate(fitted)
    validate_correlated_location_scale_certificate(certificate)
    tampered = deepcopy(certificate)
    tampered["model"]["rho_location_log_scale"] = -0.8
    body = {k: v for k, v in tampered.items() if k != "certificate_fingerprint_sha256"}
    tampered["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="model fingerprint"):
        validate_correlated_location_scale_certificate(tampered)


def test_resigned_boundary_correlation_certificate_fails_closed(fitted_model):
    _, fitted = fitted_model
    certificate = build_correlated_location_scale_certificate(fitted)
    forged = deepcopy(certificate)
    forged["model"]["rho_location_log_scale"] = float(np.tanh(4.0))
    forged["model_fingerprint_sha256"] = benchmark_fingerprint(forged["model"])
    body = {k: v for k, v in forged.items() if k != "certificate_fingerprint_sha256"}
    forged["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="artificial optimizer boundary"):
        validate_correlated_location_scale_certificate(forged)


def test_resigned_boundary_correlation_result_fails_closed(fitted_model):
    _, fitted = fitted_model
    certificate = build_correlated_location_scale_certificate(fitted)
    forged_model = deepcopy(certificate["model"])
    forged_model["rho_location_log_scale"] = float(np.tanh(4.0))
    forged = replace(
        fitted,
        rho_location_scale=float(np.tanh(4.0)),
        model_fingerprint_sha256=benchmark_fingerprint(forged_model),
    )
    with pytest.raises(SchemaError, match="artificial optimizer boundary"):
        build_correlated_location_scale_certificate(forged)


def test_certificate_rejects_claim_promotion(fitted_model):
    _, fitted = fitted_model
    certificate = build_correlated_location_scale_certificate(fitted)
    promoted = deepcopy(certificate)
    promoted["claim_boundary"]["random_slopes_modelled"] = True
    body = {k: v for k, v in promoted.items() if k != "certificate_fingerprint_sha256"}
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_correlated_location_scale_certificate(promoted)


def test_result_mutation_and_structural_metadata_guards(fitted_model):
    _, fitted = fitted_model
    fitted.location_coef[0] += 0.2
    try:
        with pytest.raises(SchemaError, match="result identity"):
            build_correlated_location_scale_certificate(fitted)
    finally:
        fitted.location_coef[0] -= 0.2
    with pytest.raises(FrozenInstanceError):
        fitted.rho_location_scale = 0.0


def test_replaced_invalid_rho_is_detected(fitted_model):
    _, fitted = fitted_model
    forged = replace(fitted, rho_location_scale=1.0)
    with pytest.raises(SchemaError, match="result identity|strictly between"):
        build_correlated_location_scale_certificate(forged)


def test_certificate_freeze_roundtrip_and_overwrite_guard(fitted_model, tmp_path):
    _, fitted = fitted_model
    target = tmp_path / "correlated-location-scale.json"
    freeze_correlated_location_scale_certificate(fitted, target)
    validate_correlated_location_scale_certificate(json.loads(target.read_text()))
    with pytest.raises(FileExistsError):
        freeze_correlated_location_scale_certificate(fitted, target)


def test_invalid_spec_missing_group_and_rank_deficiency_fail_closed():
    with pytest.raises(ValueError, match="odd integer"):
        CorrelatedLocationScaleSpec("y", "g", quadrature_points=4)
    with pytest.raises(ValueError, match="must be distinct"):
        CorrelatedLocationScaleSpec("y", "y")
    with pytest.raises(ValueError, match="reserved term"):
        CorrelatedLocationScaleSpec("y", "g", location_predictors=("Intercept",))
    data = _synthetic_correlated(groups=3, n_per_group=4)
    data.loc[0, "participant_id"] = None
    with pytest.raises(SchemaError, match="missing group identity"):
        fit_correlated_location_scale(data, spec=CorrelatedLocationScaleSpec("y", "participant_id"))
    data = _synthetic_correlated(groups=4, n_per_group=5)
    data["x_copy"] = data["x"]
    with pytest.raises(SchemaError, match="rank deficient"):
        fit_correlated_location_scale(
            data,
            spec=CorrelatedLocationScaleSpec(
                "y", "participant_id", ("x", "x_copy"), (), quadrature_points=3
            ),
        )
