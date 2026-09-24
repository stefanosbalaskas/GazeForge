from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

import gazeforge.correlated_location_random_slope_scale as corr
import gazeforge.full_covariance_location_random_slope_scale as full
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError

# ============================================================
# SHARED FIXTURES — NO FITTING
# ============================================================


def _data():
    return pd.DataFrame(
        {
            "y": [
                1.0,
                1.2,
                1.4,
                2.0,
                2.2,
                2.4,
            ],
            "g": [
                "A",
                "A",
                "A",
                "B",
                "B",
                "B",
            ],
            "x": [
                0.0,
                1.0,
                2.0,
                0.0,
                1.0,
                2.0,
            ],
            "z": [
                0.0,
                1.0,
                0.0,
                0.0,
                1.0,
                0.0,
            ],
        }
    )


def _corr_spec(**changes):
    values = {
        "outcome_col": "y",
        "group_col": "g",
        "random_slope_predictor": "x",
        "location_predictors": ("x",),
        "scale_predictors": ("z",),
        "quadrature_points": 3,
        "min_group_size": 3,
        "max_iter": 10,
        "tolerance": 1e-7,
    }

    values.update(changes)

    return corr.CorrelatedLocationRandomSlopeScaleSpec(**values)


def _full_spec(**changes):
    values = {
        "outcome_col": "y",
        "group_col": "g",
        "random_slope_predictor": "x",
        "location_predictors": ("x",),
        "scale_predictors": ("z",),
        "quadrature_points": 3,
        "min_group_size": 3,
        "max_iter": 10,
        "tolerance": 1e-7,
    }

    values.update(changes)

    return full.FullCovarianceLocationRandomSlopeScaleSpec(**values)


def _group_effects():
    return pd.DataFrame(
        {
            "g": ["A", "B"],
            "n_obs": [3, 3],
            "location_intercept_random_mean": [
                0.10,
                -0.10,
            ],
            "location_slope_random_mean": [
                0.05,
                -0.05,
            ],
            "log_scale_random_mean": [
                0.02,
                -0.02,
            ],
        }
    )


def _corr_result():
    spec = _corr_spec()

    location_coef = np.array(
        [1.0, 0.5],
        dtype=float,
    )

    scale_coef = np.array(
        [-0.2, 0.1],
        dtype=float,
    )

    groups = _group_effects()

    identity = corr._model_identity_payload(
        spec=spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept", "z"),
        location_coef=location_coef,
        scale_coef=scale_coef,
        tau_intercept=0.4,
        tau_slope=0.2,
        tau_scale=0.3,
        rho=0.25,
        log_likelihood=-12.0,
        n_obs=6,
        n_groups=2,
        group_effects=groups,
        input_fingerprint="a" * 64,
    )

    return corr.CorrelatedLocationRandomSlopeScaleResult(
        spec=spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept", "z"),
        location_coef=location_coef,
        scale_coef=scale_coef,
        tau_location_intercept=0.4,
        tau_location_slope=0.2,
        tau_scale=0.3,
        rho_location_intercept_slope=0.25,
        log_likelihood=-12.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="synthetic fixture",
        optimizer_iterations=3,
        n_obs=6,
        n_groups=2,
        group_effects=groups,
        input_fingerprint_sha256="a" * 64,
        model_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def _full_result():
    spec = _full_spec()

    r01 = 0.20
    r02 = -0.10
    partial = 0.30

    _, r12 = full._correlation_matrix_from_coordinates(
        r01,
        r02,
        partial,
    )

    location_coef = np.array(
        [1.0, 0.5],
        dtype=float,
    )

    scale_coef = np.array(
        [-0.2, 0.1],
        dtype=float,
    )

    groups = _group_effects()

    identity = full._model_identity_payload(
        spec=spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept", "z"),
        location_coef=location_coef,
        scale_coef=scale_coef,
        tau_intercept=0.4,
        tau_slope=0.2,
        tau_scale=0.3,
        rho_intercept_slope=r01,
        rho_intercept_scale=r02,
        rho_slope_scale=r12,
        partial_rho_slope_scale_given_intercept=partial,
        log_likelihood=-13.0,
        n_obs=6,
        n_groups=2,
        group_effects=groups,
        input_fingerprint="b" * 64,
    )

    return full.FullCovarianceLocationRandomSlopeScaleResult(
        spec=spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept", "z"),
        location_coef=location_coef,
        scale_coef=scale_coef,
        tau_location_intercept=0.4,
        tau_location_slope=0.2,
        tau_scale=0.3,
        rho_location_intercept_slope=r01,
        rho_location_intercept_log_scale=r02,
        rho_location_slope_log_scale=r12,
        partial_rho_location_slope_log_scale_given_intercept=partial,
        log_likelihood=-13.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="synthetic fixture",
        optimizer_iterations=3,
        n_obs=6,
        n_groups=2,
        group_effects=groups,
        input_fingerprint_sha256="b" * 64,
        model_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def _resign_corr(certificate):
    certificate["model_fingerprint_sha256"] = benchmark_fingerprint(certificate["model"])

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def _resign_full(certificate):
    certificate["model_fingerprint_sha256"] = benchmark_fingerprint(certificate["model"])

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


# ============================================================
# CORRELATED RANDOM-SLOPE PURE HELPERS
# ============================================================


def test_corr_spec_reuses_canonical_contract():
    spec = _corr_spec()

    assert spec.outcome_col == "y"
    assert spec.group_col == "g"
    assert spec.random_slope_predictor == "x"
    assert spec.location_predictors == ("x",)


def test_corr_spec_invalid_propagates():
    with pytest.raises(
        ValueError,
        match="must also appear",
    ):
        _corr_spec(location_predictors=())


def test_corr_initial_parameters_adds_eta():
    prepared = corr._prepare_model(
        _data(),
        _corr_spec(),
    )

    independent = corr._independent_initial_parameters(prepared)

    correlated = corr._initial_parameters(prepared)

    assert len(correlated) == len(independent) + 1
    assert correlated[-1] == 0.0


def test_corr_unpack():
    values = corr._unpack(
        np.array(
            [
                1.0,
                2.0,
                3.0,
                4.0,
                np.log(0.4),
                np.log(0.2),
                np.log(0.3),
                0.25,
            ]
        ),
        2,
        2,
    )

    assert values[0].tolist() == [1.0, 2.0]
    assert values[1].tolist() == [3.0, 4.0]

    assert values[2:5] == pytest.approx((0.4, 0.2, 0.3))

    assert values[5] == pytest.approx(np.tanh(0.25))


def test_corr_latent_parameterization_valid():
    latent, delta = corr._latent_location_parameterization(
        0.4,
        0.2,
        0.25,
    )

    assert latent > 0
    assert np.isfinite(delta)


@pytest.mark.parametrize(
    ("tau0", "tau1", "rho"),
    [
        (0.0, 0.2, 0.0),
        (0.4, 0.0, 0.0),
        (np.nan, 0.2, 0.0),
        (0.4, np.nan, 0.0),
        (0.4, 0.2, 1.0),
        (0.4, 0.2, -1.0),
    ],
)
def test_corr_latent_parameterization_invalid(
    tau0,
    tau1,
    rho,
):
    with pytest.raises(
        ValueError,
        match="numerically unsupported",
    ):
        corr._latent_location_parameterization(
            tau0,
            tau1,
            rho,
        )


@pytest.mark.parametrize(
    "rho",
    [
        np.nan,
        np.inf,
        corr._MAX_ABS_CERTIFIABLE_RHO,
        -corr._MAX_ABS_CERTIFIABLE_RHO,
    ],
)
def test_corr_correlation_boundary_true(
    rho,
):
    assert corr._correlation_at_numerical_boundary(rho)


def test_corr_correlation_boundary_false():
    assert not corr._correlation_at_numerical_boundary(0.25)


def test_corr_latent_boundary_invalid_covariance():
    assert corr._latent_intercept_boundary_reached(
        0.4,
        0.2,
        1.0,
    )


def test_corr_latent_boundary_safe():
    assert not corr._latent_intercept_boundary_reached(
        0.4,
        0.2,
        0.25,
    )


def test_corr_effective_slope_values():
    effective, latent, delta = corr._effective_slope_values(
        np.array([0.0, 1.0, 2.0]),
        0.4,
        0.2,
        0.25,
    )

    assert np.isfinite(effective).all()
    assert latent > 0
    assert np.isfinite(delta)


def test_corr_effective_slope_nonfinite():
    with pytest.raises(
        ValueError,
        match="non-finite",
    ):
        corr._effective_slope_values(
            np.array([0.0, np.inf]),
            0.4,
            0.2,
            0.25,
        )


def test_corr_objective_nonfinite_theta():
    prepared = corr._prepare_model(
        _data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    objective = corr._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = corr._initial_parameters(prepared)

    theta[0] = np.nan

    assert objective(theta) == 1e100


def test_corr_objective_invalid_tau():
    prepared = corr._prepare_model(
        _data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    objective = corr._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = corr._initial_parameters(prepared)

    theta[-4] = np.log(corr._MIN_RANDOM_EFFECT_SD / 10)

    assert objective(theta) == 1e100


def test_corr_objective_invalid_covariance():
    prepared = corr._prepare_model(
        _data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    objective = corr._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = corr._initial_parameters(prepared)

    theta[-1] = 100.0

    assert objective(theta) == 1e100


def test_corr_objective_quadrature_failure(
    monkeypatch,
):
    prepared = corr._prepare_model(
        _data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    monkeypatch.setattr(
        corr,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty((0, 3)),
            np.empty(0),
            np.zeros(3),
        ),
    )

    objective = corr._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(corr._initial_parameters(prepared)) == 1e100


def test_corr_objective_mock_success(
    monkeypatch,
):
    prepared = corr._prepare_model(
        _data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    monkeypatch.setattr(
        corr,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -2.0,
            np.zeros((1, 3)),
            np.ones(1),
            np.zeros(3),
        ),
    )

    objective = corr._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(corr._initial_parameters(prepared)) == pytest.approx(4.0)


def test_corr_posterior_failure(
    monkeypatch,
):
    prepared = corr._prepare_model(
        _data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    monkeypatch.setattr(
        corr,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty((0, 3)),
            np.empty(0),
            np.zeros(3),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="recovering correlated",
    ):
        corr._posterior_group_effects(
            prepared,
            _corr_spec(),
            np.array([1.0, 0.5]),
            np.array([-0.2, 0.1]),
            0.4,
            0.2,
            0.3,
            0.25,
            nodes,
            weights,
        )


def test_corr_posterior_mock_success(
    monkeypatch,
):
    prepared = corr._prepare_model(
        _data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    monkeypatch.setattr(
        corr,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -2.0,
            np.zeros((1, 3)),
            np.ones(1),
            np.zeros(3),
        ),
    )

    result = corr._posterior_group_effects(
        prepared,
        _corr_spec(),
        np.array([1.0, 0.5]),
        np.array([-0.2, 0.1]),
        0.4,
        0.2,
        0.3,
        0.25,
        nodes,
        weights,
    )

    assert len(result) == 2
    assert "location_slope_random_mean" in result.columns


# ============================================================
# CORRELATED SYNTHETIC RESULT
# ============================================================


def test_corr_fixed_effects():
    result = _corr_result()

    table = result.fixed_effects()

    assert len(table) == 4


def test_corr_random_effect_correlation():
    assert _corr_result().random_effect_correlation() == pytest.approx(0.25)


def test_corr_prediction_known():
    predicted = corr.predict_correlated_location_random_slope_scale(
        _corr_result(),
        pd.DataFrame(
            {
                "g": ["A"],
                "x": [1.0],
                "z": [0.0],
            }
        ),
    )

    assert bool(predicted["group_effect_used"].iloc[0])


def test_corr_prediction_population_only():
    predicted = corr.predict_correlated_location_random_slope_scale(
        _corr_result(),
        pd.DataFrame(
            {
                "g": ["A"],
                "x": [1.0],
                "z": [0.0],
            }
        ),
        include_group_effects=False,
    )

    assert not bool(predicted["group_effect_used"].iloc[0])


def test_corr_prediction_unseen_rejected():
    with pytest.raises(
        SchemaError,
        match="unseen groups",
    ):
        corr.predict_correlated_location_random_slope_scale(
            _corr_result(),
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [1.0],
                    "z": [0.0],
                }
            ),
            allow_new_groups=False,
        )


def test_corr_prediction_missing_group():
    with pytest.raises(
        SchemaError,
        match="complete",
    ):
        corr.predict_correlated_location_random_slope_scale(
            _corr_result(),
            pd.DataFrame(
                {
                    "g": [None],
                    "x": [1.0],
                    "z": [0.0],
                }
            ),
        )


def test_corr_prediction_bad_slope():
    with pytest.raises(
        SchemaError,
        match="finite and numeric",
    ):
        corr.predict_correlated_location_random_slope_scale(
            _corr_result(),
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [np.nan],
                    "z": [0.0],
                }
            ),
        )


def test_corr_prediction_extreme_scale():
    result = replace(
        _corr_result(),
        scale_coef=np.array([30.0, 0.0]),
    )

    identity = corr._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        RuntimeError,
        match="numerically supported range",
    ):
        corr.predict_correlated_location_random_slope_scale(
            result,
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [0.0],
                    "z": [0.0],
                }
            ),
        )


def test_corr_diagnostics_bad_outcome():
    data = _data()
    data.loc[0, "y"] = np.nan

    with pytest.raises(
        SchemaError,
        match="finite for diagnostics",
    ):
        corr.correlated_location_random_slope_scale_diagnostics(
            _corr_result(),
            data,
        )


def test_corr_diagnostics_valid():
    result = corr.correlated_location_random_slope_scale_diagnostics(
        _corr_result(),
        _data(),
    )

    assert "standardized_residual" in result


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "g" * 64,
        "a" * 63,
    ],
)
def test_corr_sha_invalid(value):
    assert not corr._is_sha256_hex(value)


def test_corr_sha_valid():
    assert corr._is_sha256_hex("a" * 64)


def test_corr_result_identity_guard():
    with pytest.raises(
        SchemaError,
        match="result identity",
    ):
        corr._validate_result_identity(
            replace(
                _corr_result(),
                model_fingerprint_sha256=("0" * 64),
            )
        )


def test_corr_result_input_fp_guard():
    result = replace(
        _corr_result(),
        input_fingerprint_sha256="bad",
    )

    identity = corr._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="input fingerprint",
    ):
        corr._validate_result_identity(result)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "tau_location_intercept",
            0.0,
        ),
        (
            "tau_location_slope",
            np.nan,
        ),
        (
            "tau_scale",
            -1.0,
        ),
    ],
)
def test_corr_result_sd_guard(
    field,
    value,
):
    result = replace(
        _corr_result(),
        **{field: value},
    )

    identity = corr._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="finite and positive",
    ):
        corr._validate_result_identity(result)


def test_corr_result_sd_boundary():
    result = replace(
        _corr_result(),
        tau_scale=(corr._MAX_LOG_SCALE_RANDOM_EFFECT_SD),
    )

    identity = corr._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="artificial numerical boundary",
    ):
        corr._validate_result_identity(result)


def test_corr_result_correlation_boundary():
    result = replace(
        _corr_result(),
        rho_location_intercept_slope=(corr._MAX_ABS_CERTIFIABLE_RHO),
    )

    identity = corr._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="optimizer boundary",
    ):
        corr._validate_result_identity(result)


def test_corr_result_count_guard():
    result = replace(
        _corr_result(),
        n_obs=5,
    )

    identity = corr._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="counts are inconsistent",
    ):
        corr._validate_result_identity(result)


# ============================================================
# CORRELATED CERTIFICATE
# ============================================================


def test_corr_certificate_valid():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_schema():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["schema"] = "bad"
    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
        match="Unsupported",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_fingerprint():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        SchemaError,
        match="fingerprint mismatch",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_claim_boundary():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["claim_boundary"]["causal_effects_established"] = True

    body = {key: value for key, value in cert.items() if key != "certificate_fingerprint_sha256"}

    cert["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        SchemaError,
        match="claim boundary",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_extra_model_field():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"]["extra"] = True
    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_invalid_spec():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"]["spec"]["quadrature_points"] = 2

    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
        match="invalid model spec",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        (
            "location_fixed_effects",
            "Location fixed-effect terms",
        ),
        (
            "scale_fixed_effects",
            "Scale fixed-effect terms",
        ),
    ],
)
def test_corr_certificate_term_guard(
    field,
    message,
):
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"][field] = {"Intercept": 1.0}

    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
        match=message,
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


@pytest.mark.parametrize(
    "field",
    [
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    ],
)
def test_corr_certificate_sha_guard(field):
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"][field] = "bad"
    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
        match="fingerprint",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_nonfinite():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"]["tau_location_intercept"] = np.nan

    _resign_corr(cert)

    with pytest.raises(SchemaError):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_nonpositive_sd():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"]["tau_location_slope"] = 0.0

    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
        match="standard deviations must be positive",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_sd_boundary():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"]["tau_log_scale"] = corr._MAX_LOG_SCALE_RANDOM_EFFECT_SD

    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
        match="numerical boundary",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_rho_boundary():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"]["rho_location_intercept_slope"] = corr._MAX_ABS_CERTIFIABLE_RHO

    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
        match="optimizer boundary",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n_obs", True),
        ("n_obs", 0),
        ("n_groups", True),
        ("n_groups", 1),
    ],
)
def test_corr_certificate_counts(
    field,
    value,
):
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"][field] = value
    _resign_corr(cert)

    with pytest.raises(SchemaError):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


def test_corr_certificate_min_group():
    cert = corr.build_correlated_location_random_slope_scale_certificate(_corr_result())

    cert["model"]["n_obs"] = 5
    _resign_corr(cert)

    with pytest.raises(
        SchemaError,
        match="min_group_size",
    ):
        corr.validate_correlated_location_random_slope_scale_certificate(cert)


# ============================================================
# FULL-COVARIANCE PURE HELPERS
# ============================================================


def test_full_spec_reuses_canonical_contract():
    spec = _full_spec()

    assert spec.random_slope_predictor == "x"
    assert spec.location_predictors == ("x",)


def test_full_invalid_spec_propagates():
    with pytest.raises(
        ValueError,
        match="must also appear",
    ):
        _full_spec(location_predictors=())


def test_full_initial_parameters_adds_three_etas():
    prepared = full._prepare_model(
        _data(),
        _full_spec(),
    )

    independent = full._independent_initial_parameters(prepared)

    values = full._initial_parameters(prepared)

    assert len(values) == len(independent) + 3

    assert values[-3:].tolist() == [
        0.0,
        0.0,
        0.0,
    ]


def test_full_correlation_from_etas():
    matrix, r01, r02, r12, partial = full._correlation_matrix_from_etas(
        0.2,
        -0.1,
        0.3,
    )

    assert matrix.shape == (3, 3)
    assert r01 == pytest.approx(np.tanh(0.2))

    assert r02 == pytest.approx(np.tanh(-0.1))

    assert partial == pytest.approx(np.tanh(0.3))

    assert -1 < r12 < 1


@pytest.mark.parametrize(
    ("r01", "r02", "partial"),
    [
        (1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, np.nan, 0.0),
        (0.0, 0.0, np.inf),
    ],
)
def test_full_coordinate_input_guard(
    r01,
    r02,
    partial,
):
    with pytest.raises(
        ValueError,
        match="strictly inside",
    ):
        full._correlation_matrix_from_coordinates(
            r01,
            r02,
            partial,
        )


def test_full_coordinate_valid():
    matrix, r12 = full._correlation_matrix_from_coordinates(
        0.2,
        -0.1,
        0.3,
    )

    assert matrix.shape == (3, 3)
    assert np.allclose(
        matrix,
        matrix.T,
    )

    assert -1 < r12 < 1


def test_full_coordinate_cholesky_failure(
    monkeypatch,
):
    def fail(_):
        raise np.linalg.LinAlgError("forced")

    monkeypatch.setattr(
        full.np.linalg,
        "cholesky",
        fail,
    )

    with pytest.raises(
        ValueError,
        match="not positive definite",
    ):
        full._correlation_matrix_from_coordinates(
            0.2,
            -0.1,
            0.3,
        )


def test_full_coordinate_numerically_unsupported(
    monkeypatch,
):
    monkeypatch.setattr(
        full.np.linalg,
        "cholesky",
        lambda matrix: np.diag([1.0, 1.0, 1e-8]),
    )

    with pytest.raises(
        ValueError,
        match="numerically unsupported",
    ):
        full._correlation_matrix_from_coordinates(
            0.2,
            -0.1,
            0.3,
        )


@pytest.mark.parametrize(
    "taus",
    [
        (0.0, 0.2, 0.3),
        (0.4, -1.0, 0.3),
        (0.4, 0.2, np.nan),
    ],
)
def test_full_population_covariance_tau_guard(
    taus,
):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        full._population_covariance(
            *taus,
            0.2,
            -0.1,
            0.3,
        )


def test_full_population_covariance_valid():
    covariance, precision, logdet, r12 = full._population_covariance(
        0.4,
        0.2,
        0.3,
        0.2,
        -0.1,
        0.3,
    )

    assert covariance.shape == (3, 3)
    assert precision.shape == (3, 3)
    assert np.isfinite(logdet)
    assert -1 < r12 < 1


def test_full_population_covariance_bad_slogdet(
    monkeypatch,
):
    monkeypatch.setattr(
        full.np.linalg,
        "slogdet",
        lambda matrix: (
            -1.0,
            0.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="numerically unsupported",
    ):
        full._population_covariance(
            0.4,
            0.2,
            0.3,
            0.2,
            -0.1,
            0.3,
        )


def test_full_population_covariance_inverse_failure(
    monkeypatch,
):
    def fail(_):
        raise np.linalg.LinAlgError("forced")

    monkeypatch.setattr(
        full.np.linalg,
        "inv",
        fail,
    )

    with pytest.raises(
        ValueError,
        match="singular",
    ):
        full._population_covariance(
            0.4,
            0.2,
            0.3,
            0.2,
            -0.1,
            0.3,
        )


def test_full_population_covariance_nonfinite_precision(
    monkeypatch,
):
    monkeypatch.setattr(
        full.np.linalg,
        "inv",
        lambda matrix: np.full(
            (3, 3),
            np.nan,
        ),
    )

    with pytest.raises(
        ValueError,
        match="non-finite",
    ):
        full._population_covariance(
            0.4,
            0.2,
            0.3,
            0.2,
            -0.1,
            0.3,
        )


def test_full_covariance_parameters_valid():
    covariance = full._population_covariance(
        0.4,
        0.2,
        0.3,
        0.2,
        -0.1,
        0.3,
    )[0]

    values = full._covariance_parameters_from_matrix(covariance)

    assert values[:3] == pytest.approx((0.4, 0.2, 0.3))


@pytest.mark.parametrize(
    "value",
    [
        np.ones((2, 2)),
        np.full((3, 3), np.nan),
    ],
)
def test_full_covariance_parameters_shape(
    value,
):
    with pytest.raises(
        ValueError,
        match="finite 3x3",
    ):
        full._covariance_parameters_from_matrix(value)


def test_full_covariance_parameters_symmetry():
    matrix = np.eye(3)
    matrix[0, 1] = 0.2

    with pytest.raises(
        ValueError,
        match="symmetric",
    ):
        full._covariance_parameters_from_matrix(matrix)


def test_full_covariance_parameters_positive_definite():
    matrix = np.array(
        [
            [1.0, 2.0, 0.0],
            [2.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )

    with pytest.raises(
        ValueError,
        match="positive definite",
    ):
        full._covariance_parameters_from_matrix(matrix)


@pytest.mark.parametrize(
    "shift",
    [
        "bad",
        None,
        True,
    ],
)
def test_full_transform_shift_type(
    shift,
):
    with pytest.raises(
        TypeError,
        match="finite real number",
    ):
        full.transform_full_covariance_for_predictor_shift(
            np.eye(3),
            shift=shift,
        )


def test_full_transform_shift_nonfinite():
    with pytest.raises(
        ValueError,
        match="shift must be finite",
    ):
        full.transform_full_covariance_for_predictor_shift(
            np.eye(3),
            shift=np.nan,
        )


def test_full_transform_shift_valid():
    covariance = full._population_covariance(
        0.4,
        0.2,
        0.3,
        0.2,
        -0.1,
        0.3,
    )[0]

    shifted = full.transform_full_covariance_for_predictor_shift(
        covariance,
        shift=2.0,
    )

    assert shifted.shape == (3, 3)
    assert np.allclose(
        shifted,
        shifted.T,
    )


def test_full_unpack():
    values = full._unpack(
        np.array(
            [
                1.0,
                2.0,
                3.0,
                4.0,
                np.log(0.4),
                np.log(0.2),
                np.log(0.3),
                0.2,
                -0.1,
                0.3,
            ]
        ),
        2,
        2,
    )

    assert values[2:5] == pytest.approx((0.4, 0.2, 0.3))


@pytest.mark.parametrize(
    "value",
    [
        np.nan,
        np.inf,
        full._MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE,
        -full._MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE,
    ],
)
def test_full_correlation_coordinate_boundary(
    value,
):
    assert full._correlation_coordinate_at_numerical_boundary(value)


def test_full_correlation_coordinate_safe():
    assert not (full._correlation_coordinate_at_numerical_boundary(0.2))


def test_full_integrand_extreme_scale():
    value, gradient, hessian = full._group_log_integrand(
        np.array([0.0, 0.0, 30.0]),
        np.array([1.0]),
        np.ones((1, 1)),
        np.ones((1, 1)),
        np.array([0.0]),
        np.array([1.0]),
        np.array([0.0]),
        np.eye(3),
        0.0,
    )

    assert value == -np.inf
    assert gradient.shape == (3,)
    assert hessian.shape == (3, 3)


def test_full_integrand_valid():
    value, gradient, hessian = full._group_log_integrand(
        np.zeros(3),
        np.array([1.0, 1.2]),
        np.ones((2, 1)),
        np.ones((2, 1)),
        np.array([0.0, 1.0]),
        np.array([1.0]),
        np.array([0.0]),
        np.eye(3),
        0.0,
    )

    assert np.isfinite(value)
    assert np.isfinite(gradient).all()
    assert np.isfinite(hessian).all()


def test_full_objective_nonfinite_theta():
    prepared = full._prepare_model(
        _data(),
        _full_spec(),
    )

    nodes, weights = full._quadrature(_full_spec())

    objective = full._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = full._initial_parameters(prepared)

    theta[0] = np.nan

    assert objective(theta) == 1e100


def test_full_objective_invalid_tau():
    prepared = full._prepare_model(
        _data(),
        _full_spec(),
    )

    nodes, weights = full._quadrature(_full_spec())

    objective = full._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = full._initial_parameters(prepared)

    theta[-6] = np.log(full._MIN_RANDOM_EFFECT_SD / 10)

    assert objective(theta) == 1e100


def test_full_objective_quadrature_failure(
    monkeypatch,
):
    prepared = full._prepare_model(
        _data(),
        _full_spec(),
    )

    nodes, weights = full._quadrature(_full_spec())

    monkeypatch.setattr(
        full,
        "_adaptive_group_quadrature_full_covariance",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty((0, 3)),
            np.empty(0),
            np.zeros(3),
        ),
    )

    objective = full._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(full._initial_parameters(prepared)) == 1e100


def test_full_objective_mock_success(
    monkeypatch,
):
    prepared = full._prepare_model(
        _data(),
        _full_spec(),
    )

    nodes, weights = full._quadrature(_full_spec())

    monkeypatch.setattr(
        full,
        "_adaptive_group_quadrature_full_covariance",
        lambda *args, **kwargs: (
            -2.0,
            np.zeros((1, 3)),
            np.ones(1),
            np.zeros(3),
        ),
    )

    objective = full._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(full._initial_parameters(prepared)) == pytest.approx(4.0)


def test_full_posterior_failure(
    monkeypatch,
):
    prepared = full._prepare_model(
        _data(),
        _full_spec(),
    )

    nodes, weights = full._quadrature(_full_spec())

    monkeypatch.setattr(
        full,
        "_adaptive_group_quadrature_full_covariance",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty((0, 3)),
            np.empty(0),
            np.zeros(3),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="recovering full-covariance",
    ):
        full._posterior_group_effects(
            prepared,
            _full_spec(),
            np.array([1.0, 0.5]),
            np.array([-0.2, 0.1]),
            0.4,
            0.2,
            0.3,
            0.2,
            -0.1,
            0.3,
            nodes,
            weights,
        )


def test_full_posterior_mock_success(
    monkeypatch,
):
    prepared = full._prepare_model(
        _data(),
        _full_spec(),
    )

    nodes, weights = full._quadrature(_full_spec())

    monkeypatch.setattr(
        full,
        "_adaptive_group_quadrature_full_covariance",
        lambda *args, **kwargs: (
            -2.0,
            np.zeros((1, 3)),
            np.ones(1),
            np.zeros(3),
        ),
    )

    result = full._posterior_group_effects(
        prepared,
        _full_spec(),
        np.array([1.0, 0.5]),
        np.array([-0.2, 0.1]),
        0.4,
        0.2,
        0.3,
        0.2,
        -0.1,
        0.3,
        nodes,
        weights,
    )

    assert len(result) == 2


# ============================================================
# FULL-COVARIANCE SYNTHETIC RESULT
# ============================================================


def test_full_fixed_effects():
    assert len(_full_result().fixed_effects()) == 4


def test_full_correlation_matrix_method():
    matrix = _full_result().random_effect_correlation_matrix()

    assert matrix.shape == (3, 3)


def test_full_covariance_matrix_method():
    matrix = _full_result().random_effect_covariance_matrix()

    assert matrix.shape == (3, 3)


def test_full_prediction_known():
    predicted = full.predict_full_covariance_location_random_slope_scale(
        _full_result(),
        pd.DataFrame(
            {
                "g": ["A"],
                "x": [1.0],
                "z": [0.0],
            }
        ),
    )

    assert bool(predicted["group_effect_used"].iloc[0])


def test_full_prediction_population_only():
    predicted = full.predict_full_covariance_location_random_slope_scale(
        _full_result(),
        pd.DataFrame(
            {
                "g": ["A"],
                "x": [1.0],
                "z": [0.0],
            }
        ),
        include_group_effects=False,
    )

    assert not bool(predicted["group_effect_used"].iloc[0])


def test_full_prediction_unseen_rejected():
    with pytest.raises(
        SchemaError,
        match="unseen groups",
    ):
        full.predict_full_covariance_location_random_slope_scale(
            _full_result(),
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [1.0],
                    "z": [0.0],
                }
            ),
            allow_new_groups=False,
        )


def test_full_prediction_bad_slope():
    with pytest.raises(
        SchemaError,
        match="finite and numeric",
    ):
        full.predict_full_covariance_location_random_slope_scale(
            _full_result(),
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [np.nan],
                    "z": [0.0],
                }
            ),
        )


def test_full_prediction_missing_group():
    with pytest.raises(
        SchemaError,
        match="complete",
    ):
        full.predict_full_covariance_location_random_slope_scale(
            _full_result(),
            pd.DataFrame(
                {
                    "g": [None],
                    "x": [1.0],
                    "z": [0.0],
                }
            ),
        )


def test_full_prediction_extreme_scale():
    result = replace(
        _full_result(),
        scale_coef=np.array([30.0, 0.0]),
    )

    identity = full._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        RuntimeError,
        match="numerically supported range",
    ):
        full.predict_full_covariance_location_random_slope_scale(
            result,
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [0.0],
                    "z": [0.0],
                }
            ),
        )


def test_full_diagnostics_bad_outcome():
    data = _data()
    data.loc[0, "y"] = np.nan

    with pytest.raises(
        SchemaError,
        match="finite for diagnostics",
    ):
        full.full_covariance_location_random_slope_scale_diagnostics(
            _full_result(),
            data,
        )


def test_full_diagnostics_valid():
    output = full.full_covariance_location_random_slope_scale_diagnostics(
        _full_result(),
        _data(),
    )

    assert "standardized_residual" in output


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "g" * 64,
        "a" * 63,
    ],
)
def test_full_sha_invalid(value):
    assert not full._is_sha256_hex(value)


def test_full_sha_valid():
    assert full._is_sha256_hex("a" * 64)


def test_full_coordinate_validation_mismatch():
    with pytest.raises(
        SchemaError,
        match="inconsistent",
    ):
        full._validate_correlation_coordinates(
            rho_intercept_slope=0.2,
            rho_intercept_scale=-0.1,
            rho_slope_scale=0.9,
            partial_rho_slope_scale_given_intercept=0.3,
        )


def test_full_coordinate_validation_boundary():
    result = _full_result()

    with pytest.raises(
        SchemaError,
        match="optimizer boundary",
    ):
        full._validate_correlation_coordinates(
            rho_intercept_slope=(full._MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE),
            rho_intercept_scale=(result.rho_location_intercept_log_scale),
            rho_slope_scale=(result.rho_location_slope_log_scale),
            partial_rho_slope_scale_given_intercept=(
                result.partial_rho_location_slope_log_scale_given_intercept
            ),
        )


def test_full_coordinate_validation_value_error(
    monkeypatch,
):
    monkeypatch.setattr(
        full,
        "_correlation_matrix_from_coordinates",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("forced")),
    )

    with pytest.raises(
        SchemaError,
        match="numerically unsupported",
    ):
        full._validate_correlation_coordinates(
            rho_intercept_slope=0.2,
            rho_intercept_scale=-0.1,
            rho_slope_scale=0.1,
            partial_rho_slope_scale_given_intercept=0.3,
        )


def test_full_coordinate_validation_nonfinite_matrix(
    monkeypatch,
):
    monkeypatch.setattr(
        full,
        "_correlation_matrix_from_coordinates",
        lambda *args, **kwargs: (
            np.full(
                (3, 3),
                np.nan,
            ),
            0.1,
        ),
    )

    with pytest.raises(
        SchemaError,
        match="non-finite",
    ):
        full._validate_correlation_coordinates(
            rho_intercept_slope=0.2,
            rho_intercept_scale=-0.1,
            rho_slope_scale=0.1,
            partial_rho_slope_scale_given_intercept=0.3,
        )


def test_full_result_identity_guard():
    with pytest.raises(
        SchemaError,
        match="result identity",
    ):
        full._validate_result_identity(
            replace(
                _full_result(),
                model_fingerprint_sha256=("0" * 64),
            )
        )


def test_full_result_input_fp_guard():
    result = replace(
        _full_result(),
        input_fingerprint_sha256="bad",
    )

    identity = full._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="input fingerprint",
    ):
        full._validate_result_identity(result)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "tau_location_intercept",
            0.0,
        ),
        (
            "tau_location_slope",
            np.nan,
        ),
        (
            "tau_scale",
            -1.0,
        ),
    ],
)
def test_full_result_sd_guard(
    field,
    value,
):
    result = replace(
        _full_result(),
        **{field: value},
    )

    identity = full._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="finite and positive",
    ):
        full._validate_result_identity(result)


def test_full_result_sd_boundary():
    result = replace(
        _full_result(),
        tau_scale=(full._MAX_LOG_SCALE_RANDOM_EFFECT_SD),
    )

    identity = full._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="artificial numerical boundary",
    ):
        full._validate_result_identity(result)


def test_full_result_count_guard():
    result = replace(
        _full_result(),
        n_obs=5,
    )

    identity = full._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="counts are inconsistent",
    ):
        full._validate_result_identity(result)


# ============================================================
# FULL-COVARIANCE CERTIFICATE
# ============================================================


def test_full_certificate_valid():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_schema():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["schema"] = "bad"
    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match="Unsupported",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_fingerprint():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        SchemaError,
        match="fingerprint mismatch",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_claim():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["claim_boundary"]["causal_effects_established"] = True

    body = {key: value for key, value in cert.items() if key != "certificate_fingerprint_sha256"}

    cert["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        SchemaError,
        match="claim boundary",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_extra_model_field():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"]["extra"] = True
    _resign_full(cert)

    with pytest.raises(SchemaError):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_invalid_spec():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"]["spec"]["quadrature_points"] = 2

    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match="invalid model spec",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        (
            "location_fixed_effects",
            "Location fixed-effect terms",
        ),
        (
            "scale_fixed_effects",
            "Scale fixed-effect terms",
        ),
    ],
)
def test_full_certificate_term_guard(
    field,
    message,
):
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"][field] = {"Intercept": 1.0}

    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match=message,
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


@pytest.mark.parametrize(
    "field",
    [
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    ],
)
def test_full_certificate_sha_guard(field):
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"][field] = "bad"
    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match="fingerprint",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_nonfinite():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"]["rho_location_intercept_slope"] = np.nan

    _resign_full(cert)

    with pytest.raises(SchemaError):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_nonpositive_sd():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"]["tau_location_slope"] = 0.0

    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match="standard deviations must be positive",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_sd_boundary():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"]["tau_log_scale"] = full._MAX_LOG_SCALE_RANDOM_EFFECT_SD

    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match="numerical boundary",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_correlation_mismatch():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"]["rho_location_slope_log_scale"] += 0.1

    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match="inconsistent",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_correlation_boundary():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"]["rho_location_intercept_slope"] = full._MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE

    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match="optimizer boundary",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n_obs", True),
        ("n_obs", 0),
        ("n_groups", True),
        ("n_groups", 1),
    ],
)
def test_full_certificate_counts(
    field,
    value,
):
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"][field] = value
    _resign_full(cert)

    with pytest.raises(SchemaError):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)


def test_full_certificate_min_group():
    cert = full.build_full_covariance_location_random_slope_scale_certificate(_full_result())

    cert["model"]["n_obs"] = 5
    _resign_full(cert)

    with pytest.raises(
        SchemaError,
        match="min_group_size",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(cert)
