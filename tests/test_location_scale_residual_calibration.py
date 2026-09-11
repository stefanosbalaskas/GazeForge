import json
from copy import deepcopy
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.correlated_location_scale import (
    CorrelatedLocationScaleSpec,
    fit_correlated_location_scale,
)
from gazeforge.exceptions import SchemaError
from gazeforge.hierarchical_location_scale import (
    HierarchicalLocationScaleSpec,
    fit_hierarchical_location_scale,
)
from gazeforge.location_scale_residual_calibration import (
    LocationScaleResidualCalibrationSpec,
    _residual_metrics,
    build_location_scale_residual_calibration_certificate,
    calibrate_location_scale_residuals,
    freeze_location_scale_residual_calibration_certificate,
    validate_location_scale_residual_calibration_certificate,
)
from gazeforge.provenance import fingerprint_frame


def _synthetic(seed=41, groups=10, n_per_group=8, rho=0.35):
    rng = np.random.default_rng(seed)
    covariance = np.array(
        [
            [0.45**2, rho * 0.45 * 0.18],
            [rho * 0.45 * 0.18, 0.18**2],
        ]
    )
    effects = rng.multivariate_normal(np.zeros(2), covariance, size=groups)
    rows = []
    for group in range(groups):
        x = rng.normal(size=n_per_group)
        mu = 0.5 + 0.55 * x + effects[group, 0]
        log_sigma = -0.15 + 0.10 * x + effects[group, 1]
        y = rng.normal(mu, np.exp(log_sigma))
        rows.extend(
            (f"p{group}", xx, yy)
            for xx, yy in zip(x, y, strict=True)
        )
    return pd.DataFrame(rows, columns=["participant_id", "x", "y"])


@pytest.fixture(scope="module")
def independent_fit():
    data = _synthetic(rho=0.0)
    spec = HierarchicalLocationScaleSpec(
        "y",
        "participant_id",
        ("x",),
        ("x",),
        quadrature_points=3,
        max_iter=180,
        tolerance=1e-7,
    )
    return data, fit_hierarchical_location_scale(data, spec=spec)


@pytest.fixture(scope="module")
def correlated_fit():
    data = _synthetic(seed=73, groups=12, n_per_group=8, rho=0.50)
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


def _calibration_spec(seed=91):
    return LocationScaleResidualCalibrationSpec(
        n_simulations=60,
        seed=seed,
        envelope_level=0.90,
        max_simulated_residual_draws=50_000,
    )


def test_independent_model_calibration_is_deterministic(independent_fit):
    data, fitted = independent_fit
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
    assert first.model_family == "independent_location_scale"
    assert first.n_obs == len(data)
    assert first.n_groups == data["participant_id"].nunique()
    assert len(first.summary) == 8
    assert len(first.base_model_certificate_fingerprint_sha256) == 64
    assert first.diagnostic_fingerprint_sha256 == second.diagnostic_fingerprint_sha256
    assert (
        first.base_model_certificate_fingerprint_sha256
        == second.base_model_certificate_fingerprint_sha256
    )
    pd.testing.assert_frame_equal(first.summary, second.summary)
    assert first.summary["simulation_percentile"].between(0.0, 1.0).all()


def test_correlated_model_family_is_supported(correlated_fit):
    data, fitted = correlated_fit
    result = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(seed=123),
    )
    assert result.model_family == "correlated_location_scale"
    assert result.model_fingerprint_sha256 == fitted.model_fingerprint_sha256
    assert len(result.base_model_certificate_fingerprint_sha256) == 64
    assert np.isfinite(
        result.summary[
            [
                "observed",
                "simulation_mean",
                "envelope_lower",
                "envelope_upper",
                "simulation_percentile",
            ]
        ].to_numpy(float)
    ).all()


@pytest.mark.parametrize("fixture_name", ["independent_fit", "correlated_fit"])
def test_calibration_rejects_noncertifiable_nonconverged_base_fit(
    fixture_name, request
):
    data, fitted = request.getfixturevalue(fixture_name)
    nonconverged = replace(fitted, converged=False)
    with pytest.raises(SchemaError, match="Only converged .* location-scale fits are certifiable"):
        calibrate_location_scale_residuals(
            nonconverged,
            data,
            spec=_calibration_spec(),
        )


def test_calibration_requires_exact_fitting_input(independent_fit):
    data, fitted = independent_fit
    changed = data.copy()
    changed.loc[0, "y"] += 0.01
    with pytest.raises(SchemaError, match="exact fitted modelling input"):
        calibrate_location_scale_residuals(
            fitted,
            changed,
            spec=_calibration_spec(),
        )


def test_simulation_budget_fails_closed(independent_fit):
    data, fitted = independent_fit
    spec = LocationScaleResidualCalibrationSpec(
        n_simulations=60,
        max_simulated_residual_draws=100,
    )
    with pytest.raises(SchemaError, match="simulation budget exceeded"):
        calibrate_location_scale_residuals(fitted, data, spec=spec)


def test_certificate_rejects_resigned_claim_promotion(independent_fit):
    data, fitted = independent_fit
    result = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )
    certificate = build_location_scale_residual_calibration_certificate(result)
    validate_location_scale_residual_calibration_certificate(certificate)

    promoted = deepcopy(certificate)
    promoted["claim_boundary"]["global_model_adequacy_established"] = True
    body = {
        key: value
        for key, value in promoted.items()
        if key != "certificate_fingerprint_sha256"
    }
    promoted["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="claim boundary"):
        validate_location_scale_residual_calibration_certificate(promoted)


def test_certificate_rejects_fully_resigned_contradictory_envelope_flag(
    independent_fit,
):
    data, fitted = independent_fit
    result = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )
    certificate = build_location_scale_residual_calibration_certificate(result)
    tampered = deepcopy(certificate)
    tampered["summary"][0]["outside_envelope"] = not tampered["summary"][0][
        "outside_envelope"
    ]
    tampered_summary = pd.DataFrame(tampered["summary"])
    summary_columns = [
        "metric",
        "observed",
        "simulation_mean",
        "envelope_lower",
        "envelope_upper",
        "simulation_percentile",
        "outside_envelope",
    ]
    tampered["diagnostic"]["summary_fingerprint_sha256"] = fingerprint_frame(
        tampered_summary.loc[:, summary_columns]
    )
    tampered["diagnostic_fingerprint_sha256"] = benchmark_fingerprint(
        tampered["diagnostic"]
    )
    body = {
        key: value
        for key, value in tampered.items()
        if key != "certificate_fingerprint_sha256"
    }
    tampered["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    with pytest.raises(SchemaError, match="contradict the bounds"):
        validate_location_scale_residual_calibration_certificate(tampered)


def test_summary_mutation_is_detected(independent_fit):
    data, fitted = independent_fit
    result = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )
    tampered = replace(result, summary=result.summary.copy(deep=True))
    tampered.summary.loc[0, "simulation_mean"] += 0.5
    with pytest.raises(SchemaError, match="summary was mutated"):
        build_location_scale_residual_calibration_certificate(tampered)


def test_base_model_certificate_lineage_mutation_is_detected(independent_fit):
    data, fitted = independent_fit
    result = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )
    tampered = replace(
        result,
        base_model_certificate_fingerprint_sha256="0" * 64,
    )
    with pytest.raises(SchemaError, match="diagnostic fingerprint mismatch"):
        build_location_scale_residual_calibration_certificate(tampered)


def test_certificate_freeze_roundtrip_is_key_order_safe(independent_fit, tmp_path):
    data, fitted = independent_fit
    result = calibrate_location_scale_residuals(
        fitted,
        data,
        spec=_calibration_spec(),
    )
    target = tmp_path / "residual-calibration.json"
    freeze_location_scale_residual_calibration_certificate(result, target)
    frozen = json.loads(target.read_text(encoding="utf-8"))
    validate_location_scale_residual_calibration_certificate(frozen)
    assert len(
        frozen["diagnostic"]["base_model_certificate_fingerprint_sha256"]
    ) == 64
    with pytest.raises(FileExistsError):
        freeze_location_scale_residual_calibration_certificate(result, target)


def test_residual_metrics_respond_to_tail_contamination():
    rng = np.random.default_rng(202)
    clean = rng.standard_normal(120)
    contaminated = clean.copy()
    contaminated[:4] = np.array([7.0, -7.0, 8.0, -8.0])
    group_codes = np.repeat(np.arange(12), 10)
    clean_metrics = _residual_metrics(
        clean,
        group_codes,
        12,
        tail_threshold=1.96,
    )
    contaminated_metrics = _residual_metrics(
        contaminated,
        group_codes,
        12,
        tail_threshold=1.96,
    )
    assert contaminated_metrics["absolute_tail_fraction"] > clean_metrics[
        "absolute_tail_fraction"
    ]
    assert contaminated_metrics["residual_excess_kurtosis"] > clean_metrics[
        "residual_excess_kurtosis"
    ]
    assert contaminated_metrics["normal_qq_rmse"] > clean_metrics["normal_qq_rmse"]


def test_invalid_specs_fail_closed():
    with pytest.raises(ValueError, match="50 through 100000"):
        LocationScaleResidualCalibrationSpec(n_simulations=49)
    with pytest.raises(ValueError, match="50 through 100000"):
        LocationScaleResidualCalibrationSpec(n_simulations=100_001)
    with pytest.raises(ValueError, match="between 0.5 and 1.0"):
        LocationScaleResidualCalibrationSpec(envelope_level=1.0)
    with pytest.raises(ValueError, match="non-negative integer"):
        LocationScaleResidualCalibrationSpec(seed=-1)
    with pytest.raises(ValueError, match="positive integer"):
        LocationScaleResidualCalibrationSpec(max_simulated_residual_draws=0)
