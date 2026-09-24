from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

import gazeforge.correlated_location_scale as corr
import gazeforge.location_random_slope_scale as slope
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError

# ============================================================
# FIXTURES — NO FITTING
# ============================================================


def _corr_spec(**changes):
    values = {
        "outcome_col": "y",
        "group_col": "g",
        "location_predictors": ("x",),
        "scale_predictors": ("z",),
        "quadrature_points": 3,
        "min_group_size": 2,
        "max_iter": 10,
        "tolerance": 1e-7,
    }
    values.update(changes)
    return corr.CorrelatedLocationScaleSpec(**values)


def _corr_data():
    return pd.DataFrame(
        {
            "y": [1.0, 1.4, 2.0, 2.4],
            "g": ["A", "A", "B", "B"],
            "x": [0.0, 1.0, 0.0, 1.0],
            "z": [0.0, 1.0, 0.0, 1.0],
        }
    )


def _corr_result():
    spec = _corr_spec()

    group_effects = pd.DataFrame(
        {
            "g": ["A", "B"],
            "n_obs": [2, 2],
            "location_random_mean": [0.1, -0.1],
            "log_scale_random_mean": [0.05, -0.05],
        }
    )

    location_coef = np.array(
        [1.0, 0.5],
        dtype=float,
    )

    scale_coef = np.array(
        [-0.2, 0.1],
        dtype=float,
    )

    identity = corr._model_identity_payload(
        spec=spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept", "z"),
        location_coef=location_coef,
        scale_coef=scale_coef,
        tau_location=0.4,
        tau_scale=0.3,
        rho=0.2,
        log_likelihood=-10.0,
        n_obs=4,
        n_groups=2,
        group_effects=group_effects,
        input_fingerprint="a" * 64,
    )

    return corr.CorrelatedLocationScaleResult(
        spec=spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept", "z"),
        location_coef=location_coef,
        scale_coef=scale_coef,
        tau_location=0.4,
        tau_scale=0.3,
        rho_location_scale=0.2,
        log_likelihood=-10.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="synthetic validated fixture",
        optimizer_iterations=3,
        n_obs=4,
        n_groups=2,
        group_effects=group_effects,
        input_fingerprint_sha256="a" * 64,
        model_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def _slope_spec(**changes):
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
    return slope.LocationRandomSlopeScaleSpec(**values)


def _slope_data():
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


def _slope_result():
    spec = _slope_spec()

    group_effects = pd.DataFrame(
        {
            "g": ["A", "B"],
            "n_obs": [3, 3],
            "location_intercept_random_mean": [
                0.1,
                -0.1,
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

    location_coef = np.array(
        [1.0, 0.5],
        dtype=float,
    )

    scale_coef = np.array(
        [-0.2, 0.1],
        dtype=float,
    )

    identity = slope._model_identity_payload(
        spec=spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept", "z"),
        location_coef=location_coef,
        scale_coef=scale_coef,
        tau_intercept=0.4,
        tau_slope=0.2,
        tau_scale=0.3,
        log_likelihood=-12.0,
        n_obs=6,
        n_groups=2,
        group_effects=group_effects,
        input_fingerprint="b" * 64,
    )

    return slope.LocationRandomSlopeScaleResult(
        spec=spec,
        location_terms=("Intercept", "x"),
        scale_terms=("Intercept", "z"),
        location_coef=location_coef,
        scale_coef=scale_coef,
        tau_location_intercept=0.4,
        tau_location_slope=0.2,
        tau_scale=0.3,
        log_likelihood=-12.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="synthetic validated fixture",
        optimizer_iterations=3,
        n_obs=6,
        n_groups=2,
        group_effects=group_effects,
        input_fingerprint_sha256="b" * 64,
        model_fingerprint_sha256=benchmark_fingerprint(identity),
    )


def _resign_corr(certificate):
    certificate["model_fingerprint_sha256"] = benchmark_fingerprint(certificate["model"])

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def _resign_slope(certificate):
    certificate["model_fingerprint_sha256"] = benchmark_fingerprint(certificate["model"])

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


# ============================================================
# CORRELATED SPEC CONTRACTS
# ============================================================


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("outcome_col", ""),
        ("outcome_col", "   "),
        ("outcome_col", None),
        ("group_col", ""),
        ("group_col", None),
    ],
)
def test_corr_spec_requires_names(
    field,
    value,
):
    with pytest.raises(
        ValueError,
        match="non-empty string",
    ):
        _corr_spec(**{field: value})


def test_corr_spec_strips_names():
    spec = _corr_spec(
        outcome_col=" y ",
        group_col=" g ",
    )

    assert spec.outcome_col == "y"
    assert spec.group_col == "g"


def test_corr_spec_distinct_outcome_group():
    with pytest.raises(
        ValueError,
        match="distinct",
    ):
        _corr_spec(
            outcome_col="y",
            group_col="y",
        )


@pytest.mark.parametrize(
    "values",
    [
        ("",),
        (" ",),
        (None,),
    ],
)
def test_corr_predictors_nonempty(values):
    with pytest.raises(
        ValueError,
        match="non-empty strings",
    ):
        corr._canonical_predictor_names(
            values,
            "fixture",
        )


def test_corr_predictors_strip():
    assert corr._canonical_predictor_names(
        (" x ", " z "),
        "fixture",
    ) == ("x", "z")


def test_corr_predictors_duplicate():
    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        corr._canonical_predictor_names(
            ("x", "x"),
            "fixture",
        )


def test_corr_predictors_reserved_intercept():
    with pytest.raises(
        ValueError,
        match="reserved",
    ):
        corr._canonical_predictor_names(
            ("Intercept",),
            "fixture",
        )


def test_corr_predictor_collision():
    with pytest.raises(
        ValueError,
        match="cannot also be model predictors",
    ):
        _corr_spec(
            location_predictors=("y",),
        )


@pytest.mark.parametrize(
    "q",
    [
        1,
        2,
        4,
        16,
    ],
)
def test_corr_quadrature_contract(q):
    with pytest.raises(
        ValueError,
        match="odd integer",
    ):
        _corr_spec(quadrature_points=q)


def test_corr_min_group_size():
    with pytest.raises(
        ValueError,
        match="at least 2",
    ):
        _corr_spec(min_group_size=1)


def test_corr_max_iter():
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        _corr_spec(max_iter=0)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        np.nan,
        np.inf,
    ],
)
def test_corr_tolerance(value):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        _corr_spec(tolerance=value)


def test_corr_spec_to_dict():
    assert _corr_spec().to_dict()["quadrature_points"] == 3


# ============================================================
# CORRELATED DESIGN PREPARATION
# ============================================================


def test_corr_require_columns():
    with pytest.raises(
        SchemaError,
        match="Missing columns",
    ):
        corr._require_columns(
            pd.DataFrame({"a": [1]}),
            ("a", "b"),
        )


def test_corr_numeric_design_valid():
    design, terms = corr._numeric_design(
        pd.DataFrame(
            {
                "x": [
                    0.0,
                    1.0,
                    2.0,
                ]
            }
        ),
        ("x",),
        equation="Location",
    )

    assert design.shape == (3, 2)
    assert terms == (
        "Intercept",
        "x",
    )


def test_corr_numeric_design_nonfinite():
    with pytest.raises(
        SchemaError,
        match="finite and numeric",
    ):
        corr._numeric_design(
            pd.DataFrame(
                {
                    "x": [
                        0.0,
                        np.nan,
                    ]
                }
            ),
            ("x",),
            equation="Location",
        )


def test_corr_numeric_design_rank_deficient():
    with pytest.raises(
        SchemaError,
        match="rank deficient",
    ):
        corr._numeric_design(
            pd.DataFrame(
                {
                    "x": [
                        1.0,
                        1.0,
                        1.0,
                    ]
                }
            ),
            ("x",),
            equation="Location",
        )


def test_corr_numeric_design_skip_rank():
    design, _ = corr._numeric_design(
        pd.DataFrame(
            {
                "x": [
                    1.0,
                    1.0,
                ]
            }
        ),
        ("x",),
        equation="Location",
        check_rank=False,
    )

    assert design.shape == (2, 2)


def test_corr_prepare_type():
    with pytest.raises(
        TypeError,
        match="pandas DataFrame",
    ):
        corr._prepare_model(
            [],
            _corr_spec(),
        )


def test_corr_prepare_empty():
    with pytest.raises(
        SchemaError,
        match="at least one row",
    ):
        corr._prepare_model(
            pd.DataFrame(),
            _corr_spec(),
        )


def test_corr_prepare_missing_column():
    with pytest.raises(
        SchemaError,
        match="Missing columns",
    ):
        corr._prepare_model(
            _corr_data().drop(columns=["z"]),
            _corr_spec(),
        )


def test_corr_prepare_missing_group():
    data = _corr_data()
    data.loc[0, "g"] = None

    with pytest.raises(
        SchemaError,
        match="group_col must be complete",
    ):
        corr._prepare_model(
            data,
            _corr_spec(),
        )


def test_corr_prepare_bad_outcome():
    data = _corr_data()
    data.loc[0, "y"] = np.nan

    with pytest.raises(
        SchemaError,
        match="Outcome values",
    ):
        corr._prepare_model(
            data,
            _corr_spec(),
        )


def test_corr_prepare_one_group():
    data = _corr_data()
    data["g"] = "A"

    with pytest.raises(
        SchemaError,
        match="at least two groups",
    ):
        corr._prepare_model(
            data,
            _corr_spec(),
        )


def test_corr_prepare_small_group():
    data = _corr_data().iloc[[0, 1, 2]].copy()

    with pytest.raises(
        SchemaError,
        match="undersized groups",
    ):
        corr._prepare_model(
            data,
            _corr_spec(min_group_size=2),
        )


def test_corr_prepare_valid():
    prepared = corr._prepare_model(
        _corr_data(),
        _corr_spec(),
    )

    assert prepared.group_levels == (
        "A",
        "B",
    )

    assert prepared.location_terms == (
        "Intercept",
        "x",
    )


def test_corr_initial_parameters_finite():
    prepared = corr._prepare_model(
        _corr_data(),
        _corr_spec(),
    )

    theta = corr._initial_parameters(prepared)

    assert np.isfinite(theta).all()


def test_corr_quadrature_shape():
    nodes, weights = corr._quadrature(_corr_spec())

    assert len(nodes) == 3
    assert len(weights) == 9


def test_corr_unpack():
    beta, gamma, t1, t2, rho = corr._unpack(
        np.array(
            [
                1.0,
                2.0,
                3.0,
                4.0,
                np.log(0.4),
                np.log(0.3),
                0.2,
            ]
        ),
        2,
        2,
    )

    assert beta.tolist() == [
        1.0,
        2.0,
    ]

    assert gamma.tolist() == [
        3.0,
        4.0,
    ]

    assert t1 == pytest.approx(0.4)
    assert t2 == pytest.approx(0.3)
    assert rho == pytest.approx(np.tanh(0.2))


# ============================================================
# CORRELATED NUMERICAL BOUNDARIES
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        np.nan,
        np.inf,
        0.0,
        -1.0,
    ],
)
def test_corr_sd_boundary_invalid_false(
    value,
):
    assert (
        corr._random_effect_sd_at_numerical_boundary(
            value,
            upper=10.0,
        )
        is False
    )


@pytest.mark.parametrize(
    "value",
    [
        corr._MIN_RANDOM_EFFECT_SD,
        corr._MAX_LOG_SCALE_RANDOM_EFFECT_SD,
    ],
)
def test_corr_sd_boundary_true(value):
    upper = (
        corr._MAX_LOG_SCALE_RANDOM_EFFECT_SD
        if value == corr._MAX_LOG_SCALE_RANDOM_EFFECT_SD
        else corr._MAX_LOCATION_RANDOM_EFFECT_SD
    )

    assert corr._random_effect_sd_at_numerical_boundary(
        value,
        upper=upper,
    )


def test_corr_sd_boundary_mid_false():
    assert not (
        corr._random_effect_sd_at_numerical_boundary(
            0.5,
            upper=10.0,
        )
    )


def test_corr_combined_boundary_location():
    assert corr._random_effect_sd_boundary_reached(
        corr._MIN_RANDOM_EFFECT_SD,
        0.3,
    )


def test_corr_combined_boundary_scale():
    assert corr._random_effect_sd_boundary_reached(
        0.4,
        corr._MAX_LOG_SCALE_RANDOM_EFFECT_SD,
    )


def test_corr_combined_boundary_false():
    assert not corr._random_effect_sd_boundary_reached(
        0.4,
        0.3,
    )


def test_corr_precision_valid():
    precision, one_minus = corr._random_effect_precision(
        0.4,
        0.3,
        0.2,
    )

    assert precision.shape == (2, 2)
    assert one_minus == pytest.approx(0.96)


@pytest.mark.parametrize(
    "rho",
    [
        1.0,
        -1.0,
        np.nan,
    ],
)
def test_corr_precision_rejects_singular(
    rho,
):
    with pytest.raises(
        ValueError,
        match="too close",
    ):
        corr._random_effect_precision(
            0.4,
            0.3,
            rho,
        )


def test_corr_integrand_extreme_scale():
    value, gradient, hessian = corr._group_log_integrand(
        np.array([0.0, 30.0]),
        np.array([1.0]),
        np.ones((1, 1)),
        np.ones((1, 1)),
        np.array([1.0]),
        np.array([0.0]),
        0.4,
        0.3,
        0.0,
    )

    assert value == -np.inf
    assert gradient.shape == (2,)
    assert hessian.shape == (2, 2)


def test_corr_integrand_invalid_rho():
    value, _, _ = corr._group_log_integrand(
        np.zeros(2),
        np.array([1.0]),
        np.ones((1, 1)),
        np.ones((1, 1)),
        np.array([1.0]),
        np.array([0.0]),
        0.4,
        0.3,
        1.0,
    )

    assert value == -np.inf


def test_corr_integrand_valid():
    value, gradient, hessian = corr._group_log_integrand(
        np.zeros(2),
        np.array([1.0, 1.2]),
        np.ones((2, 1)),
        np.ones((2, 1)),
        np.array([1.0]),
        np.array([0.0]),
        0.4,
        0.3,
        0.2,
    )

    assert np.isfinite(value)
    assert np.isfinite(gradient).all()
    assert np.isfinite(hessian).all()


def test_corr_objective_nonfinite_theta():
    prepared = corr._prepare_model(
        _corr_data(),
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
        _corr_data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    objective = corr._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = corr._initial_parameters(prepared)

    theta[-3] = np.log(corr._MIN_RANDOM_EFFECT_SD / 10)

    assert objective(theta) == 1e100


def test_corr_objective_quadrature_failure(
    monkeypatch,
):
    prepared = corr._prepare_model(
        _corr_data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    monkeypatch.setattr(
        corr,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty((0, 2)),
            np.empty(0),
            np.zeros(2),
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
        _corr_data(),
        _corr_spec(),
    )

    nodes, weights = corr._quadrature(_corr_spec())

    monkeypatch.setattr(
        corr,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -2.0,
            np.zeros((1, 2)),
            np.ones(1),
            np.zeros(2),
        ),
    )

    objective = corr._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(corr._initial_parameters(prepared)) == pytest.approx(4.0)


# ============================================================
# CORRELATED SYNTHETIC RESULT + PREDICTION
# ============================================================


def test_corr_result_fixed_effects():
    table = _corr_result().fixed_effects()

    assert len(table) == 4
    assert set(table["equation"]) == {
        "location",
        "log_scale",
    }


def test_corr_result_correlation():
    assert _corr_result().random_effect_correlation() == pytest.approx(0.2)


def test_corr_prediction_known_group():
    data = pd.DataFrame(
        {
            "g": ["A"],
            "x": [1.0],
            "z": [0.0],
        }
    )

    predicted = corr.predict_correlated_location_scale(
        _corr_result(),
        data,
    )

    assert bool(predicted["group_effect_used"].iloc[0])


def test_corr_prediction_population_only():
    data = pd.DataFrame(
        {
            "g": ["A"],
            "x": [1.0],
            "z": [0.0],
        }
    )

    predicted = corr.predict_correlated_location_scale(
        _corr_result(),
        data,
        include_group_effects=False,
    )

    assert not bool(predicted["group_effect_used"].iloc[0])


def test_corr_prediction_unseen_allowed():
    data = pd.DataFrame(
        {
            "g": ["NEW"],
            "x": [1.0],
            "z": [0.0],
        }
    )

    predicted = corr.predict_correlated_location_scale(
        _corr_result(),
        data,
    )

    assert not bool(predicted["group_effect_used"].iloc[0])


def test_corr_prediction_unseen_rejected():
    data = pd.DataFrame(
        {
            "g": ["NEW"],
            "x": [1.0],
            "z": [0.0],
        }
    )

    with pytest.raises(
        SchemaError,
        match="unseen groups",
    ):
        corr.predict_correlated_location_scale(
            _corr_result(),
            data,
            allow_new_groups=False,
        )


def test_corr_prediction_missing_group():
    data = pd.DataFrame(
        {
            "g": [None],
            "x": [1.0],
            "z": [0.0],
        }
    )

    with pytest.raises(
        SchemaError,
        match="complete",
    ):
        corr.predict_correlated_location_scale(
            _corr_result(),
            data,
        )


def test_corr_prediction_extreme_log_scale():
    result = _corr_result()

    attacked = replace(
        result,
        scale_coef=np.array([30.0, 0.0]),
    )

    identity = corr._current_result_identity(attacked)

    attacked = replace(
        attacked,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        RuntimeError,
        match="numerically supported range",
    ):
        corr.predict_correlated_location_scale(
            attacked,
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [0.0],
                    "z": [0.0],
                }
            ),
        )


def test_corr_diagnostics_bad_outcome():
    data = _corr_data()
    data.loc[0, "y"] = np.nan

    with pytest.raises(
        SchemaError,
        match="finite for diagnostics",
    ):
        corr.correlated_location_scale_diagnostics(
            _corr_result(),
            data,
        )


def test_corr_diagnostics_valid():
    output = corr.correlated_location_scale_diagnostics(
        _corr_result(),
        _corr_data(),
    )

    assert "standardized_residual" in output


# ============================================================
# CORRELATED RESULT IDENTITY + CERTIFICATE
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "g" * 64,
        "a" * 63,
    ],
)
def test_corr_sha_helper_invalid(value):
    assert not corr._is_sha256_hex(value)


def test_corr_sha_helper_valid():
    assert corr._is_sha256_hex("a" * 64)


def test_corr_result_model_identity_guard():
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
    result = _corr_result()

    attacked = replace(
        result,
        input_fingerprint_sha256="bad",
    )

    identity = corr._current_result_identity(attacked)

    attacked = replace(
        attacked,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="input fingerprint",
    ):
        corr._validate_result_identity(attacked)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "tau_location",
            0.0,
        ),
        (
            "tau_scale",
            np.nan,
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


def test_corr_result_sd_boundary_guard():
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


@pytest.mark.parametrize(
    "rho",
    [
        -1.0,
        1.0,
    ],
)
def test_corr_result_rho_range(rho):
    result = replace(
        _corr_result(),
        rho_location_scale=rho,
    )

    identity = corr._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="strictly between",
    ):
        corr._validate_result_identity(result)


def test_corr_result_rho_optimizer_boundary():
    result = replace(
        _corr_result(),
        rho_location_scale=(corr._MAX_ABS_CERTIFIABLE_RHO),
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
        n_obs=3,
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


def test_corr_certificate_valid():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_schema():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["schema"] = "bad"
    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="Unsupported",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_fingerprint():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        SchemaError,
        match="fingerprint mismatch",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_claim_boundary():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["claim_boundary"]["causal_effects_established"] = True

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        SchemaError,
        match="claim boundary",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_model_extra_key():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["extra"] = 1
    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_model_fingerprint():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model_fingerprint_sha256"] = "0" * 64

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        SchemaError,
        match="model fingerprint",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_invalid_spec():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["spec"]["quadrature_points"] = 2

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="invalid model spec",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_location_terms():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["location_fixed_effects"] = {
        "Intercept": 1.0,
    }

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="Location fixed-effect terms",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_scale_terms():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["scale_fixed_effects"] = {
        "Intercept": -0.2,
    }

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="Scale fixed-effect terms",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


@pytest.mark.parametrize(
    "field",
    [
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    ],
)
def test_corr_certificate_sha_fields(
    field,
):
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"][field] = "bad"

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="fingerprint",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_nonfinite_estimate():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["tau_location"] = np.nan

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_nonpositive_sd():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["tau_location"] = 0.0

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="standard deviations must be positive",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_sd_boundary():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["tau_log_scale"] = corr._MAX_LOG_SCALE_RANDOM_EFFECT_SD

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="numerical boundary",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


@pytest.mark.parametrize(
    "rho",
    [
        -1.0,
        1.0,
    ],
)
def test_corr_certificate_rho_range(rho):
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["rho_location_log_scale"] = rho

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="strictly between",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_rho_boundary():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["rho_location_log_scale"] = corr._MAX_ABS_CERTIFIABLE_RHO

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="optimizer boundary",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


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
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"][field] = value

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


def test_corr_certificate_min_group_violation():
    certificate = corr.build_correlated_location_scale_certificate(_corr_result())

    certificate["model"]["n_obs"] = 3

    _resign_corr(certificate)

    with pytest.raises(
        SchemaError,
        match="min_group_size",
    ):
        corr.validate_correlated_location_scale_certificate(certificate)


# ============================================================
# RANDOM-SLOPE SPEC + PREPARATION
# ============================================================


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("outcome_col", ""),
        ("group_col", ""),
        ("random_slope_predictor", ""),
        ("random_slope_predictor", None),
    ],
)
def test_slope_spec_names(
    field,
    value,
):
    with pytest.raises(
        ValueError,
        match="non-empty string",
    ):
        _slope_spec(**{field: value})


@pytest.mark.parametrize(
    ("outcome", "group", "random"),
    [
        ("y", "y", "x"),
        ("y", "g", "y"),
        ("y", "g", "g"),
    ],
)
def test_slope_spec_distinct(
    outcome,
    group,
    random,
):
    with pytest.raises(
        ValueError,
        match="distinct",
    ):
        _slope_spec(
            outcome_col=outcome,
            group_col=group,
            random_slope_predictor=random,
        )


def test_slope_requires_fixed_slope():
    with pytest.raises(
        ValueError,
        match="must also appear",
    ):
        _slope_spec(location_predictors=())


def test_slope_predictor_collision():
    with pytest.raises(
        ValueError,
        match="cannot also be model predictors",
    ):
        _slope_spec(
            scale_predictors=("y",),
        )


@pytest.mark.parametrize(
    "q",
    [
        1,
        2,
        4,
        10,
    ],
)
def test_slope_quadrature(q):
    with pytest.raises(
        ValueError,
        match="odd integer",
    ):
        _slope_spec(quadrature_points=q)


def test_slope_min_group():
    with pytest.raises(
        ValueError,
        match="at least 3",
    ):
        _slope_spec(min_group_size=2)


def test_slope_max_iter():
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        _slope_spec(max_iter=0)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        np.nan,
    ],
)
def test_slope_tolerance(value):
    with pytest.raises(
        ValueError,
        match="finite and positive",
    ):
        _slope_spec(tolerance=value)


def test_slope_require_columns():
    with pytest.raises(
        SchemaError,
        match="Missing columns",
    ):
        slope._require_columns(
            pd.DataFrame({"a": [1]}),
            ("a", "b"),
        )


def test_slope_numeric_design_nonfinite():
    with pytest.raises(
        SchemaError,
        match="finite and numeric",
    ):
        slope._numeric_design(
            pd.DataFrame(
                {
                    "x": [
                        0.0,
                        np.nan,
                    ]
                }
            ),
            ("x",),
            equation="Location",
        )


def test_slope_numeric_design_rank():
    with pytest.raises(
        SchemaError,
        match="rank deficient",
    ):
        slope._numeric_design(
            pd.DataFrame(
                {
                    "x": [
                        1.0,
                        1.0,
                        1.0,
                    ]
                }
            ),
            ("x",),
            equation="Location",
        )


def test_slope_prepare_type():
    with pytest.raises(
        TypeError,
        match="pandas DataFrame",
    ):
        slope._prepare_model(
            [],
            _slope_spec(),
        )


def test_slope_prepare_empty():
    with pytest.raises(
        SchemaError,
        match="at least one row",
    ):
        slope._prepare_model(
            pd.DataFrame(),
            _slope_spec(),
        )


def test_slope_prepare_missing_group():
    data = _slope_data()
    data.loc[0, "g"] = None

    with pytest.raises(
        SchemaError,
        match="group_col must be complete",
    ):
        slope._prepare_model(
            data,
            _slope_spec(),
        )


def test_slope_prepare_bad_outcome():
    data = _slope_data()
    data.loc[0, "y"] = np.nan

    with pytest.raises(
        SchemaError,
        match="Outcome values",
    ):
        slope._prepare_model(
            data,
            _slope_spec(),
        )


def test_slope_prepare_bad_slope():
    data = _slope_data()
    data.loc[0, "x"] = np.nan

    with pytest.raises(
        SchemaError,
        match="finite and numeric",
    ):
        slope._prepare_model(
            data,
            _slope_spec(),
        )


def test_slope_prepare_one_group():
    data = _slope_data()
    data["g"] = "A"

    with pytest.raises(
        SchemaError,
        match="at least two groups",
    ):
        slope._prepare_model(
            data,
            _slope_spec(),
        )


def test_slope_prepare_small_group():
    data = _slope_data().iloc[[0, 1, 2, 3, 4]].copy()

    with pytest.raises(
        SchemaError,
        match="undersized groups",
    ):
        slope._prepare_model(
            data,
            _slope_spec(),
        )


def test_slope_prepare_rank_deficient_group():
    data = _slope_data()

    data.loc[
        data["g"] == "A",
        "x",
    ] = 1.0

    with pytest.raises(
        SchemaError,
        match="rank deficient groups",
    ):
        slope._prepare_model(
            data,
            _slope_spec(),
        )


def test_slope_prepare_valid():
    prepared = slope._prepare_model(
        _slope_data(),
        _slope_spec(),
    )

    assert prepared.group_levels == (
        "A",
        "B",
    )


def test_slope_initial_parameters_finite():
    prepared = slope._prepare_model(
        _slope_data(),
        _slope_spec(),
    )

    assert np.isfinite(slope._initial_parameters(prepared)).all()


def test_slope_quadrature_shape():
    nodes, weights = slope._quadrature(_slope_spec())

    assert len(nodes) == 3
    assert len(weights) == 27


def test_slope_unpack():
    values = slope._unpack(
        np.array(
            [
                1.0,
                2.0,
                3.0,
                4.0,
                np.log(0.4),
                np.log(0.2),
                np.log(0.3),
            ]
        ),
        2,
        2,
    )

    assert values[2:] == pytest.approx(
        (
            0.4,
            0.2,
            0.3,
        )
    )


# ============================================================
# RANDOM-SLOPE NUMERICAL HELPERS
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        np.nan,
        0.0,
        -1.0,
    ],
)
def test_slope_sd_boundary_invalid_false(
    value,
):
    assert not (
        slope._random_effect_sd_at_numerical_boundary(
            value,
            upper=10.0,
        )
    )


def test_slope_boundary_each_component():
    assert slope._random_effect_sd_boundary_reached(
        slope._MIN_RANDOM_EFFECT_SD,
        0.2,
        0.3,
    )

    assert slope._random_effect_sd_boundary_reached(
        0.4,
        slope._MAX_LOCATION_RANDOM_EFFECT_SD,
        0.3,
    )

    assert slope._random_effect_sd_boundary_reached(
        0.4,
        0.2,
        slope._MAX_LOG_SCALE_RANDOM_EFFECT_SD,
    )


def test_slope_boundary_false():
    assert not (
        slope._random_effect_sd_boundary_reached(
            0.4,
            0.2,
            0.3,
        )
    )


def test_slope_node_triples():
    triples = slope._node_triples(np.array([-1.0, 1.0]))

    assert triples.shape == (8, 3)


def test_slope_integrand_extreme():
    value, gradient, hessian = slope._group_log_integrand(
        np.array([0.0, 0.0, 30.0]),
        np.array([1.0]),
        np.ones((1, 1)),
        np.ones((1, 1)),
        np.array([1.0]),
        np.array([1.0]),
        np.array([0.0]),
        0.4,
        0.2,
        0.3,
    )

    assert value == -np.inf
    assert gradient.shape == (3,)
    assert hessian.shape == (3, 3)


def test_slope_integrand_valid():
    value, gradient, hessian = slope._group_log_integrand(
        np.zeros(3),
        np.array([1.0, 1.2]),
        np.ones((2, 1)),
        np.ones((2, 1)),
        np.array([0.0, 1.0]),
        np.array([1.0]),
        np.array([0.0]),
        0.4,
        0.2,
        0.3,
    )

    assert np.isfinite(value)
    assert np.isfinite(gradient).all()
    assert np.isfinite(hessian).all()


def test_slope_objective_nonfinite_theta():
    prepared = slope._prepare_model(
        _slope_data(),
        _slope_spec(),
    )

    nodes, weights = slope._quadrature(_slope_spec())

    objective = slope._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = slope._initial_parameters(prepared)

    theta[0] = np.nan

    assert objective(theta) == 1e100


def test_slope_objective_bad_tau():
    prepared = slope._prepare_model(
        _slope_data(),
        _slope_spec(),
    )

    nodes, weights = slope._quadrature(_slope_spec())

    objective = slope._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = slope._initial_parameters(prepared)

    theta[-1] = np.log(slope._MAX_LOG_SCALE_RANDOM_EFFECT_SD * 2)

    assert objective(theta) == 1e100


def test_slope_objective_quadrature_failure(
    monkeypatch,
):
    prepared = slope._prepare_model(
        _slope_data(),
        _slope_spec(),
    )

    nodes, weights = slope._quadrature(_slope_spec())

    monkeypatch.setattr(
        slope,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty((0, 3)),
            np.empty(0),
            np.zeros(3),
        ),
    )

    objective = slope._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(slope._initial_parameters(prepared)) == 1e100


def test_slope_objective_mock_success(
    monkeypatch,
):
    prepared = slope._prepare_model(
        _slope_data(),
        _slope_spec(),
    )

    nodes, weights = slope._quadrature(_slope_spec())

    monkeypatch.setattr(
        slope,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -2.0,
            np.zeros((1, 3)),
            np.ones(1),
            np.zeros(3),
        ),
    )

    objective = slope._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(slope._initial_parameters(prepared)) == pytest.approx(4.0)


# ============================================================
# RANDOM-SLOPE RESULT + PREDICTION
# ============================================================


def test_slope_fixed_effects():
    table = _slope_result().fixed_effects()

    assert len(table) == 4


def test_slope_prediction_known():
    output = slope.predict_location_random_slope_scale(
        _slope_result(),
        pd.DataFrame(
            {
                "g": ["A"],
                "x": [1.0],
                "z": [0.0],
            }
        ),
    )

    assert bool(output["group_effect_used"].iloc[0])


def test_slope_prediction_unseen_rejected():
    with pytest.raises(
        SchemaError,
        match="unseen groups",
    ):
        slope.predict_location_random_slope_scale(
            _slope_result(),
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [1.0],
                    "z": [0.0],
                }
            ),
            allow_new_groups=False,
        )


def test_slope_prediction_bad_slope():
    with pytest.raises(
        SchemaError,
        match="finite and numeric",
    ):
        slope.predict_location_random_slope_scale(
            _slope_result(),
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [np.nan],
                    "z": [0.0],
                }
            ),
        )


def test_slope_prediction_missing_group():
    with pytest.raises(
        SchemaError,
        match="complete",
    ):
        slope.predict_location_random_slope_scale(
            _slope_result(),
            pd.DataFrame(
                {
                    "g": [None],
                    "x": [1.0],
                    "z": [0.0],
                }
            ),
        )


def test_slope_prediction_extreme_scale():
    result = replace(
        _slope_result(),
        scale_coef=np.array([30.0, 0.0]),
    )

    identity = slope._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        RuntimeError,
        match="numerically supported range",
    ):
        slope.predict_location_random_slope_scale(
            result,
            pd.DataFrame(
                {
                    "g": ["NEW"],
                    "x": [0.0],
                    "z": [0.0],
                }
            ),
        )


def test_slope_diagnostics_bad_outcome():
    data = _slope_data()
    data.loc[0, "y"] = np.nan

    with pytest.raises(
        SchemaError,
        match="finite for diagnostics",
    ):
        slope.location_random_slope_scale_diagnostics(
            _slope_result(),
            data,
        )


def test_slope_diagnostics_valid():
    output = slope.location_random_slope_scale_diagnostics(
        _slope_result(),
        _slope_data(),
    )

    assert "standardized_residual" in output


# ============================================================
# RANDOM-SLOPE IDENTITY + CERTIFICATE
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "g" * 64,
        "a" * 63,
    ],
)
def test_slope_sha_invalid(value):
    assert not slope._is_sha256_hex(value)


def test_slope_sha_valid():
    assert slope._is_sha256_hex("a" * 64)


def test_slope_result_identity():
    with pytest.raises(
        SchemaError,
        match="result identity",
    ):
        slope._validate_result_identity(
            replace(
                _slope_result(),
                model_fingerprint_sha256=("0" * 64),
            )
        )


def test_slope_result_input_fp():
    result = replace(
        _slope_result(),
        input_fingerprint_sha256="bad",
    )

    identity = slope._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="input fingerprint",
    ):
        slope._validate_result_identity(result)


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
def test_slope_result_sd_guard(
    field,
    value,
):
    result = replace(
        _slope_result(),
        **{field: value},
    )

    identity = slope._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="finite and positive",
    ):
        slope._validate_result_identity(result)


def test_slope_result_boundary():
    result = replace(
        _slope_result(),
        tau_scale=(slope._MAX_LOG_SCALE_RANDOM_EFFECT_SD),
    )

    identity = slope._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="artificial numerical boundary",
    ):
        slope._validate_result_identity(result)


def test_slope_result_count_guard():
    result = replace(
        _slope_result(),
        n_obs=5,
    )

    identity = slope._current_result_identity(result)

    result = replace(
        result,
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )

    with pytest.raises(
        SchemaError,
        match="counts are inconsistent",
    ):
        slope._validate_result_identity(result)


def test_slope_certificate_valid():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_schema():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["schema"] = "bad"

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="Unsupported",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_fingerprint():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        SchemaError,
        match="fingerprint mismatch",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_claim():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["claim_boundary"]["causal_effects_established"] = True

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        SchemaError,
        match="claim boundary",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_model_extra():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["extra"] = True

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_model_fingerprint():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model_fingerprint_sha256"] = "0" * 64

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)

    with pytest.raises(
        SchemaError,
        match="model fingerprint",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_invalid_spec():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["spec"]["quadrature_points"] = 2

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="invalid model spec",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_location_terms():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["location_fixed_effects"] = {"Intercept": 1.0}

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="Location fixed-effect terms",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_scale_terms():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["scale_fixed_effects"] = {"Intercept": -0.2}

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="Scale fixed-effect terms",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_independence():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["population_random_effect_correlations"] = "correlated"

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="independence claim",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


@pytest.mark.parametrize(
    "field",
    [
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    ],
)
def test_slope_certificate_sha_fields(
    field,
):
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"][field] = "bad"

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="fingerprint",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_nonfinite():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["tau_location_intercept"] = np.nan

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_nonpositive():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["tau_location_slope"] = 0.0

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="standard deviations must be positive",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_boundary():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["tau_log_scale"] = slope._MAX_LOG_SCALE_RANDOM_EFFECT_SD

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="numerical boundary",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n_obs", True),
        ("n_obs", 0),
        ("n_groups", True),
        ("n_groups", 1),
    ],
)
def test_slope_certificate_counts(
    field,
    value,
):
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"][field] = value

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)


def test_slope_certificate_min_group():
    certificate = slope.build_location_random_slope_scale_certificate(_slope_result())

    certificate["model"]["n_obs"] = 5

    _resign_slope(certificate)

    with pytest.raises(
        SchemaError,
        match="min_group_size",
    ):
        slope.validate_location_random_slope_scale_certificate(certificate)
