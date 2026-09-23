from __future__ import annotations

import copy
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from test_location_scale_bootstrap_monte_carlo import _synthetic_bootstrap

import gazeforge._location_scale_bootstrap_monte_carlo_core as mc
import gazeforge.correlated_location_random_slope_scale as correlated_slope
import gazeforge.full_covariance_location_random_slope_scale as full
import gazeforge.hierarchical_location_scale as hierarchical
import gazeforge.location_random_slope_scale as random_slope
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError

# =====================================================================
# SHARED CERTIFICATE HELPERS
# =====================================================================


def _seal(module, model):
    body = {
        "schema": module._CERTIFICATE_SCHEMA,
        "model": model,
        "model_fingerprint_sha256": benchmark_fingerprint(model),
        "optimizer": {
            "converged": True,
            "status": 0,
            "message": "converged",
            "iterations": 3,
        },
        "claim_boundary": dict(module._CLAIM_BOUNDARY),
    }

    return {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }


def _resign(certificate, *, model_changed=True):
    if model_changed:
        certificate["model_fingerprint_sha256"] = benchmark_fingerprint(certificate["model"])

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def _hierarchical_certificate():
    spec = hierarchical.HierarchicalLocationScaleSpec(
        outcome_col="y",
        group_col="g",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=3,
        min_group_size=2,
    )

    model = {
        "spec": spec.to_dict(),
        "location_fixed_effects": {
            "Intercept": 0.1,
            "x": 0.5,
        },
        "scale_fixed_effects": {
            "Intercept": -0.2,
            "x": 0.1,
        },
        "tau_location": 0.5,
        "tau_log_scale": 0.2,
        "log_likelihood": -10.0,
        "n_obs": 4,
        "n_groups": 2,
        "group_effects_fingerprint_sha256": "a" * 64,
        "input_fingerprint_sha256": "b" * 64,
    }

    return _seal(
        hierarchical,
        model,
    )


def _correlated_slope_certificate():
    spec = correlated_slope.CorrelatedLocationRandomSlopeScaleSpec(
        outcome_col="y",
        group_col="g",
        random_slope_predictor="x",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=3,
        min_group_size=3,
    )

    model = {
        "spec": spec.to_dict(),
        "location_fixed_effects": {
            "Intercept": 0.1,
            "x": 0.5,
        },
        "scale_fixed_effects": {
            "Intercept": -0.2,
            "x": 0.1,
        },
        "tau_location_intercept": 0.5,
        "tau_location_slope": 0.3,
        "tau_log_scale": 0.2,
        "rho_location_intercept_slope": 0.25,
        "log_likelihood": -20.0,
        "n_obs": 6,
        "n_groups": 2,
        "group_effects_fingerprint_sha256": "c" * 64,
        "input_fingerprint_sha256": "d" * 64,
    }

    return _seal(
        correlated_slope,
        model,
    )


# =====================================================================
# HIERARCHICAL LOCATION-SCALE
# =====================================================================


@pytest.mark.parametrize(
    "values",
    [
        ("",),
        (" ",),
        (1,),
        ("x", "x"),
        ("Intercept",),
    ],
)
def test_hierarchical_predictor_name_guards(values):
    with pytest.raises(ValueError):
        hierarchical._canonical_predictor_names(
            values,
            "predictors",
        )


def test_hierarchical_predictor_names_strip():
    assert hierarchical._canonical_predictor_names(
        (" x ", "z"),
        "predictors",
    ) == ("x", "z")


def test_hierarchical_missing_columns_guard():
    with pytest.raises(SchemaError):
        hierarchical._require_columns(
            pd.DataFrame({"x": [1]}),
            ("x", "y"),
        )


def test_hierarchical_numeric_design_nonfinite():
    frame = pd.DataFrame(
        {
            "x": [1.0, np.nan],
        }
    )

    with pytest.raises(SchemaError):
        hierarchical._numeric_design(
            frame,
            ("x",),
            equation="Location",
        )


def test_hierarchical_numeric_design_rank_guard():
    frame = pd.DataFrame(
        {
            "x": [1.0, 1.0],
        }
    )

    with pytest.raises(SchemaError):
        hierarchical._numeric_design(
            frame,
            ("x",),
            equation="Location",
        )

    design, terms = hierarchical._numeric_design(
        frame,
        ("x",),
        equation="Location",
        check_rank=False,
    )

    assert design.shape == (2, 2)
    assert terms == ("Intercept", "x")


def _hierarchical_spec():
    return hierarchical.HierarchicalLocationScaleSpec(
        outcome_col="y",
        group_col="g",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=3,
        min_group_size=2,
    )


def test_hierarchical_prepare_type_guard():
    with pytest.raises(TypeError):
        hierarchical._prepare_model(
            object(),
            _hierarchical_spec(),
        )


def test_hierarchical_prepare_empty_guard():
    with pytest.raises(SchemaError):
        hierarchical._prepare_model(
            pd.DataFrame(),
            _hierarchical_spec(),
        )


def test_hierarchical_prepare_missing_group_guard():
    frame = pd.DataFrame(
        {
            "y": [1.0, 2.0, 3.0, 4.0],
            "g": ["a", "a", None, "b"],
            "x": [0.0, 1.0, 0.0, 1.0],
        }
    )

    with pytest.raises(SchemaError):
        hierarchical._prepare_model(
            frame,
            _hierarchical_spec(),
        )


def test_hierarchical_prepare_nonfinite_outcome_guard():
    frame = pd.DataFrame(
        {
            "y": [1.0, np.nan, 3.0, 4.0],
            "g": ["a", "a", "b", "b"],
            "x": [0.0, 1.0, 0.0, 1.0],
        }
    )

    with pytest.raises(SchemaError):
        hierarchical._prepare_model(
            frame,
            _hierarchical_spec(),
        )


def test_hierarchical_prepare_one_group_guard():
    frame = pd.DataFrame(
        {
            "y": [1.0, 2.0],
            "g": ["a", "a"],
            "x": [0.0, 1.0],
        }
    )

    with pytest.raises(SchemaError):
        hierarchical._prepare_model(
            frame,
            _hierarchical_spec(),
        )


def test_hierarchical_prepare_min_group_guard():
    frame = pd.DataFrame(
        {
            "y": [1.0, 2.0, 3.0],
            "g": ["a", "a", "b"],
            "x": [0.0, 1.0, 0.5],
        }
    )

    with pytest.raises(SchemaError):
        hierarchical._prepare_model(
            frame,
            _hierarchical_spec(),
        )


@pytest.mark.parametrize(
    ("value", "upper", "expected"),
    [
        (np.nan, 10.0, False),
        (0.0, 10.0, False),
        (-1.0, 10.0, False),
        (1.0, 10.0, False),
        (
            hierarchical._MIN_RANDOM_EFFECT_SD,
            10.0,
            True,
        ),
        (
            hierarchical._MAX_LOCATION_RANDOM_EFFECT_SD,
            hierarchical._MAX_LOCATION_RANDOM_EFFECT_SD,
            True,
        ),
    ],
)
def test_hierarchical_sd_boundary_helper(
    value,
    upper,
    expected,
):
    assert (
        hierarchical._random_effect_sd_at_numerical_boundary(
            value,
            upper=upper,
        )
        == expected
    )


def test_hierarchical_sd_boundary_union():
    assert not hierarchical._random_effect_sd_boundary_reached(
        0.5,
        0.2,
    )

    assert hierarchical._random_effect_sd_boundary_reached(
        hierarchical._MIN_RANDOM_EFFECT_SD,
        0.2,
    )

    assert hierarchical._random_effect_sd_boundary_reached(
        0.5,
        hierarchical._MAX_LOG_SCALE_RANDOM_EFFECT_SD,
    )


def test_hierarchical_group_integrand_extreme_scale_path():
    value, gradient, hessian = hierarchical._group_log_integrand(
        np.array([0.0, 30.0]),
        np.array([1.0, 2.0]),
        np.ones((2, 1)),
        np.ones((2, 1)),
        np.array([0.0]),
        np.array([0.0]),
        0.5,
        0.2,
    )

    assert value == -np.inf
    assert np.array_equal(
        gradient,
        np.zeros(2),
    )
    assert np.array_equal(
        hessian,
        np.eye(2),
    )


def test_hierarchical_certificate_baseline():
    hierarchical.validate_hierarchical_location_scale_certificate(_hierarchical_certificate())


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema",), "wrong"),
        (
            (
                "model",
                "group_effects_fingerprint_sha256",
            ),
            "bad",
        ),
        (
            (
                "model",
                "input_fingerprint_sha256",
            ),
            "bad",
        ),
        (
            (
                "model",
                "tau_location",
            ),
            0.0,
        ),
        (
            (
                "model",
                "tau_log_scale",
            ),
            0.0,
        ),
        (
            (
                "model",
                "n_obs",
            ),
            True,
        ),
        (
            (
                "model",
                "n_groups",
            ),
            True,
        ),
        (
            (
                "model",
                "n_groups",
            ),
            1,
        ),
    ],
)
def test_hierarchical_certificate_guards(
    path,
    value,
):
    certificate = _hierarchical_certificate()

    cursor = certificate

    for key in path[:-1]:
        cursor = cursor[key]

    cursor[path[-1]] = value

    _resign(
        certificate,
        model_changed=path[0] == "model",
    )

    with pytest.raises(SchemaError):
        hierarchical.validate_hierarchical_location_scale_certificate(certificate)


def test_hierarchical_certificate_noncanonical_spec():
    certificate = _hierarchical_certificate()

    certificate["model"]["spec"]["outcome_col"] = " y "

    _resign(certificate)

    with pytest.raises(SchemaError):
        hierarchical.validate_hierarchical_location_scale_certificate(certificate)


def test_hierarchical_certificate_location_terms():
    certificate = _hierarchical_certificate()

    certificate["model"]["location_fixed_effects"] = {
        "Intercept": 0.1,
    }

    _resign(certificate)

    with pytest.raises(SchemaError):
        hierarchical.validate_hierarchical_location_scale_certificate(certificate)


def test_hierarchical_certificate_scale_terms():
    certificate = _hierarchical_certificate()

    certificate["model"]["scale_fixed_effects"] = {
        "Intercept": -0.2,
    }

    _resign(certificate)

    with pytest.raises(SchemaError):
        hierarchical.validate_hierarchical_location_scale_certificate(certificate)


def test_hierarchical_certificate_group_size_contract():
    certificate = _hierarchical_certificate()

    certificate["model"]["n_obs"] = 3

    _resign(certificate)

    with pytest.raises(SchemaError):
        hierarchical.validate_hierarchical_location_scale_certificate(certificate)


# =====================================================================
# INDEPENDENT RANDOM-SLOPE SCALE HELPERS
# =====================================================================


@pytest.mark.parametrize(
    "values",
    [
        ("",),
        ("x", "x"),
        ("Intercept",),
    ],
)
def test_random_slope_predictor_name_guards(values):
    with pytest.raises(ValueError):
        random_slope._canonical_predictor_names(
            values,
            "predictors",
        )


def _random_slope_spec():
    return random_slope.LocationRandomSlopeScaleSpec(
        outcome_col="y",
        group_col="g",
        random_slope_predictor="x",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=3,
        min_group_size=3,
    )


def test_random_slope_prepare_rank_deficient_group():
    frame = pd.DataFrame(
        {
            "y": [
                1.0,
                2.0,
                3.0,
                4.0,
                5.0,
                6.0,
            ],
            "g": [
                "a",
                "a",
                "a",
                "b",
                "b",
                "b",
            ],
            "x": [
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                2.0,
            ],
        }
    )

    with pytest.raises(
        SchemaError,
        match="rank 2",
    ):
        random_slope._prepare_model(
            frame,
            _random_slope_spec(),
        )


def test_random_slope_group_integrand_extreme_scale():
    value, gradient, hessian = random_slope._group_log_integrand(
        np.array([0.0, 0.0, 30.0]),
        np.array([1.0, 2.0]),
        np.ones((2, 1)),
        np.ones((2, 1)),
        np.array([0.0, 1.0]),
        np.array([0.0]),
        np.array([0.0]),
        0.5,
        0.3,
        0.2,
    )

    assert value == -np.inf
    assert np.array_equal(
        gradient,
        np.zeros(3),
    )
    assert np.array_equal(
        hessian,
        np.eye(3),
    )


@pytest.mark.parametrize(
    ("value", "upper", "expected"),
    [
        (np.nan, 100.0, False),
        (0.0, 100.0, False),
        (1.0, 100.0, False),
        (
            random_slope._MIN_RANDOM_EFFECT_SD,
            100.0,
            True,
        ),
        (
            random_slope._MAX_LOCATION_RANDOM_EFFECT_SD,
            random_slope._MAX_LOCATION_RANDOM_EFFECT_SD,
            True,
        ),
    ],
)
def test_random_slope_sd_boundary_helper(
    value,
    upper,
    expected,
):
    assert (
        random_slope._random_effect_sd_at_numerical_boundary(
            value,
            upper=upper,
        )
        == expected
    )


def test_random_slope_boundary_union():
    assert not random_slope._random_effect_sd_boundary_reached(
        0.5,
        0.3,
        0.2,
    )

    assert random_slope._random_effect_sd_boundary_reached(
        random_slope._MIN_RANDOM_EFFECT_SD,
        0.3,
        0.2,
    )

    assert random_slope._random_effect_sd_boundary_reached(
        0.5,
        random_slope._MAX_LOCATION_RANDOM_EFFECT_SD,
        0.2,
    )

    assert random_slope._random_effect_sd_boundary_reached(
        0.5,
        0.3,
        random_slope._MAX_LOG_SCALE_RANDOM_EFFECT_SD,
    )


# =====================================================================
# CORRELATED RANDOM-SLOPE SCALE
# =====================================================================


@pytest.mark.parametrize(
    ("tau_intercept", "tau_slope", "rho"),
    [
        (0.0, 0.3, 0.0),
        (0.5, 0.0, 0.0),
        (np.nan, 0.3, 0.0),
        (0.5, np.nan, 0.0),
        (0.5, 0.3, 1.0),
        (0.5, 0.3, -1.0),
    ],
)
def test_correlated_slope_latent_parameterization_guards(
    tau_intercept,
    tau_slope,
    rho,
):
    with pytest.raises(ValueError):
        correlated_slope._latent_location_parameterization(
            tau_intercept,
            tau_slope,
            rho,
        )


def test_correlated_slope_latent_parameterization_baseline():
    latent_tau, delta = correlated_slope._latent_location_parameterization(
        0.5,
        0.25,
        0.4,
    )

    assert latent_tau > 0.0
    assert np.isfinite(delta)


@pytest.mark.parametrize(
    ("rho", "expected"),
    [
        (0.0, False),
        (np.nan, True),
        (
            correlated_slope._MAX_ABS_CERTIFIABLE_RHO,
            True,
        ),
        (
            -correlated_slope._MAX_ABS_CERTIFIABLE_RHO,
            True,
        ),
    ],
)
def test_correlated_slope_correlation_boundary(
    rho,
    expected,
):
    assert correlated_slope._correlation_at_numerical_boundary(rho) is expected


def test_correlated_slope_latent_boundary_helper():
    assert not correlated_slope._latent_intercept_boundary_reached(
        0.5,
        0.3,
        0.2,
    )

    assert correlated_slope._latent_intercept_boundary_reached(
        0.5,
        0.3,
        1.0,
    )


def test_correlated_slope_effective_values():
    effective, latent_tau, delta = correlated_slope._effective_slope_values(
        np.array([0.0, 1.0]),
        0.5,
        0.3,
        0.2,
    )

    assert effective.shape == (2,)
    assert latent_tau > 0.0
    assert np.isfinite(delta)


def test_correlated_slope_effective_values_nonfinite():
    with pytest.raises(ValueError):
        correlated_slope._effective_slope_values(
            np.array([0.0, np.inf]),
            0.5,
            0.3,
            0.2,
        )


def _objective_prepared():
    return SimpleNamespace(
        y=np.array([1.0, 1.5]),
        location_design=np.ones((2, 1)),
        scale_design=np.ones((2, 1)),
        slope_values=np.array([0.0, 1.0]),
        group_rows=(
            np.array([0]),
            np.array([1]),
        ),
    )


def test_correlated_slope_objective_nonfinite_theta():
    objective = correlated_slope._objective_factory(
        _objective_prepared(),
        np.array([0.0]),
        np.array([0.0]),
    )

    theta = np.zeros(6)
    theta[0] = np.nan

    assert objective(theta) == 1e100


def test_correlated_slope_objective_invalid_sd():
    objective = correlated_slope._objective_factory(
        _objective_prepared(),
        np.array([0.0]),
        np.array([0.0]),
    )

    theta = np.zeros(6)
    theta[-4] = -1000.0

    assert objective(theta) == 1e100


def test_correlated_slope_objective_effective_failure(
    monkeypatch,
):
    objective = correlated_slope._objective_factory(
        _objective_prepared(),
        np.array([0.0]),
        np.array([0.0]),
    )

    def fail(*args, **kwargs):
        raise ValueError("forced")

    monkeypatch.setattr(
        correlated_slope,
        "_effective_slope_values",
        fail,
    )

    assert objective(np.zeros(6)) == 1e100


def test_correlated_slope_objective_bad_group_likelihood(
    monkeypatch,
):
    objective = correlated_slope._objective_factory(
        _objective_prepared(),
        np.array([0.0]),
        np.array([0.0]),
    )

    monkeypatch.setattr(
        correlated_slope,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty((0, 3)),
            np.empty(0),
            np.zeros(3),
        ),
    )

    assert objective(np.zeros(6)) == 1e100


def test_correlated_slope_certificate_baseline():
    correlated_slope.validate_correlated_location_random_slope_scale_certificate(
        _correlated_slope_certificate()
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "rho_location_intercept_slope",
            correlated_slope._MAX_ABS_CERTIFIABLE_RHO,
        ),
        (
            "tau_location_intercept",
            0.0,
        ),
        (
            "tau_location_slope",
            0.0,
        ),
        (
            "tau_log_scale",
            0.0,
        ),
        (
            "n_obs",
            True,
        ),
        (
            "n_groups",
            True,
        ),
        (
            "n_groups",
            1,
        ),
    ],
)
def test_correlated_slope_certificate_guards(
    field,
    value,
):
    certificate = _correlated_slope_certificate()

    certificate["model"][field] = value

    _resign(certificate)

    with pytest.raises(SchemaError):
        correlated_slope.validate_correlated_location_random_slope_scale_certificate(certificate)


def test_correlated_slope_certificate_group_size_contract():
    certificate = _correlated_slope_certificate()

    certificate["model"]["n_obs"] = 5

    _resign(certificate)

    with pytest.raises(SchemaError):
        correlated_slope.validate_correlated_location_random_slope_scale_certificate(certificate)


# =====================================================================
# FULL COVARIANCE PURE MATH / GUARD PATHS
# =====================================================================


@pytest.mark.parametrize(
    "coordinates",
    [
        (1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        (np.nan, 0.0, 0.0),
        (0.0, np.inf, 0.0),
    ],
)
def test_full_covariance_coordinate_guards(
    coordinates,
):
    with pytest.raises(ValueError):
        full._correlation_matrix_from_coordinates(*coordinates)


def test_full_covariance_eta_parameterization():
    matrix, r01, r02, r12, partial = full._correlation_matrix_from_etas(
        0.2,
        -0.3,
        0.4,
    )

    assert matrix.shape == (3, 3)
    assert np.isfinite(
        [
            r01,
            r02,
            r12,
            partial,
        ]
    ).all()


@pytest.mark.parametrize(
    "taus",
    [
        (0.0, 0.2, 0.1),
        (-1.0, 0.2, 0.1),
        (np.nan, 0.2, 0.1),
    ],
)
def test_full_covariance_population_sd_guards(
    taus,
):
    with pytest.raises(ValueError):
        full._population_covariance(
            taus[0],
            taus[1],
            taus[2],
            0.1,
            0.1,
            0.1,
        )


def test_full_covariance_population_inverse_failure(
    monkeypatch,
):
    def fail(*args, **kwargs):
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
            0.5,
            0.3,
            0.2,
            0.1,
            0.1,
            0.1,
        )


def test_full_covariance_population_nonfinite_precision(
    monkeypatch,
):
    monkeypatch.setattr(
        full.np.linalg,
        "inv",
        lambda matrix: np.full_like(
            matrix,
            np.inf,
        ),
    )

    with pytest.raises(
        ValueError,
        match="non-finite",
    ):
        full._population_covariance(
            0.5,
            0.3,
            0.2,
            0.1,
            0.1,
            0.1,
        )


@pytest.mark.parametrize(
    "matrix",
    [
        np.eye(2),
        np.array(
            [
                [1.0, np.nan, 0.0],
                [np.nan, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        ),
        np.array(
            [
                [1.0, 0.2, 0.0],
                [0.1, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        ),
        np.array(
            [
                [1.0, 2.0, 0.0],
                [2.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        ),
    ],
)
def test_full_covariance_matrix_guards(matrix):
    with pytest.raises(ValueError):
        full._covariance_parameters_from_matrix(matrix)


def test_full_covariance_decomposition_consistency_guard(
    monkeypatch,
):
    covariance = np.array(
        [
            [1.0, 0.2, 0.1],
            [0.2, 1.0, 0.1],
            [0.1, 0.1, 1.0],
        ]
    )

    original = full._correlation_matrix_from_coordinates

    def changed(r01, r02, partial):
        matrix, r12 = original(
            r01,
            r02,
            partial,
        )
        altered = matrix.copy()
        altered[1, 2] += 0.1
        altered[2, 1] += 0.1
        return altered, r12 + 0.1

    monkeypatch.setattr(
        full,
        "_correlation_matrix_from_coordinates",
        changed,
    )

    with pytest.raises(
        ValueError,
        match="decomposition",
    ):
        full._covariance_parameters_from_matrix(covariance)


@pytest.mark.parametrize(
    "shift",
    [
        True,
        "1",
        None,
    ],
)
def test_full_covariance_shift_type_guard(shift):
    with pytest.raises(TypeError):
        full.transform_full_covariance_for_predictor_shift(
            np.eye(3),
            shift=shift,
        )


def test_full_covariance_shift_finite_guard():
    with pytest.raises(ValueError):
        full.transform_full_covariance_for_predictor_shift(
            np.eye(3),
            shift=np.inf,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, False),
        (np.nan, True),
        (
            full._MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE,
            True,
        ),
        (
            -full._MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE,
            True,
        ),
    ],
)
def test_full_covariance_coordinate_boundary(
    value,
    expected,
):
    assert full._correlation_coordinate_at_numerical_boundary(value) is expected


def test_full_covariance_group_integrand_extreme_scale():
    covariance, precision, logdet, _ = full._population_covariance(
        0.5,
        0.3,
        0.2,
        0.1,
        0.1,
        0.1,
    )

    assert covariance.shape == (3, 3)

    value, gradient, hessian = full._group_log_integrand(
        np.array(
            [
                0.0,
                0.0,
                30.0,
            ]
        ),
        np.array(
            [
                1.0,
                2.0,
            ]
        ),
        np.ones((2, 1)),
        np.ones((2, 1)),
        np.array(
            [
                0.0,
                1.0,
            ]
        ),
        np.array([0.0]),
        np.array([0.0]),
        precision,
        logdet,
    )

    assert value == -np.inf
    assert np.array_equal(
        gradient,
        np.zeros(3),
    )
    assert np.array_equal(
        hessian,
        np.eye(3),
    )


# =====================================================================
# BOOTSTRAP MONTE CARLO CORE — NO REFITTING
# =====================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a" * 64, True),
        ("A" * 64, False),
        ("g" * 64, False),
        ("a" * 63, False),
        (None, False),
    ],
)
def test_mc_sha_guard(
    value,
    expected,
):
    assert mc._is_sha256_hex(value) is expected


@pytest.mark.parametrize(
    "value",
    [
        np.nan,
        np.inf,
        0.5,
        1.0,
    ],
)
def test_mc_spec_guards(value):
    with pytest.raises(ValueError):
        mc.LocationScaleBootstrapMonteCarloSpec(confidence_level=value)


def test_mc_jackknife_requires_three():
    with pytest.raises(SchemaError):
        mc._jackknife_sd_mcse(np.array([1.0, 2.0]))


def test_mc_jackknife_constant_values():
    value = mc._jackknife_sd_mcse(np.ones(5))

    assert value == pytest.approx(0.0)


def test_mc_jackknife_invalid_variance():
    with pytest.raises(SchemaError):
        mc._jackknife_sd_mcse(
            np.array(
                [
                    1.0,
                    np.inf,
                    3.0,
                ]
            )
        )


@pytest.mark.parametrize(
    "values",
    [
        np.array([]),
        np.array([1.0, np.nan]),
    ],
)
def test_mc_order_band_replicate_guards(values):
    with pytest.raises(SchemaError):
        mc._order_statistic_quantile_band(
            values,
            probability=0.5,
            confidence_level=0.95,
        )


@pytest.mark.parametrize(
    "probability",
    [
        0.0,
        1.0,
        -0.1,
    ],
)
def test_mc_order_band_probability_guard(
    probability,
):
    with pytest.raises(ValueError):
        mc._order_statistic_quantile_band(
            np.arange(
                1.0,
                11.0,
            ),
            probability=probability,
            confidence_level=0.95,
        )


def test_mc_order_band_coverage_guard(
    monkeypatch,
):
    monkeypatch.setattr(
        mc.binom,
        "cdf",
        lambda *args, **kwargs: 1.0,
    )

    monkeypatch.setattr(
        mc.binom,
        "sf",
        lambda *args, **kwargs: 1.0,
    )

    with pytest.raises(SchemaError):
        mc._order_statistic_quantile_band(
            np.arange(
                1.0,
                21.0,
            ),
            probability=0.5,
            confidence_level=0.95,
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        np.nan,
        np.inf,
        "1",
    ],
)
def test_mc_optional_float_guard(value):
    with pytest.raises(SchemaError):
        mc._canonical_optional_float(
            value,
            context="demo",
        )


def test_mc_optional_float_none_and_number():
    assert (
        mc._canonical_optional_float(
            None,
            context="demo",
        )
        is None
    )

    assert (
        mc._canonical_optional_float(
            1,
            context="demo",
        )
        == 1.0
    )


@pytest.fixture(scope="module")
def mc_result():
    return mc.assess_location_scale_bootstrap_monte_carlo(_synthetic_bootstrap(20))


@pytest.fixture(scope="module")
def mc_certificate(mc_result):
    return mc.build_location_scale_bootstrap_monte_carlo_certificate(mc_result)


def _resign_mc(certificate):
    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_mc_certificate_baseline(mc_certificate):
    mc.validate_location_scale_bootstrap_monte_carlo_certificate(copy.deepcopy(mc_certificate))


def test_mc_diagnostics_container_guard(
    mc_certificate,
):
    diagnostics = copy.deepcopy(mc_certificate["diagnostics"])

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            None,
            n_simulations=20,
            parameter_ids=tuple(row["parameter_id"] for row in diagnostics),
        )


def test_mc_diagnostic_schema_guard(
    mc_certificate,
):
    rows = copy.deepcopy(mc_certificate["diagnostics"])

    rows[0]["extra"] = True

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            rows,
            n_simulations=20,
            parameter_ids=tuple(row["parameter_id"] for row in mc_certificate["diagnostics"]),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("parameter_id", "wrong"),
        ("component", ""),
        ("term", ""),
        ("n_simulations", 19),
        ("bootstrap_mean", True),
        ("bootstrap_mean", np.nan),
        ("bootstrap_se", np.inf),
        (
            "interval_lower_mc_rank_lower",
            True,
        ),
        (
            "interval_lower_mc_rank_lower",
            -1,
        ),
        (
            "interval_upper_mc_rank_upper",
            999,
        ),
        (
            "interval_lower_mc_band_lower",
            True,
        ),
    ],
)
def test_mc_diagnostic_row_guards(
    mc_certificate,
    field,
    value,
):
    rows = copy.deepcopy(mc_certificate["diagnostics"])

    rows[0][field] = value

    parameter_ids = tuple(row["parameter_id"] for row in mc_certificate["diagnostics"])

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            rows,
            n_simulations=20,
            parameter_ids=parameter_ids,
        )


def test_mc_source_json_guard(mc_result):
    attacked = replace(
        mc_result,
        source_bootstrap_certificate_json="{",
    )

    with pytest.raises(SchemaError):
        mc.build_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_mc_source_lineage_guard(mc_result):
    attacked = replace(
        mc_result,
        source_bootstrap_fingerprint_sha256="0" * 64,
    )

    with pytest.raises(SchemaError):
        mc.build_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_mc_result_diagnostics_fingerprint_guard(
    mc_result,
):
    attacked = replace(
        mc_result,
        diagnostics_fingerprint_sha256="0" * 64,
    )

    with pytest.raises(SchemaError):
        mc.build_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_mc_result_identity_guard(mc_result):
    attacked = replace(
        mc_result,
        model_family="wrong",
    )

    with pytest.raises(SchemaError):
        mc.build_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_mc_result_assessment_fingerprint_shape(
    mc_result,
):
    attacked = replace(
        mc_result,
        assessment_fingerprint_sha256="bad",
    )

    with pytest.raises(SchemaError):
        mc.build_location_scale_bootstrap_monte_carlo_certificate(attacked)


def test_mc_certificate_requires_dictionary():
    with pytest.raises(TypeError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate([])


def test_mc_certificate_schema_guard(
    mc_certificate,
):
    certificate = copy.deepcopy(mc_certificate)

    certificate["schema"] = "wrong"

    _resign_mc(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_fingerprint_guard(
    mc_certificate,
):
    certificate = copy.deepcopy(mc_certificate)

    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_claim_guard(
    mc_certificate,
):
    certificate = copy.deepcopy(mc_certificate)

    certificate["claim_boundary"]["automatic_stability_threshold_applied"] = True

    _resign_mc(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_assessment_schema_guard(
    mc_certificate,
):
    certificate = copy.deepcopy(mc_certificate)

    certificate["assessment"]["schema"] = "wrong"

    _resign_mc(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_assessment_spec_guard(
    mc_certificate,
):
    certificate = copy.deepcopy(mc_certificate)

    certificate["assessment"]["spec"]["confidence_level"] = 1.0

    _resign_mc(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_diagnostic_consistency_guard(
    mc_certificate,
):
    certificate = copy.deepcopy(mc_certificate)

    certificate["diagnostics"][0]["bootstrap_mean"] += 0.1

    _resign_mc(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_assessment_identity_guard(
    mc_certificate,
):
    certificate = copy.deepcopy(mc_certificate)

    certificate["assessment"]["model_family"] = "wrong"

    _resign_mc(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_assessment_fingerprint_guard(
    mc_certificate,
):
    certificate = copy.deepcopy(mc_certificate)

    certificate["assessment_fingerprint_sha256"] = "0" * 64

    _resign_mc(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_freeze_overwrite(
    tmp_path,
    mc_result,
):
    target = tmp_path / "mc.json"

    assert (
        mc.freeze_location_scale_bootstrap_monte_carlo_certificate(
            mc_result,
            target,
        )
        == target
    )

    with pytest.raises(FileExistsError):
        mc.freeze_location_scale_bootstrap_monte_carlo_certificate(
            mc_result,
            target,
        )

    assert (
        mc.freeze_location_scale_bootstrap_monte_carlo_certificate(
            mc_result,
            target,
            overwrite=True,
        )
        == target
    )
