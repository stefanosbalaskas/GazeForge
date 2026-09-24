from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.hierarchical_location_scale as hier
import gazeforge.location_scale_residual_calibration as cal
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.provenance import fingerprint_frame

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


# ============================================================
# HIERARCHICAL FIXTURES
# ============================================================


def _hier_spec():
    return hier.HierarchicalLocationScaleSpec(
        outcome_col="y",
        group_col="g",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=3,
        min_group_size=2,
        max_iter=20,
        tolerance=1e-6,
    )


def _hier_data():
    return pd.DataFrame(
        {
            "g": [
                "a",
                "a",
                "b",
                "b",
            ],
            "x": [
                -1.0,
                1.0,
                -0.5,
                0.5,
            ],
            "y": [
                0.2,
                1.2,
                0.4,
                1.0,
            ],
        }
    )


def _hier_result(
    *,
    input_fingerprint=SHA_A,
    tau_location=0.4,
    tau_scale=0.2,
    n_obs=4,
    n_groups=2,
    scale_intercept=-0.2,
):
    spec = _hier_spec()

    group_effects = pd.DataFrame(
        {
            "g": [
                "a",
                "b",
            ],
            "n_obs": [
                2,
                2,
            ],
            "location_random_mode": [
                0.1,
                -0.1,
            ],
            "log_scale_random_mode": [
                0.05,
                -0.05,
            ],
            "location_random_mean": [
                0.08,
                -0.08,
            ],
            "location_random_sd": [
                0.1,
                0.1,
            ],
            "log_scale_random_mean": [
                0.04,
                -0.04,
            ],
            "log_scale_random_sd": [
                0.05,
                0.05,
            ],
            "scale_multiplier_mean": [
                1.04,
                0.96,
            ],
        }
    )

    identity = hier._model_identity_payload(
        spec=spec,
        location_terms=(
            "Intercept",
            "x",
        ),
        scale_terms=(
            "Intercept",
            "x",
        ),
        location_coef=np.asarray(
            [
                0.7,
                0.3,
            ]
        ),
        scale_coef=np.asarray(
            [
                scale_intercept,
                0.05,
            ]
        ),
        tau_location=tau_location,
        tau_scale=tau_scale,
        log_likelihood=-5.0,
        n_obs=n_obs,
        n_groups=n_groups,
        group_effects=group_effects,
        input_fingerprint=input_fingerprint,
    )

    return hier.HierarchicalLocationScaleResult(
        spec=spec,
        location_terms=(
            "Intercept",
            "x",
        ),
        scale_terms=(
            "Intercept",
            "x",
        ),
        location_coef=np.asarray(
            [
                0.7,
                0.3,
            ]
        ),
        scale_coef=np.asarray(
            [
                scale_intercept,
                0.05,
            ]
        ),
        tau_location=tau_location,
        tau_scale=tau_scale,
        log_likelihood=-5.0,
        converged=True,
        optimizer_status=0,
        optimizer_message="converged",
        optimizer_iterations=3,
        n_obs=n_obs,
        n_groups=n_groups,
        group_effects=group_effects,
        input_fingerprint_sha256=(input_fingerprint),
        model_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )


def _resign_hier(
    certificate,
    *,
    model=False,
):
    if model:
        certificate["model_fingerprint_sha256"] = benchmark_fingerprint(certificate["model"])

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


# ============================================================
# HIERARCHICAL SPEC
# ============================================================


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "outcome_col",
            "",
        ),
        (
            "group_col",
            " ",
        ),
    ],
)
def test_hier_spec_required_names(
    field,
    value,
):
    kwargs = {
        "outcome_col": "y",
        "group_col": "g",
    }

    kwargs[field] = value

    with pytest.raises(ValueError):
        hier.HierarchicalLocationScaleSpec(**kwargs)


@pytest.mark.parametrize(
    "predictors",
    [
        ("",),
        (
            "x",
            "x",
        ),
        ("Intercept",),
    ],
)
def test_hier_spec_predictor_names(
    predictors,
):
    with pytest.raises(ValueError):
        hier.HierarchicalLocationScaleSpec(
            "y",
            "g",
            location_predictors=predictors,
        )


@pytest.mark.parametrize(
    "predictors",
    [
        ("y",),
        ("g",),
    ],
)
def test_hier_spec_column_collisions(
    predictors,
):
    with pytest.raises(ValueError):
        hier.HierarchicalLocationScaleSpec(
            "y",
            "g",
            scale_predictors=predictors,
        )


@pytest.mark.parametrize(
    "value",
    [
        1,
        2,
        4,
        16,
    ],
)
def test_hier_spec_quadrature(
    value,
):
    with pytest.raises(ValueError):
        hier.HierarchicalLocationScaleSpec(
            "y",
            "g",
            quadrature_points=value,
        )


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "min_group_size",
            1,
        ),
        (
            "max_iter",
            0,
        ),
        (
            "tolerance",
            0,
        ),
        (
            "tolerance",
            np.nan,
        ),
    ],
)
def test_hier_spec_scalar_guards(
    field,
    value,
):
    kwargs = {
        "outcome_col": "y",
        "group_col": "g",
    }

    kwargs[field] = value

    with pytest.raises(ValueError):
        hier.HierarchicalLocationScaleSpec(**kwargs)


def test_hier_spec_canonicalizes_names():
    spec = hier.HierarchicalLocationScaleSpec(
        " y ",
        " g ",
        location_predictors=(" x ",),
    )

    assert spec.outcome_col == "y"
    assert spec.group_col == "g"

    assert spec.location_predictors == ("x",)


# ============================================================
# HIERARCHICAL PREPARATION
# ============================================================


def test_hier_require_columns():
    with pytest.raises(SchemaError):
        hier._require_columns(
            pd.DataFrame({"x": [1]}),
            (
                "x",
                "y",
            ),
        )


def test_hier_numeric_design_nonfinite():
    data = pd.DataFrame(
        {
            "x": [
                1,
                "bad",
            ]
        }
    )

    with pytest.raises(SchemaError):
        hier._numeric_design(
            data,
            ("x",),
            equation="Location",
        )


def test_hier_numeric_design_rank_guard():
    data = pd.DataFrame(
        {
            "x": [
                1,
                1,
                1,
            ]
        }
    )

    with pytest.raises(SchemaError):
        hier._numeric_design(
            data,
            ("x",),
            equation="Location",
        )


def test_hier_numeric_design_rank_can_be_disabled():
    data = pd.DataFrame(
        {
            "x": [
                1,
                1,
            ]
        }
    )

    design, terms = hier._numeric_design(
        data,
        ("x",),
        equation="Location",
        check_rank=False,
    )

    assert design.shape == (
        2,
        2,
    )

    assert terms == (
        "Intercept",
        "x",
    )


def test_hier_prepare_type():
    with pytest.raises(TypeError):
        hier._prepare_model(
            object(),
            _hier_spec(),
        )


def test_hier_prepare_empty():
    with pytest.raises(SchemaError):
        hier._prepare_model(
            _hier_data().iloc[0:0],
            _hier_spec(),
        )


def test_hier_prepare_missing_column():
    data = _hier_data().drop(columns=["x"])

    with pytest.raises(SchemaError):
        hier._prepare_model(
            data,
            _hier_spec(),
        )


def test_hier_prepare_missing_group():
    data = _hier_data()

    data.loc[
        0,
        "g",
    ] = None

    with pytest.raises(SchemaError):
        hier._prepare_model(
            data,
            _hier_spec(),
        )


def test_hier_prepare_nonfinite_outcome():
    data = _hier_data()

    data.loc[
        0,
        "y",
    ] = np.nan

    with pytest.raises(SchemaError):
        hier._prepare_model(
            data,
            _hier_spec(),
        )


def test_hier_prepare_one_group():
    data = _hier_data()

    data["g"] = "a"

    with pytest.raises(SchemaError):
        hier._prepare_model(
            data,
            _hier_spec(),
        )


def test_hier_prepare_undersized_group():
    data = (
        _hier_data()
        .iloc[
            [
                0,
                1,
                2,
            ]
        ]
        .copy()
    )

    with pytest.raises(SchemaError):
        hier._prepare_model(
            data,
            _hier_spec(),
        )


def test_hier_prepare_success():
    prepared = hier._prepare_model(
        _hier_data(),
        _hier_spec(),
    )

    assert prepared.group_levels == (
        "a",
        "b",
    )

    assert prepared.location_design.shape == (
        4,
        2,
    )


def test_hier_initial_parameters():
    prepared = hier._prepare_model(
        _hier_data(),
        _hier_spec(),
    )

    theta = hier._initial_parameters(prepared)

    assert theta.shape == (6,)

    assert np.isfinite(theta).all()


def test_hier_quadrature_and_unpack():
    spec = _hier_spec()

    nodes, weights = hier._quadrature(spec)

    assert len(nodes) == 3

    assert len(weights) == 9

    theta = np.asarray(
        [
            1,
            2,
            3,
            4,
            np.log(0.5),
            np.log(0.2),
        ],
        dtype=float,
    )

    beta, gamma, tau_l, tau_s = hier._unpack(
        theta,
        2,
        2,
    )

    assert beta.tolist() == [
        1,
        2,
    ]

    assert gamma.tolist() == [
        3,
        4,
    ]

    assert tau_l == pytest.approx(0.5)

    assert tau_s == pytest.approx(0.2)


# ============================================================
# HIERARCHICAL NUMERICAL BOUNDARIES
# ============================================================


@pytest.mark.parametrize(
    (
        "value",
        "upper",
        "expected",
    ),
    [
        (
            np.nan,
            10,
            False,
        ),
        (
            0,
            10,
            False,
        ),
        (
            1e-8,
            10,
            True,
        ),
        (
            10,
            10,
            True,
        ),
        (
            1,
            10,
            False,
        ),
    ],
)
def test_hier_boundary_helper(
    value,
    upper,
    expected,
):
    assert (
        bool(
            hier._random_effect_sd_at_numerical_boundary(
                value,
                upper=upper,
            )
        )
        is expected
    )


def test_hier_boundary_combiner():
    assert hier._random_effect_sd_boundary_reached(
        hier._MIN_RANDOM_EFFECT_SD,
        0.2,
    )

    assert hier._random_effect_sd_boundary_reached(
        0.4,
        hier._MAX_LOG_SCALE_RANDOM_EFFECT_SD,
    )

    assert not hier._random_effect_sd_boundary_reached(
        0.4,
        0.2,
    )


def test_hier_integrand_logscale_guard():
    value, gradient, hessian = hier._group_log_integrand(
        np.asarray(
            [
                0,
                30,
            ],
            dtype=float,
        ),
        np.asarray(
            [
                1,
                2,
            ],
            dtype=float,
        ),
        np.ones(
            (
                2,
                1,
            )
        ),
        np.ones(
            (
                2,
                1,
            )
        ),
        np.asarray(
            [0],
            dtype=float,
        ),
        np.asarray(
            [0],
            dtype=float,
        ),
        0.4,
        0.2,
    )

    assert value == -np.inf

    assert gradient.tolist() == [
        0,
        0,
    ]

    assert hessian.shape == (
        2,
        2,
    )


def test_hier_integrand_regular():
    value, gradient, hessian = hier._group_log_integrand(
        np.asarray(
            [
                0.1,
                0.05,
            ]
        ),
        np.asarray(
            [
                1.0,
                1.2,
            ]
        ),
        np.ones(
            (
                2,
                1,
            )
        ),
        np.ones(
            (
                2,
                1,
            )
        ),
        np.asarray([1.0]),
        np.asarray([-0.1]),
        0.4,
        0.2,
    )

    assert np.isfinite(value)

    assert np.isfinite(gradient).all()

    assert np.isfinite(hessian).all()


# ============================================================
# HIERARCHICAL OBJECTIVE
# ============================================================


def test_hier_objective_nonfinite_theta():
    prepared = hier._prepare_model(
        _hier_data(),
        _hier_spec(),
    )

    nodes, weights = hier._quadrature(_hier_spec())

    objective = hier._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = hier._initial_parameters(prepared)

    theta[0] = np.nan

    assert objective(theta) == 1e100


def test_hier_objective_tau_guard():
    prepared = hier._prepare_model(
        _hier_data(),
        _hier_spec(),
    )

    nodes, weights = hier._quadrature(_hier_spec())

    objective = hier._objective_factory(
        prepared,
        nodes,
        weights,
    )

    theta = hier._initial_parameters(prepared)

    theta[-2] = np.log(hier._MIN_RANDOM_EFFECT_SD) - 2

    assert objective(theta) == 1e100


def test_hier_objective_quadrature_failure(
    monkeypatch,
):
    prepared = hier._prepare_model(
        _hier_data(),
        _hier_spec(),
    )

    nodes, weights = hier._quadrature(_hier_spec())

    monkeypatch.setattr(
        hier,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty(
                (
                    0,
                    2,
                )
            ),
            np.empty(0),
            np.zeros(2),
        ),
    )

    objective = hier._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(hier._initial_parameters(prepared)) == 1e100


def test_hier_objective_success(
    monkeypatch,
):
    prepared = hier._prepare_model(
        _hier_data(),
        _hier_spec(),
    )

    nodes, weights = hier._quadrature(_hier_spec())

    monkeypatch.setattr(
        hier,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            2.0,
            np.zeros(
                (
                    1,
                    2,
                )
            ),
            np.ones(1),
            np.zeros(2),
        ),
    )

    objective = hier._objective_factory(
        prepared,
        nodes,
        weights,
    )

    assert objective(hier._initial_parameters(prepared)) == pytest.approx(-4.0)


def test_hier_group_effect_recovery_failure(
    monkeypatch,
):
    prepared = hier._prepare_model(
        _hier_data(),
        _hier_spec(),
    )

    nodes, weights = hier._quadrature(_hier_spec())

    monkeypatch.setattr(
        hier,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            -np.inf,
            np.empty(
                (
                    0,
                    2,
                )
            ),
            np.empty(0),
            np.zeros(2),
        ),
    )

    with pytest.raises(RuntimeError):
        hier._posterior_group_effects(
            prepared,
            _hier_spec(),
            np.asarray(
                [
                    0.5,
                    0.2,
                ]
            ),
            np.asarray(
                [
                    -0.2,
                    0.1,
                ]
            ),
            0.4,
            0.2,
            nodes,
            weights,
        )


def test_hier_group_effect_recovery_success(
    monkeypatch,
):
    prepared = hier._prepare_model(
        _hier_data(),
        _hier_spec(),
    )

    nodes, weights = hier._quadrature(_hier_spec())

    grid = np.asarray(
        [
            [
                -0.1,
                -0.05,
            ],
            [
                0.1,
                0.05,
            ],
        ]
    )

    probabilities = np.asarray(
        [
            0.5,
            0.5,
        ]
    )

    monkeypatch.setattr(
        hier,
        "_adaptive_group_quadrature",
        lambda *args, **kwargs: (
            1.0,
            grid,
            probabilities,
            np.asarray(
                [
                    0,
                    0,
                ]
            ),
        ),
    )

    frame = hier._posterior_group_effects(
        prepared,
        _hier_spec(),
        np.asarray(
            [
                0.5,
                0.2,
            ]
        ),
        np.asarray(
            [
                -0.2,
                0.1,
            ]
        ),
        0.4,
        0.2,
        nodes,
        weights,
    )

    assert len(frame) == 2

    assert np.isfinite(frame.select_dtypes(include=["number"])).all().all()


# ============================================================
# HIERARCHICAL OUTER FIT FAIL-CLOSED
# ============================================================


def test_hier_fit_nonconvergence(
    monkeypatch,
):
    data = _hier_data()

    spec = _hier_spec()

    def fake_minimize(
        fun,
        x0,
        *,
        method,
        **kwargs,
    ):
        assert method == "L-BFGS-B"

        return SimpleNamespace(
            x=np.asarray(
                x0,
                dtype=float,
            ),
            success=False,
            status=1,
            message="synthetic failure",
            nit=1,
            fun=1.0,
        )

    monkeypatch.setattr(
        hier,
        "minimize",
        fake_minimize,
    )

    with pytest.raises(
        RuntimeError,
        match="did not converge",
    ):
        hier.fit_hierarchical_location_scale(
            data,
            spec=spec,
        )


# ============================================================
# HIERARCHICAL RESULT/PREDICTION
# ============================================================


def test_hier_fixed_effects():
    frame = _hier_result().fixed_effects()

    assert set(frame["equation"]) == {
        "location",
        "log_scale",
    }

    scale = frame.loc[frame["equation"] == "log_scale"]

    assert np.isfinite(scale["sigma_ratio"]).all()


def test_hier_prediction_missing_group_column():
    with pytest.raises(SchemaError):
        hier.predict_hierarchical_location_scale(
            _hier_result(),
            pd.DataFrame({"x": [0]}),
        )


def test_hier_prediction_missing_group_identity():
    data = pd.DataFrame(
        {
            "g": [None],
            "x": [0.0],
        }
    )

    with pytest.raises(SchemaError):
        hier.predict_hierarchical_location_scale(
            _hier_result(),
            data,
        )


def test_hier_prediction_population_only():
    data = pd.DataFrame(
        {
            "g": ["new"],
            "x": [0.0],
        }
    )

    result = hier.predict_hierarchical_location_scale(
        _hier_result(),
        data,
        include_group_effects=False,
    )

    assert not bool(result["group_effect_used"].iloc[0])


def test_hier_prediction_known_group():
    data = pd.DataFrame(
        {
            "g": ["a"],
            "x": [0.0],
        }
    )

    result = hier.predict_hierarchical_location_scale(
        _hier_result(),
        data,
    )

    assert bool(result["group_effect_used"].iloc[0])


def test_hier_prediction_rejects_unseen():
    data = pd.DataFrame(
        {
            "g": ["new"],
            "x": [0.0],
        }
    )

    with pytest.raises(SchemaError):
        hier.predict_hierarchical_location_scale(
            _hier_result(),
            data,
            allow_new_groups=False,
        )


def test_hier_prediction_logscale_guard():
    result = _hier_result(scale_intercept=30.0)

    data = pd.DataFrame(
        {
            "g": ["new"],
            "x": [0.0],
        }
    )

    with pytest.raises(RuntimeError):
        hier.predict_hierarchical_location_scale(
            result,
            data,
            include_group_effects=False,
        )


def test_hier_diagnostics_nonfinite_outcome():
    data = pd.DataFrame(
        {
            "g": ["a"],
            "x": [0.0],
            "y": [np.nan],
        }
    )

    with pytest.raises(SchemaError):
        hier.hierarchical_location_scale_diagnostics(
            _hier_result(),
            data,
        )


def test_hier_diagnostics_success():
    data = pd.DataFrame(
        {
            "g": ["a"],
            "x": [0.0],
            "y": [1.0],
        }
    )

    diagnostics = hier.hierarchical_location_scale_diagnostics(
        _hier_result(),
        data,
    )

    assert np.isfinite(diagnostics["standardized_residual"]).all()


# ============================================================
# HIERARCHICAL RESULT IDENTITY
# ============================================================


def test_hier_result_bad_model_fingerprint():
    result = replace(
        _hier_result(),
        model_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        hier._validate_result_identity(result)


def test_hier_result_bad_input_fingerprint():
    result = _hier_result(input_fingerprint="bad")

    with pytest.raises(SchemaError):
        hier._validate_result_identity(result)


@pytest.mark.parametrize(
    (
        "tau_location",
        "tau_scale",
    ),
    [
        (
            -1.0,
            0.2,
        ),
        (
            0.4,
            -1.0,
        ),
        (
            hier._MIN_RANDOM_EFFECT_SD,
            0.2,
        ),
        (
            0.4,
            hier._MAX_LOG_SCALE_RANDOM_EFFECT_SD,
        ),
    ],
)
def test_hier_result_random_effect_sd(
    tau_location,
    tau_scale,
):
    result = _hier_result(
        tau_location=tau_location,
        tau_scale=tau_scale,
    )

    with pytest.raises(SchemaError):
        hier._validate_result_identity(result)


def test_hier_result_count_mismatch():
    result = _hier_result(
        n_obs=3,
        n_groups=2,
    )

    with pytest.raises(SchemaError):
        hier._validate_result_identity(result)


def test_hier_result_valid():
    identity = hier._validate_result_identity(_hier_result())

    assert identity["n_groups"] == 2


# ============================================================
# HIERARCHICAL CERTIFICATE
# ============================================================


def _hier_certificate():
    return hier.build_hierarchical_location_scale_certificate(_hier_result())


def test_hier_certificate_roundtrip():
    certificate = _hier_certificate()

    hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_extra_field():
    certificate = _hier_certificate()

    certificate["extra"] = True

    _resign_hier(certificate)

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_schema():
    certificate = _hier_certificate()

    certificate["schema"] = "wrong"

    _resign_hier(certificate)

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_fingerprint():
    certificate = _hier_certificate()

    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_claim_boundary():
    certificate = _hier_certificate()

    certificate["claim_boundary"]["causal_effects_established"] = True

    _resign_hier(certificate)

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_model_extra_field():
    certificate = _hier_certificate()

    certificate["model"]["extra"] = True

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_invalid_spec():
    certificate = _hier_certificate()

    certificate["model"]["spec"]["quadrature_points"] = 4

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


@pytest.mark.parametrize(
    "equation",
    [
        "location_fixed_effects",
        "scale_fixed_effects",
    ],
)
def test_hier_certificate_effect_terms(
    equation,
):
    certificate = _hier_certificate()

    certificate["model"][equation].pop("x")

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


@pytest.mark.parametrize(
    "field",
    [
        ("group_effects_fingerprint_sha256"),
        ("input_fingerprint_sha256"),
    ],
)
def test_hier_certificate_lineage_sha(
    field,
):
    certificate = _hier_certificate()

    certificate["model"][field] = "bad"

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_numeric_type():
    certificate = _hier_certificate()

    certificate["model"]["tau_location"] = "0.4"

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_negative_sd():
    certificate = _hier_certificate()

    certificate["model"]["tau_location"] = -1.0

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_boundary_sd():
    certificate = _hier_certificate()

    certificate["model"]["tau_log_scale"] = hier._MAX_LOG_SCALE_RANDOM_EFFECT_SD

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "n_obs",
            True,
        ),
        (
            "n_obs",
            0,
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
def test_hier_certificate_counts(
    field,
    value,
):
    certificate = _hier_certificate()

    certificate["model"][field] = value

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_certificate_min_group_size_count():
    certificate = _hier_certificate()

    certificate["model"]["n_obs"] = 3

    _resign_hier(
        certificate,
        model=True,
    )

    with pytest.raises(SchemaError):
        hier.validate_hierarchical_location_scale_certificate(certificate)


def test_hier_freeze_overwrite(
    tmp_path,
):
    result = _hier_result()

    target = tmp_path / "hier.json"

    assert (
        hier.freeze_hierarchical_location_scale_certificate(
            result,
            target,
        )
        == target
    )

    with pytest.raises(FileExistsError):
        hier.freeze_hierarchical_location_scale_certificate(
            result,
            target,
        )

    hier.freeze_hierarchical_location_scale_certificate(
        result,
        target,
        overwrite=True,
    )


# ============================================================
# RESIDUAL CALIBRATION FIXTURES
# ============================================================


def _cal_summary():
    observed = {metric: float(index + 1) for index, metric in enumerate(cal._METRIC_ORDER)}

    simulated = {
        metric: np.linspace(
            observed[metric] - 0.25,
            observed[metric] + 0.25,
            50,
        )
        for metric in cal._METRIC_ORDER
    }

    return cal._simulation_summary(
        observed,
        simulated,
        envelope_level=0.90,
    )


def _cal_result(
    *,
    family="independent_location_scale",
    n_obs=4,
    n_groups=2,
):
    spec = cal.LocationScaleResidualCalibrationSpec(
        n_simulations=50,
        seed=19,
        envelope_level=0.90,
        max_simulated_residual_draws=1000,
    )

    summary = _cal_summary()

    summary_fp = cal._summary_fingerprint(summary)

    identity = cal._diagnostic_identity_payload(
        spec=spec,
        model_family=family,
        model_fingerprint=SHA_A,
        base_model_certificate_fingerprint=SHA_B,
        input_fingerprint=SHA_C,
        n_obs=n_obs,
        n_groups=n_groups,
        residuals_fingerprint=SHA_D,
        summary_fingerprint=summary_fp,
    )

    return cal.LocationScaleResidualCalibrationResult(
        spec=spec,
        model_family=family,
        model_fingerprint_sha256=SHA_A,
        base_model_certificate_fingerprint_sha256=SHA_B,
        input_fingerprint_sha256=SHA_C,
        n_obs=n_obs,
        n_groups=n_groups,
        residuals_fingerprint_sha256=SHA_D,
        summary=summary,
        summary_fingerprint_sha256=summary_fp,
        diagnostic_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )


def _resign_cal(
    certificate,
    *,
    diagnostic=False,
):
    if diagnostic:
        certificate["diagnostic_fingerprint_sha256"] = benchmark_fingerprint(
            certificate["diagnostic"]
        )

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


# ============================================================
# RESIDUAL ADAPTERS
# ============================================================


@pytest.mark.parametrize(
    (
        "klass",
        "family",
    ),
    [
        (
            cal.HierarchicalLocationScaleResult,
            "independent_location_scale",
        ),
        (
            cal.CorrelatedLocationScaleResult,
            "correlated_location_scale",
        ),
        (
            cal.LocationRandomSlopeScaleResult,
            "location_random_slope_scale",
        ),
        (
            cal.CorrelatedLocationRandomSlopeScaleResult,
            ("correlated_location_random_slope_scale"),
        ),
        (
            cal.FullCovarianceLocationRandomSlopeScaleResult,
            ("full_covariance_location_random_slope_scale"),
        ),
    ],
)
def test_cal_model_adapter(
    klass,
    family,
):
    result = object.__new__(klass)

    object.__setattr__(
        result,
        "spec",
        SimpleNamespace(),
    )

    observed, _, diagnostic = cal._model_adapter(result)

    assert observed == family

    assert callable(diagnostic)


def test_cal_model_adapter_type():
    with pytest.raises(TypeError):
        cal._model_adapter(object())


# ============================================================
# RESIDUAL FITTING INPUT
# ============================================================


def test_cal_input_columns_deduplicate():
    spec = SimpleNamespace(
        outcome_col="y",
        group_col="g",
        location_predictors=("x",),
        scale_predictors=("x",),
    )

    assert cal._input_columns(spec) == [
        "y",
        "g",
        "x",
    ]


def test_cal_exact_input_type():
    result = SimpleNamespace(
        spec=SimpleNamespace(
            outcome_col="y",
            group_col="g",
            location_predictors=(),
            scale_predictors=(),
        ),
        input_fingerprint_sha256=SHA_A,
    )

    with pytest.raises(TypeError):
        cal._require_exact_fitting_input(
            result,
            object(),
        )


def test_cal_exact_input_missing():
    result = SimpleNamespace(
        spec=SimpleNamespace(
            outcome_col="y",
            group_col="g",
            location_predictors=(),
            scale_predictors=(),
        ),
        input_fingerprint_sha256=SHA_A,
    )

    with pytest.raises(SchemaError):
        cal._require_exact_fitting_input(
            result,
            pd.DataFrame({"y": [1]}),
        )


def test_cal_exact_input_mismatch():
    data = pd.DataFrame(
        {
            "y": [
                1,
                2,
            ],
            "g": [
                "a",
                "b",
            ],
        }
    )

    result = SimpleNamespace(
        spec=SimpleNamespace(
            outcome_col="y",
            group_col="g",
            location_predictors=(),
            scale_predictors=(),
        ),
        input_fingerprint_sha256=SHA_A,
    )

    with pytest.raises(SchemaError):
        cal._require_exact_fitting_input(
            result,
            data,
        )


def test_cal_exact_input_success():
    data = pd.DataFrame(
        {
            "y": [
                1,
                2,
            ],
            "g": [
                "a",
                "b",
            ],
        }
    )

    current = fingerprint_frame(
        data.loc[
            :,
            [
                "y",
                "g",
            ],
        ]
    )

    result = SimpleNamespace(
        spec=SimpleNamespace(
            outcome_col="y",
            group_col="g",
            location_predictors=(),
            scale_predictors=(),
        ),
        input_fingerprint_sha256=current,
    )

    assert (
        cal._require_exact_fitting_input(
            result,
            data,
        )
        == current
    )


# ============================================================
# RESIDUAL NUMERICAL HELPERS
# ============================================================


def test_cal_moments_too_short():
    with pytest.raises(SchemaError):
        cal._safe_standardized_moments(np.asarray([1.0]))


def test_cal_moments_zero_dispersion():
    with pytest.raises(SchemaError):
        cal._safe_standardized_moments(
            np.asarray(
                [
                    1.0,
                    1.0,
                    1.0,
                ]
            )
        )


def test_cal_moments_success():
    mean, sd, skew, kurt = cal._safe_standardized_moments(
        np.asarray(
            [
                -1.0,
                0.0,
                1.0,
            ]
        )
    )

    assert mean == pytest.approx(0)

    assert sd > 0

    assert np.isfinite(
        [
            skew,
            kurt,
        ]
    ).all()


def test_cal_qq_rmse():
    value = cal._normal_qq_rmse(
        np.asarray(
            [
                -1.0,
                0.0,
                1.0,
            ]
        )
    )

    assert np.isfinite(value)

    assert value >= 0


def test_cal_group_empty():
    with pytest.raises(SchemaError):
        cal._group_metric_arrays(
            np.asarray(
                [
                    1.0,
                    2.0,
                ]
            ),
            np.asarray(
                [
                    0,
                    0,
                ]
            ),
            2,
        )


def test_cal_group_zero_second_moment():
    with pytest.raises(SchemaError):
        cal._group_metric_arrays(
            np.asarray(
                [
                    0.0,
                    1.0,
                ]
            ),
            np.asarray(
                [
                    0,
                    1,
                ]
            ),
            2,
        )


def test_cal_group_success():
    means, moments = cal._group_metric_arrays(
        np.asarray(
            [
                -1.0,
                1.0,
                -0.5,
                0.5,
            ]
        ),
        np.asarray(
            [
                0,
                0,
                1,
                1,
            ]
        ),
        2,
    )

    assert np.isfinite(means).all()

    assert np.isfinite(moments).all()


@pytest.mark.parametrize(
    (
        "z",
        "codes",
    ),
    [
        (
            np.asarray([[1.0]]),
            np.asarray([0]),
        ),
        (
            np.asarray(
                [
                    1.0,
                    2.0,
                ]
            ),
            np.asarray([0]),
        ),
        (
            np.asarray(
                [
                    1.0,
                    np.nan,
                ]
            ),
            np.asarray(
                [
                    0,
                    1,
                ]
            ),
        ),
    ],
)
def test_cal_metrics_vector_contract(
    z,
    codes,
):
    with pytest.raises(SchemaError):
        cal._residual_metrics(
            z,
            codes,
            2,
            tail_threshold=1.96,
        )


def test_cal_metrics_success():
    result = cal._residual_metrics(
        np.asarray(
            [
                -1.0,
                1.0,
                -0.5,
                0.5,
            ]
        ),
        np.asarray(
            [
                0,
                0,
                1,
                1,
            ]
        ),
        2,
        tail_threshold=1.96,
    )

    assert tuple(result) == cal._METRIC_ORDER


# ============================================================
# RESIDUAL SUMMARY CANONICALIZATION
# ============================================================


def test_cal_summary_type():
    with pytest.raises(SchemaError):
        cal._canonical_summary([])


def test_cal_summary_columns():
    summary = _cal_summary()

    summary["extra"] = True

    with pytest.raises(SchemaError):
        cal._canonical_summary(summary)


def test_cal_summary_length():
    summary = _cal_summary().iloc[:-1].copy()

    with pytest.raises(SchemaError):
        cal._canonical_summary(summary)


def test_cal_summary_order():
    summary = _cal_summary().iloc[::-1].reset_index(drop=True)

    with pytest.raises(SchemaError):
        cal._canonical_summary(summary)


def test_cal_summary_nonfinite():
    summary = _cal_summary()

    summary.loc[
        0,
        "observed",
    ] = np.nan

    with pytest.raises(SchemaError):
        cal._canonical_summary(summary)


def test_cal_summary_bounds():
    summary = _cal_summary()

    summary.loc[
        0,
        "envelope_lower",
    ] = 10

    summary.loc[
        0,
        "envelope_upper",
    ] = 0

    with pytest.raises(SchemaError):
        cal._canonical_summary(summary)


def test_cal_summary_percentile():
    summary = _cal_summary()

    summary.loc[
        0,
        "simulation_percentile",
    ] = 2

    with pytest.raises(SchemaError):
        cal._canonical_summary(summary)


def test_cal_summary_boolean():
    summary = _cal_summary().astype({"outside_envelope": (object)})

    summary.loc[
        0,
        "outside_envelope",
    ] = 1

    with pytest.raises(SchemaError):
        cal._canonical_summary(summary)


def test_cal_summary_contradiction():
    summary = _cal_summary()

    summary.loc[
        0,
        "outside_envelope",
    ] = not bool(
        summary.loc[
            0,
            "outside_envelope",
        ]
    )

    with pytest.raises(SchemaError):
        cal._canonical_summary(summary)


def test_cal_summary_success():
    summary = cal._canonical_summary(_cal_summary())

    assert len(summary) == len(cal._METRIC_ORDER)


# ============================================================
# RESIDUAL CALIBRATION ORCHESTRATION
# ============================================================


def _patch_calibration(
    monkeypatch,
    *,
    nonfinite=False,
):
    model_spec = SimpleNamespace(
        outcome_col="y",
        group_col="g",
        location_predictors=(),
        scale_predictors=(),
    )

    base = SimpleNamespace(
        spec=model_spec,
        model_fingerprint_sha256=SHA_A,
    )

    def diagnostics(
        result,
        data,
    ):
        z = np.asarray(
            [
                -1.0,
                0.5,
                -0.5,
                1.0,
            ]
        )

        if nonfinite:
            z[0] = np.nan

        return pd.DataFrame(
            {
                "location_mean": [
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                ],
                "sigma": [
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                ],
                "residual": z,
                ("standardized_residual"): z,
                "group_effect_used": [
                    True,
                    True,
                    True,
                    True,
                ],
            },
            index=data.index,
        )

    monkeypatch.setattr(
        cal,
        "_model_adapter",
        lambda result: (
            "independent_location_scale",
            model_spec,
            diagnostics,
        ),
    )

    monkeypatch.setattr(
        cal,
        "_require_certifiable_base_model",
        lambda result: SHA_B,
    )

    monkeypatch.setattr(
        cal,
        "_require_exact_fitting_input",
        lambda result, data: SHA_C,
    )

    return base


def _cal_data():
    return pd.DataFrame(
        {
            "g": [
                "a",
                "a",
                "b",
                "b",
            ],
            "y": [
                1.0,
                1.2,
                0.8,
                1.1,
            ],
        }
    )


def test_calibrate_nonfinite_residual(
    monkeypatch,
):
    base = _patch_calibration(
        monkeypatch,
        nonfinite=True,
    )

    with pytest.raises(SchemaError):
        cal.calibrate_location_scale_residuals(
            base,
            _cal_data(),
            spec=(
                cal.LocationScaleResidualCalibrationSpec(
                    n_simulations=50,
                    max_simulated_residual_draws=1000,
                )
            ),
        )


def test_calibrate_missing_group(
    monkeypatch,
):
    base = _patch_calibration(monkeypatch)

    data = _cal_data()

    data.loc[
        0,
        "g",
    ] = None

    with pytest.raises(SchemaError):
        cal.calibrate_location_scale_residuals(
            base,
            data,
            spec=(
                cal.LocationScaleResidualCalibrationSpec(
                    n_simulations=50,
                    max_simulated_residual_draws=1000,
                )
            ),
        )


def test_calibrate_one_group(
    monkeypatch,
):
    base = _patch_calibration(monkeypatch)

    data = _cal_data()

    data["g"] = "a"

    with pytest.raises(SchemaError):
        cal.calibrate_location_scale_residuals(
            base,
            data,
            spec=(
                cal.LocationScaleResidualCalibrationSpec(
                    n_simulations=50,
                    max_simulated_residual_draws=1000,
                )
            ),
        )


def test_calibrate_budget(
    monkeypatch,
):
    base = _patch_calibration(monkeypatch)

    with pytest.raises(SchemaError):
        cal.calibrate_location_scale_residuals(
            base,
            _cal_data(),
            spec=(
                cal.LocationScaleResidualCalibrationSpec(
                    n_simulations=50,
                    max_simulated_residual_draws=100,
                )
            ),
        )


def test_calibrate_success(
    monkeypatch,
):
    base = _patch_calibration(monkeypatch)

    result = cal.calibrate_location_scale_residuals(
        base,
        _cal_data(),
        spec=(
            cal.LocationScaleResidualCalibrationSpec(
                n_simulations=50,
                seed=123,
                envelope_level=0.9,
                max_simulated_residual_draws=1000,
            )
        ),
    )

    assert result.n_groups == 2

    assert len(result.summary) == len(cal._METRIC_ORDER)

    assert len(result.diagnostic_fingerprint_sha256) == 64


# ============================================================
# RESIDUAL RESULT IDENTITY
# ============================================================


def test_cal_result_type():
    with pytest.raises(TypeError):
        cal._validate_result_identity(object())


def test_cal_result_family():
    result = _cal_result(family="other")

    with pytest.raises(SchemaError):
        cal._validate_result_identity(result)


@pytest.mark.parametrize(
    "field",
    [
        "model_fingerprint_sha256",
        ("base_model_certificate_fingerprint_sha256"),
        "input_fingerprint_sha256",
        "residuals_fingerprint_sha256",
        "summary_fingerprint_sha256",
        ("diagnostic_fingerprint_sha256"),
    ],
)
def test_cal_result_sha(
    field,
):
    result = replace(
        _cal_result(),
        **{field: "bad"},
    )

    with pytest.raises(SchemaError):
        cal._validate_result_identity(result)


def test_cal_result_summary_mutation():
    result = _cal_result()

    summary = result.summary.copy()

    summary.loc[
        0,
        "observed",
    ] += 0.1

    result = replace(
        result,
        summary=summary,
    )

    with pytest.raises(SchemaError):
        cal._validate_result_identity(result)


def test_cal_result_identity_mismatch():
    result = replace(
        _cal_result(),
        diagnostic_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        cal._validate_result_identity(result)


@pytest.mark.parametrize(
    (
        "n_obs",
        "n_groups",
    ),
    [
        (
            1,
            2,
        ),
        (
            4,
            1,
        ),
        (
            2,
            3,
        ),
    ],
)
def test_cal_result_counts(
    n_obs,
    n_groups,
):
    result = _cal_result(
        n_obs=n_obs,
        n_groups=n_groups,
    )

    with pytest.raises(SchemaError):
        cal._validate_result_identity(result)


def test_cal_result_metrics_defensive():
    result = _cal_result()

    copied = result.metrics()

    copied.loc[
        0,
        "observed",
    ] += 10

    assert (
        copied.loc[
            0,
            "observed",
        ]
        != result.summary.loc[
            0,
            "observed",
        ]
    )


# ============================================================
# RESIDUAL CERTIFICATE
# ============================================================


def _cal_certificate():
    return cal.build_location_scale_residual_calibration_certificate(_cal_result())


def test_cal_certificate_roundtrip():
    certificate = _cal_certificate()

    cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_type():
    with pytest.raises(TypeError):
        cal.validate_location_scale_residual_calibration_certificate([])


def test_cal_certificate_extra():
    certificate = _cal_certificate()

    certificate["extra"] = True

    _resign_cal(certificate)

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_schema():
    certificate = _cal_certificate()

    certificate["schema"] = "wrong"

    _resign_cal(certificate)

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_fingerprint():
    certificate = _cal_certificate()

    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_boundary():
    certificate = _cal_certificate()

    certificate["claim_boundary"]["global_model_adequacy_established"] = True

    _resign_cal(certificate)

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_diagnostic_schema():
    certificate = _cal_certificate()

    certificate["diagnostic"]["schema"] = "wrong"

    _resign_cal(
        certificate,
        diagnostic=True,
    )

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_invalid_spec():
    certificate = _cal_certificate()

    certificate["diagnostic"]["spec"]["n_simulations"] = 49

    _resign_cal(
        certificate,
        diagnostic=True,
    )

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_family():
    certificate = _cal_certificate()

    certificate["diagnostic"]["model_family"] = "other"

    _resign_cal(
        certificate,
        diagnostic=True,
    )

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_lineage_sha():
    certificate = _cal_certificate()

    certificate["diagnostic"]["input_fingerprint_sha256"] = "bad"

    _resign_cal(
        certificate,
        diagnostic=True,
    )

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_counts():
    certificate = _cal_certificate()

    certificate["diagnostic"]["n_groups"] = 1

    _resign_cal(
        certificate,
        diagnostic=True,
    )

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_budget():
    certificate = _cal_certificate()

    certificate["diagnostic"]["spec"]["max_simulated_residual_draws"] = 100

    _resign_cal(
        certificate,
        diagnostic=True,
    )

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_summary_length():
    certificate = _cal_certificate()

    certificate["summary"] = []

    _resign_cal(certificate)

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_metric_inventory():
    certificate = _cal_certificate()

    certificate["summary"][0]["metric"] = "other"

    _resign_cal(certificate)

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_summary_fingerprint():
    certificate = _cal_certificate()

    certificate["summary"][0]["observed"] += 0.1

    _resign_cal(certificate)

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_certificate_diagnostic_fingerprint():
    certificate = _cal_certificate()

    certificate["diagnostic_fingerprint_sha256"] = "0" * 64

    _resign_cal(certificate)

    with pytest.raises(SchemaError):
        cal.validate_location_scale_residual_calibration_certificate(certificate)


def test_cal_freeze(
    tmp_path,
):
    result = _cal_result()

    target = tmp_path / "calibration.json"

    assert (
        cal.freeze_location_scale_residual_calibration_certificate(
            result,
            target,
        )
        == target
    )

    with pytest.raises(FileExistsError):
        cal.freeze_location_scale_residual_calibration_certificate(
            result,
            target,
        )

    cal.freeze_location_scale_residual_calibration_certificate(
        result,
        target,
        overwrite=True,
    )
