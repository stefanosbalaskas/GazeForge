from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import gazeforge.location_scale_refit_residual_calibration as refit
from gazeforge import _location_scale_bootstrap_monte_carlo_core as mc
from gazeforge import _location_scale_hierarchical_bootstrap_core as hb
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64


# ============================================================
# SHARED SYNTHETIC BUILDERS
# ============================================================


def _refit_ledger():
    rows = []

    for index in range(2):
        rows.append(
            {
                "simulation_index": index,
                "model_fingerprint_sha256": SHA_A,
                "model_certificate_fingerprint_sha256": SHA_B,
                ("standardized_residuals_fingerprint_sha256"): SHA_C,
            }
        )

    return refit._canonical_refit_ledger(
        rows,
        n_simulations=2,
    )


def _refit_summary():
    observed = {metric: float(index + 1) for index, metric in enumerate(refit._METRIC_ORDER)}

    simulated = {
        metric: np.asarray(
            [
                observed[metric] - 0.25,
                observed[metric] + 0.25,
            ],
            dtype=float,
        )
        for metric in refit._METRIC_ORDER
    }

    return refit._simulation_summary(
        observed,
        simulated,
        envelope_level=0.90,
    )


def _refit_result():
    spec = refit.LocationScaleRefitResidualCalibrationSpec(
        n_simulations=2,
        seed=7,
        envelope_level=0.90,
        max_refit_rows=100,
    )

    ledger = _refit_ledger()

    ledger_fp = refit._refit_ledger_fingerprint(
        ledger,
        n_simulations=2,
    )

    summary = _refit_summary()

    summary_fp = refit._summary_fingerprint(summary)

    identity = refit._diagnostic_identity_payload(
        spec=spec,
        model_family=("independent_location_scale"),
        model_fingerprint=SHA_A,
        base_model_certificate_fingerprint=SHA_B,
        input_fingerprint=SHA_C,
        n_obs=4,
        n_groups=2,
        observed_residuals_fingerprint=SHA_D,
        refit_ledger_fingerprint=ledger_fp,
        summary_fingerprint=summary_fp,
    )

    return refit.LocationScaleRefitResidualCalibrationResult(
        spec=spec,
        model_family=("independent_location_scale"),
        model_fingerprint_sha256=SHA_A,
        base_model_certificate_fingerprint_sha256=SHA_B,
        input_fingerprint_sha256=SHA_C,
        n_obs=4,
        n_groups=2,
        observed_residuals_fingerprint_sha256=SHA_D,
        refit_ledger=ledger,
        refit_ledger_fingerprint_sha256=ledger_fp,
        summary=summary,
        summary_fingerprint_sha256=summary_fp,
        diagnostic_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )


def _hb_inventory():
    return hb._canonical_inventory(
        [
            {
                "parameter_id": ("location_fixed::Intercept"),
                "component": ("location_fixed"),
                "term": "Intercept",
                "observed": 1.0,
            },
            {
                "parameter_id": ("random_sd::location_intercept"),
                "component": "random_sd",
                "term": ("location_intercept"),
                "observed": 0.4,
            },
        ]
    )


def _hb_ledger(
    n_simulations=3,
):
    inventory = _hb_inventory()

    rows = []

    for index in range(n_simulations):
        rows.append(
            {
                "simulation_index": index,
                ("population_random_effects_fingerprint_sha256"): SHA_A,
                ("simulated_input_fingerprint_sha256"): SHA_B,
                ("model_fingerprint_sha256"): SHA_C,
                ("model_certificate_fingerprint_sha256"): SHA_D,
                "parameter_estimates": {
                    ("location_fixed::Intercept"): (0.9 + 0.1 * index),
                    ("random_sd::location_intercept"): (0.35 + 0.02 * index),
                },
            }
        )

    return hb._canonical_refit_ledger(
        rows,
        inventory=inventory,
        n_simulations=n_simulations,
    )


def _hb_result(
    n_simulations=3,
):
    spec = hb.LocationScaleHierarchicalBootstrapSpec(
        n_simulations=n_simulations,
        seed=11,
        interval_level=0.90,
        max_refit_rows=100,
    )

    inventory = _hb_inventory()

    ledger = _hb_ledger(n_simulations)

    ledger_fp = hb._refit_ledger_fingerprint(
        ledger,
        inventory=inventory,
        n_simulations=n_simulations,
    )

    summary = hb._bootstrap_summary(
        inventory,
        ledger,
        interval_level=(spec.interval_level),
    )

    summary_fp = hb._summary_fingerprint(summary)

    identity = hb._bootstrap_identity_payload(
        spec=spec,
        model_family=("independent_location_scale"),
        model_fingerprint=SHA_E,
        base_model_certificate_fingerprint=SHA_F,
        input_fingerprint=SHA_A,
        n_obs=10,
        n_groups=2,
        parameter_inventory=inventory,
        refit_ledger_fingerprint=ledger_fp,
        summary_fingerprint=summary_fp,
    )

    return hb.LocationScaleHierarchicalBootstrapResult(
        spec=spec,
        model_family=("independent_location_scale"),
        model_fingerprint_sha256=SHA_E,
        base_model_certificate_fingerprint_sha256=SHA_F,
        input_fingerprint_sha256=SHA_A,
        n_obs=10,
        n_groups=2,
        parameter_inventory=inventory,
        refit_ledger=ledger,
        refit_ledger_fingerprint_sha256=ledger_fp,
        summary=summary,
        summary_fingerprint_sha256=summary_fp,
        bootstrap_fingerprint_sha256=(benchmark_fingerprint(identity)),
    )


def _resign(
    certificate,
):
    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


# ============================================================
# REFIT SPEC VALIDATION
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        True,
        1,
        10001,
    ],
)
def test_refit_spec_simulations(
    value,
):
    with pytest.raises(ValueError):
        refit.LocationScaleRefitResidualCalibrationSpec(n_simulations=value)


@pytest.mark.parametrize(
    "value",
    [
        True,
        -1,
    ],
)
def test_refit_spec_seed(
    value,
):
    with pytest.raises(ValueError):
        refit.LocationScaleRefitResidualCalibrationSpec(seed=value)


@pytest.mark.parametrize(
    "value",
    [
        0.5,
        1.0,
        np.nan,
        np.inf,
    ],
)
def test_refit_spec_envelope(
    value,
):
    with pytest.raises(ValueError):
        refit.LocationScaleRefitResidualCalibrationSpec(envelope_level=value)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        np.nan,
        np.inf,
    ],
)
def test_refit_spec_tail_threshold(
    value,
):
    with pytest.raises(ValueError):
        refit.LocationScaleRefitResidualCalibrationSpec(absolute_tail_threshold=value)


@pytest.mark.parametrize(
    "value",
    [
        True,
        0,
        -1,
    ],
)
def test_refit_spec_budget(
    value,
):
    with pytest.raises(ValueError):
        refit.LocationScaleRefitResidualCalibrationSpec(max_refit_rows=value)


def test_refit_spec_canonicalizes_float_fields():
    spec = refit.LocationScaleRefitResidualCalibrationSpec(
        envelope_level=np.float64(0.9),
        absolute_tail_threshold=np.float64(2),
    )

    assert isinstance(
        spec.envelope_level,
        float,
    )

    assert isinstance(
        spec.absolute_tail_threshold,
        float,
    )


# ============================================================
# REFIT MODEL DISPATCH
# ============================================================


@pytest.mark.parametrize(
    (
        "klass",
        "expected",
    ),
    [
        (
            refit.HierarchicalLocationScaleResult,
            refit.fit_hierarchical_location_scale,
        ),
        (
            refit.CorrelatedLocationScaleResult,
            refit.fit_correlated_location_scale,
        ),
        (
            (refit.CorrelatedLocationRandomSlopeScaleResult),
            (refit.fit_correlated_location_random_slope_scale),
        ),
        (
            refit.LocationRandomSlopeScaleResult,
            refit.fit_location_random_slope_scale,
        ),
        (
            (refit.FullCovarianceLocationRandomSlopeScaleResult),
            (refit.fit_full_covariance_location_random_slope_scale),
        ),
    ],
)
def test_refit_fit_function_dispatch(
    klass,
    expected,
):
    instance = object.__new__(klass)

    assert refit._fit_function_for_result(instance) is expected


def test_refit_fit_function_type():
    with pytest.raises(TypeError):
        refit._fit_function_for_result(object())


# ============================================================
# REFIT LEDGER
# ============================================================


@pytest.mark.parametrize(
    "rows",
    [
        None,
        [],
        (),
        [{"simulation_index": 0}],
    ],
)
def test_refit_ledger_length(
    rows,
):
    with pytest.raises(SchemaError):
        refit._canonical_refit_ledger(
            rows,
            n_simulations=2,
        )


@pytest.mark.parametrize(
    "index",
    [
        True,
        -1,
        1,
    ],
)
def test_refit_ledger_index(
    index,
):
    rows = [
        {
            "simulation_index": index,
            "model_fingerprint_sha256": SHA_A,
            ("model_certificate_fingerprint_sha256"): SHA_B,
            ("standardized_residuals_fingerprint_sha256"): SHA_C,
        },
        {
            "simulation_index": 1,
            "model_fingerprint_sha256": SHA_A,
            ("model_certificate_fingerprint_sha256"): SHA_B,
            ("standardized_residuals_fingerprint_sha256"): SHA_C,
        },
    ]

    with pytest.raises(SchemaError):
        refit._canonical_refit_ledger(
            rows,
            n_simulations=2,
        )


@pytest.mark.parametrize(
    "field",
    [
        "model_fingerprint_sha256",
        ("model_certificate_fingerprint_sha256"),
        ("standardized_residuals_fingerprint_sha256"),
    ],
)
def test_refit_ledger_sha(
    field,
):
    rows = [
        {
            "simulation_index": 0,
            "model_fingerprint_sha256": SHA_A,
            ("model_certificate_fingerprint_sha256"): SHA_B,
            ("standardized_residuals_fingerprint_sha256"): SHA_C,
        },
        {
            "simulation_index": 1,
            "model_fingerprint_sha256": SHA_A,
            ("model_certificate_fingerprint_sha256"): SHA_B,
            ("standardized_residuals_fingerprint_sha256"): SHA_C,
        },
    ]

    rows[0][field] = "bad"

    with pytest.raises(SchemaError):
        refit._canonical_refit_ledger(
            rows,
            n_simulations=2,
        )


def test_refit_ledger_extra_field():
    rows = [dict(row) for row in _refit_ledger()]

    rows[0]["accepted"] = True

    with pytest.raises(SchemaError):
        refit._canonical_refit_ledger(
            rows,
            n_simulations=2,
        )


def test_refit_ledger_fingerprint_stable():
    ledger = _refit_ledger()

    assert refit._refit_ledger_fingerprint(
        ledger,
        n_simulations=2,
    ) == refit._refit_ledger_fingerprint(
        ledger,
        n_simulations=2,
    )


# ============================================================
# REFIT RESIDUAL FRAME
# ============================================================


def test_refit_residual_frame_fingerprint():
    data = pd.DataFrame(
        {
            "g": [
                "a",
                "a",
                "b",
                "b",
            ]
        }
    )

    diagnostics = pd.DataFrame(
        {
            "location_mean": [
                1,
                2,
                3,
                4,
            ],
            "sigma": [
                1,
                1,
                1,
                1,
            ],
            "residual": [
                -1,
                1,
                -1,
                1,
            ],
            ("standardized_residual"): [
                -1,
                1,
                -1,
                1,
            ],
            "group_effect_used": [
                True,
                True,
                True,
                True,
            ],
        }
    )

    fingerprint = refit._residual_frame_fingerprint(
        data,
        diagnostics,
        group_col="g",
    )

    assert len(fingerprint) == 64


# ============================================================
# REFIT RESULT IDENTITY
# ============================================================


def test_refit_result_type():
    with pytest.raises(TypeError):
        refit._validate_result_identity(object())


def test_refit_result_family():
    result = replace(
        _refit_result(),
        model_family="other",
    )

    with pytest.raises(SchemaError):
        refit._validate_result_identity(result)


@pytest.mark.parametrize(
    "field",
    [
        "model_fingerprint_sha256",
        ("base_model_certificate_fingerprint_sha256"),
        "input_fingerprint_sha256",
        ("observed_residuals_fingerprint_sha256"),
        ("refit_ledger_fingerprint_sha256"),
        ("summary_fingerprint_sha256"),
        ("diagnostic_fingerprint_sha256"),
    ],
)
def test_refit_result_bad_sha(
    field,
):
    result = replace(
        _refit_result(),
        **{field: "bad"},
    )

    with pytest.raises(SchemaError):
        refit._validate_result_identity(result)


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
def test_refit_result_counts(
    n_obs,
    n_groups,
):
    result = replace(
        _refit_result(),
        n_obs=n_obs,
        n_groups=n_groups,
    )

    with pytest.raises(SchemaError):
        refit._validate_result_identity(result)


def test_refit_result_budget():
    result = replace(
        _refit_result(),
        spec=(
            refit.LocationScaleRefitResidualCalibrationSpec(
                n_simulations=2,
                max_refit_rows=4,
            )
        ),
    )

    with pytest.raises(SchemaError):
        refit._validate_result_identity(result)


def test_refit_result_ledger_mutation():
    result = replace(
        _refit_result(),
        refit_ledger_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        refit._validate_result_identity(result)


def test_refit_result_summary_mutation():
    result = _refit_result()

    changed = result.summary.copy()

    changed.loc[
        0,
        "observed",
    ] += 0.1

    result = replace(
        result,
        summary=changed,
    )

    with pytest.raises(SchemaError):
        refit._validate_result_identity(result)


def test_refit_result_diagnostic_mutation():
    result = replace(
        _refit_result(),
        diagnostic_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        refit._validate_result_identity(result)


def test_refit_result_accessors_defensive():
    result = _refit_result()

    metrics = result.metrics()
    refits = result.refits()

    metrics.loc[
        0,
        "observed",
    ] += 100

    refits.loc[
        0,
        "simulation_index",
    ] = 99

    assert (
        result.summary.loc[
            0,
            "observed",
        ]
        != metrics.loc[
            0,
            "observed",
        ]
    )

    assert result.refit_ledger[0]["simulation_index"] == 0


# ============================================================
# REFIT ORCHESTRATION WITHOUT EXPENSIVE FITTING
# ============================================================


def _patch_refit_orchestration(
    monkeypatch,
    *,
    base_nonfinite=False,
    refit_nonfinite=False,
    fail_refit=False,
):
    model_spec = SimpleNamespace(
        outcome_col="y",
        group_col="g",
    )

    base = SimpleNamespace(
        spec=model_spec,
        model_fingerprint_sha256=SHA_A,
        kind="base",
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

        if result.kind == "base" and base_nonfinite:
            z[0] = np.nan

        if result.kind == "refit" and refit_nonfinite:
            z[0] = np.nan

        return pd.DataFrame(
            {
                "location_mean": [
                    1.0,
                    1.1,
                    1.2,
                    1.3,
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

    def fake_fit(
        data,
        *,
        spec,
    ):
        if fail_refit:
            raise RuntimeError("synthetic optimizer failure")

        return SimpleNamespace(
            spec=spec,
            model_fingerprint_sha256=SHA_E,
            kind="refit",
        )

    monkeypatch.setattr(
        refit,
        "_model_adapter",
        lambda result: (
            "independent_location_scale",
            model_spec,
            diagnostics,
        ),
    )

    monkeypatch.setattr(
        refit,
        "_fit_function_for_result",
        lambda result: fake_fit,
    )

    monkeypatch.setattr(
        refit,
        "_require_certifiable_base_model",
        lambda result: SHA_B,
    )

    monkeypatch.setattr(
        refit,
        "_require_exact_fitting_input",
        lambda result, data: SHA_C,
    )

    return base


def _small_refit_data():
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
                1.1,
                1.2,
                1.3,
            ],
        }
    )


def test_refit_orchestration_budget(
    monkeypatch,
):
    base = _patch_refit_orchestration(monkeypatch)

    with pytest.raises(SchemaError):
        refit.calibrate_location_scale_residuals_with_refits(
            base,
            _small_refit_data(),
            spec=(
                refit.LocationScaleRefitResidualCalibrationSpec(
                    n_simulations=2,
                    max_refit_rows=4,
                )
            ),
        )


def test_refit_orchestration_observed_nonfinite(
    monkeypatch,
):
    base = _patch_refit_orchestration(
        monkeypatch,
        base_nonfinite=True,
    )

    with pytest.raises(SchemaError):
        refit.calibrate_location_scale_residuals_with_refits(
            base,
            _small_refit_data(),
            spec=(
                refit.LocationScaleRefitResidualCalibrationSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_refit_orchestration_missing_group(
    monkeypatch,
):
    base = _patch_refit_orchestration(monkeypatch)

    data = _small_refit_data()

    data.loc[
        0,
        "g",
    ] = None

    with pytest.raises(SchemaError):
        refit.calibrate_location_scale_residuals_with_refits(
            base,
            data,
            spec=(
                refit.LocationScaleRefitResidualCalibrationSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_refit_orchestration_one_group(
    monkeypatch,
):
    base = _patch_refit_orchestration(monkeypatch)

    data = _small_refit_data()

    data["g"] = "a"

    with pytest.raises(SchemaError):
        refit.calibrate_location_scale_residuals_with_refits(
            base,
            data,
            spec=(
                refit.LocationScaleRefitResidualCalibrationSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_refit_orchestration_failed_refit(
    monkeypatch,
):
    base = _patch_refit_orchestration(
        monkeypatch,
        fail_refit=True,
    )

    with pytest.raises(SchemaError):
        refit.calibrate_location_scale_residuals_with_refits(
            base,
            _small_refit_data(),
            spec=(
                refit.LocationScaleRefitResidualCalibrationSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_refit_orchestration_refit_nonfinite(
    monkeypatch,
):
    base = _patch_refit_orchestration(
        monkeypatch,
        refit_nonfinite=True,
    )

    with pytest.raises(SchemaError):
        refit.calibrate_location_scale_residuals_with_refits(
            base,
            _small_refit_data(),
            spec=(
                refit.LocationScaleRefitResidualCalibrationSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_refit_orchestration_success(
    monkeypatch,
):
    base = _patch_refit_orchestration(monkeypatch)

    result = refit.calibrate_location_scale_residuals_with_refits(
        base,
        _small_refit_data(),
        spec=(
            refit.LocationScaleRefitResidualCalibrationSpec(
                n_simulations=2,
                seed=12,
                envelope_level=0.9,
                max_refit_rows=100,
            )
        ),
    )

    assert result.model_family == "independent_location_scale"

    assert len(result.refit_ledger) == 2

    assert result.n_groups == 2

    assert len(result.diagnostic_fingerprint_sha256) == 64


# ============================================================
# REFIT CERTIFICATE
# ============================================================


def _refit_certificate():
    return refit.build_location_scale_refit_residual_calibration_certificate(_refit_result())


def test_refit_certificate_roundtrip():
    certificate = _refit_certificate()

    refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_type():
    with pytest.raises(TypeError):
        refit.validate_location_scale_refit_residual_calibration_certificate([])


def test_refit_certificate_extra():
    certificate = _refit_certificate()

    certificate["extra"] = True

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_schema():
    certificate = _refit_certificate()

    certificate["schema"] = "wrong"

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_fingerprint():
    certificate = _refit_certificate()

    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_boundary():
    certificate = _refit_certificate()

    certificate["claim_boundary"]["causal_effects_established"] = True

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_diagnostic_schema():
    certificate = _refit_certificate()

    certificate["diagnostic"]["schema"] = "wrong"

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_invalid_spec():
    certificate = _refit_certificate()

    certificate["diagnostic"]["spec"]["n_simulations"] = 1

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_noncanonical_spec():
    certificate = _refit_certificate()

    certificate["diagnostic"]["spec"]["absolute_tail_threshold"] = 2

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_family():
    certificate = _refit_certificate()

    certificate["diagnostic"]["model_family"] = "other"

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_sha():
    certificate = _refit_certificate()

    certificate["diagnostic"]["input_fingerprint_sha256"] = "bad"

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


@pytest.mark.parametrize(
    (
        "n_obs",
        "n_groups",
    ),
    [
        (
            True,
            2,
        ),
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
def test_refit_certificate_counts(
    n_obs,
    n_groups,
):
    certificate = _refit_certificate()

    certificate["diagnostic"]["n_obs"] = n_obs

    certificate["diagnostic"]["n_groups"] = n_groups

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_budget():
    certificate = _refit_certificate()

    certificate["diagnostic"]["spec"]["max_refit_rows"] = 4

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_ledger_fingerprint():
    certificate = _refit_certificate()

    certificate["diagnostic"]["refit_ledger_fingerprint_sha256"] = "0" * 64

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


@pytest.mark.parametrize(
    "summary",
    [
        [],
        None,
    ],
)
def test_refit_certificate_summary_shape(
    summary,
):
    certificate = _refit_certificate()

    certificate["summary"] = summary

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_metric_inventory():
    certificate = _refit_certificate()

    certificate["summary"][0]["metric"] = "other"

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_summary_columns():
    certificate = _refit_certificate()

    certificate["summary"][0]["extra"] = True

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_summary_fingerprint():
    certificate = _refit_certificate()

    certificate["summary"][0]["observed"] += 0.1

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_certificate_diagnostic_fingerprint():
    certificate = _refit_certificate()

    certificate["diagnostic_fingerprint_sha256"] = "0" * 64

    _resign(certificate)

    with pytest.raises(SchemaError):
        refit.validate_location_scale_refit_residual_calibration_certificate(certificate)


def test_refit_freeze(
    tmp_path,
):
    result = _refit_result()

    target = tmp_path / "refit.json"

    written = refit.freeze_location_scale_refit_residual_calibration_certificate(
        result,
        target,
    )

    assert written == target

    with pytest.raises(FileExistsError):
        refit.freeze_location_scale_refit_residual_calibration_certificate(
            result,
            target,
        )

    refit.freeze_location_scale_refit_residual_calibration_certificate(
        result,
        target,
        overwrite=True,
    )


# ============================================================
# HIERARCHICAL BOOTSTRAP SPEC
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        True,
        1,
        10001,
    ],
)
def test_hb_spec_simulations(
    value,
):
    with pytest.raises(ValueError):
        hb.LocationScaleHierarchicalBootstrapSpec(n_simulations=value)


@pytest.mark.parametrize(
    "value",
    [
        True,
        -1,
    ],
)
def test_hb_spec_seed(
    value,
):
    with pytest.raises(ValueError):
        hb.LocationScaleHierarchicalBootstrapSpec(seed=value)


@pytest.mark.parametrize(
    "value",
    [
        0.5,
        1.0,
        np.nan,
        np.inf,
    ],
)
def test_hb_spec_interval(
    value,
):
    with pytest.raises(ValueError):
        hb.LocationScaleHierarchicalBootstrapSpec(interval_level=value)


@pytest.mark.parametrize(
    "value",
    [
        True,
        0,
        -1,
    ],
)
def test_hb_spec_budget(
    value,
):
    with pytest.raises(ValueError):
        hb.LocationScaleHierarchicalBootstrapSpec(max_refit_rows=value)


# ============================================================
# HIERARCHICAL FIXED DESIGN
# ============================================================


def test_hb_fixed_design_valid():
    data = pd.DataFrame(
        {
            "x": [
                1.0,
                2.0,
            ]
        }
    )

    values = hb._fixed_design(
        data,
        ("x",),
        np.asarray(
            [
                1.0,
                2.0,
            ]
        ),
        equation="Location",
    )

    assert values.tolist() == [
        3.0,
        5.0,
    ]


@pytest.mark.parametrize(
    "value",
    [
        "bad",
        np.nan,
        np.inf,
    ],
)
def test_hb_fixed_design_predictor(
    value,
):
    data = pd.DataFrame(
        {
            "x": [
                value,
                1,
            ]
        }
    )

    with pytest.raises(SchemaError):
        hb._fixed_design(
            data,
            ("x",),
            np.asarray(
                [
                    1.0,
                    2.0,
                ]
            ),
            equation="Location",
        )


@pytest.mark.parametrize(
    "coef",
    [
        np.asarray([1.0]),
        np.asarray(
            [
                1.0,
                np.nan,
            ]
        ),
        np.asarray(
            [
                [
                    1.0,
                    2.0,
                ]
            ]
        ),
    ],
)
def test_hb_fixed_design_coefficients(
    coef,
):
    data = pd.DataFrame(
        {
            "x": [
                1.0,
                2.0,
            ]
        }
    )

    with pytest.raises(SchemaError):
        hb._fixed_design(
            data,
            ("x",),
            coef,
            equation="Location",
        )


# ============================================================
# HIERARCHICAL INVENTORY
# ============================================================


@pytest.mark.parametrize(
    "rows",
    [
        None,
        [],
        (),
    ],
)
def test_hb_inventory_empty(
    rows,
):
    with pytest.raises(SchemaError):
        hb._canonical_inventory(rows)


def test_hb_inventory_duplicate():
    rows = [
        {
            "parameter_id": "x",
            "component": "fixed",
            "term": "x",
            "observed": 1.0,
        },
        {
            "parameter_id": "x",
            "component": "fixed",
            "term": "x2",
            "observed": 2.0,
        },
    ]

    with pytest.raises(SchemaError):
        hb._canonical_inventory(rows)


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "parameter_id",
            "",
        ),
        (
            "component",
            "",
        ),
        (
            "term",
            "",
        ),
        (
            "observed",
            True,
        ),
        (
            "observed",
            np.nan,
        ),
    ],
)
def test_hb_inventory_invalid(
    field,
    value,
):
    row = {
        "parameter_id": "x",
        "component": "fixed",
        "term": "x",
        "observed": 1.0,
    }

    row[field] = value

    with pytest.raises(SchemaError):
        hb._canonical_inventory([row])


def test_hb_inventory_extra_field():
    row = {
        "parameter_id": "x",
        "component": "fixed",
        "term": "x",
        "observed": 1.0,
        "extra": True,
    }

    with pytest.raises(SchemaError):
        hb._canonical_inventory([row])


# ============================================================
# HIERARCHICAL PARAMETER ESTIMATES
# ============================================================


def test_hb_parameter_estimates_mapping():
    inventory = _hb_inventory()

    result = hb._canonical_parameter_estimates(
        {
            ("location_fixed::Intercept"): 1,
            ("random_sd::location_intercept"): 0.4,
        },
        parameter_ids=tuple(row["parameter_id"] for row in inventory),
    )

    assert isinstance(
        result[("location_fixed::Intercept")],
        float,
    )


@pytest.mark.parametrize(
    "mapping",
    [
        {},
        {
            ("location_fixed::Intercept"): 1.0,
        },
    ],
)
def test_hb_parameter_estimates_keys(
    mapping,
):
    inventory = _hb_inventory()

    with pytest.raises(SchemaError):
        hb._canonical_parameter_estimates(
            mapping,
            parameter_ids=tuple(row["parameter_id"] for row in inventory),
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        np.nan,
        np.inf,
        "bad",
    ],
)
def test_hb_parameter_estimates_value(
    value,
):
    inventory = _hb_inventory()

    mapping = {
        ("location_fixed::Intercept"): value,
        ("random_sd::location_intercept"): 0.4,
    }

    with pytest.raises(SchemaError):
        hb._canonical_parameter_estimates(
            mapping,
            parameter_ids=tuple(row["parameter_id"] for row in inventory),
        )


# ============================================================
# HIERARCHICAL LEDGER
# ============================================================


def test_hb_ledger_length():
    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            [],
            inventory=_hb_inventory(),
            n_simulations=3,
        )


def test_hb_ledger_index():
    rows = [dict(row) for row in _hb_ledger()]

    rows[0]["simulation_index"] = True

    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            rows,
            inventory=_hb_inventory(),
            n_simulations=3,
        )


@pytest.mark.parametrize(
    "field",
    [
        ("population_random_effects_fingerprint_sha256"),
        ("simulated_input_fingerprint_sha256"),
        ("model_fingerprint_sha256"),
        ("model_certificate_fingerprint_sha256"),
    ],
)
def test_hb_ledger_sha(
    field,
):
    rows = [deepcopy(row) for row in _hb_ledger()]

    rows[0][field] = "bad"

    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            rows,
            inventory=_hb_inventory(),
            n_simulations=3,
        )


def test_hb_ledger_parameter_estimates():
    rows = [deepcopy(row) for row in _hb_ledger()]

    rows[0]["parameter_estimates"][("location_fixed::Intercept")] = np.nan

    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            rows,
            inventory=_hb_inventory(),
            n_simulations=3,
        )


# ============================================================
# HIERARCHICAL SUMMARY
# ============================================================


def test_hb_summary_valid():
    summary = hb._bootstrap_summary(
        _hb_inventory(),
        _hb_ledger(),
        interval_level=0.90,
    )

    assert tuple(summary.columns) == hb._SUMMARY_COLUMNS

    assert len(summary) == 2


def test_hb_summary_too_few_replicates():
    inventory = _hb_inventory()

    row = deepcopy(_hb_ledger()[0])

    with pytest.raises(SchemaError):
        hb._bootstrap_summary(
            inventory,
            (row,),
            interval_level=0.90,
        )


def test_hb_summary_nonfinite_replicate():
    inventory = _hb_inventory()

    ledger = [deepcopy(row) for row in _hb_ledger()]

    ledger[0]["parameter_estimates"][("location_fixed::Intercept")] = np.nan

    with pytest.raises(SchemaError):
        hb._bootstrap_summary(
            inventory,
            tuple(ledger),
            interval_level=0.90,
        )


def test_hb_summary_fingerprint_type():
    with pytest.raises(TypeError):
        hb._summary_fingerprint([])


def test_hb_summary_fingerprint_columns():
    summary = hb._bootstrap_summary(
        _hb_inventory(),
        _hb_ledger(),
        interval_level=0.90,
    )

    summary["extra"] = True

    with pytest.raises(SchemaError):
        hb._summary_fingerprint(summary)


# ============================================================
# BOOTSTRAP ORCHESTRATION WITHOUT OPTIMIZER
# ============================================================


def _patch_hb_orchestration(
    monkeypatch,
    *,
    fail_refit=False,
    lineage_mismatch=False,
):
    model_spec = SimpleNamespace(
        outcome_col="y",
        group_col="g",
        location_predictors=(),
        scale_predictors=(),
    )

    base = SimpleNamespace(
        spec=model_spec,
        model_fingerprint_sha256=SHA_E,
    )

    inventory = _hb_inventory()

    monkeypatch.setattr(
        hb,
        "_model_adapter",
        lambda result: (
            "independent_location_scale",
            model_spec,
            None,
        ),
    )

    monkeypatch.setattr(
        hb,
        "_require_certifiable_base_model",
        lambda result: SHA_F,
    )

    monkeypatch.setattr(
        hb,
        "_require_exact_fitting_input",
        lambda result, data: SHA_A,
    )

    monkeypatch.setattr(
        hb,
        "_parameter_inventory",
        lambda result: inventory,
    )

    monkeypatch.setattr(
        hb,
        "_input_columns",
        lambda spec: [
            "y",
            "g",
        ],
    )

    def simulate(
        result,
        data,
        *,
        rng,
    ):
        simulated = data.copy(deep=True)

        simulated["y"] = simulated["y"].to_numpy(dtype=float) + rng.normal(
            scale=0.01,
            size=len(simulated),
        )

        return (
            simulated,
            SHA_B,
        )

    monkeypatch.setattr(
        hb,
        "_simulate_hierarchical_outcome",
        simulate,
    )

    def fake_fit(
        data,
        *,
        spec,
    ):
        if fail_refit:
            raise RuntimeError("synthetic refit failure")

        current = hb.fingerprint_frame(
            data.loc[
                :,
                [
                    "y",
                    "g",
                ],
            ]
        )

        return SimpleNamespace(
            spec=spec,
            model_fingerprint_sha256=SHA_C,
            input_fingerprint_sha256=("0" * 64 if lineage_mismatch else current),
        )

    monkeypatch.setattr(
        hb,
        "_fit_function_for_result",
        lambda result: fake_fit,
    )

    monkeypatch.setattr(
        hb,
        "_parameter_estimates",
        lambda result: {
            ("location_fixed::Intercept"): 1.0,
            ("random_sd::location_intercept"): 0.4,
        },
    )

    return base


def _small_hb_data():
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
                1.1,
                0.9,
                1.2,
            ],
        }
    )


def test_hb_orchestration_budget(
    monkeypatch,
):
    base = _patch_hb_orchestration(monkeypatch)

    with pytest.raises(SchemaError):
        hb.bootstrap_location_scale_hierarchy(
            base,
            _small_hb_data(),
            spec=(
                hb.LocationScaleHierarchicalBootstrapSpec(
                    n_simulations=2,
                    max_refit_rows=4,
                )
            ),
        )


def test_hb_orchestration_missing_group(
    monkeypatch,
):
    base = _patch_hb_orchestration(monkeypatch)

    data = _small_hb_data()

    data.loc[
        0,
        "g",
    ] = None

    with pytest.raises(SchemaError):
        hb.bootstrap_location_scale_hierarchy(
            base,
            data,
            spec=(
                hb.LocationScaleHierarchicalBootstrapSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_hb_orchestration_one_group(
    monkeypatch,
):
    base = _patch_hb_orchestration(monkeypatch)

    data = _small_hb_data()

    data["g"] = "a"

    with pytest.raises(SchemaError):
        hb.bootstrap_location_scale_hierarchy(
            base,
            data,
            spec=(
                hb.LocationScaleHierarchicalBootstrapSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_hb_orchestration_refit_failure(
    monkeypatch,
):
    base = _patch_hb_orchestration(
        monkeypatch,
        fail_refit=True,
    )

    with pytest.raises(SchemaError):
        hb.bootstrap_location_scale_hierarchy(
            base,
            _small_hb_data(),
            spec=(
                hb.LocationScaleHierarchicalBootstrapSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_hb_orchestration_lineage_failure(
    monkeypatch,
):
    base = _patch_hb_orchestration(
        monkeypatch,
        lineage_mismatch=True,
    )

    with pytest.raises(SchemaError):
        hb.bootstrap_location_scale_hierarchy(
            base,
            _small_hb_data(),
            spec=(
                hb.LocationScaleHierarchicalBootstrapSpec(
                    n_simulations=2,
                    max_refit_rows=100,
                )
            ),
        )


def test_hb_orchestration_success(
    monkeypatch,
):
    base = _patch_hb_orchestration(monkeypatch)

    result = hb.bootstrap_location_scale_hierarchy(
        base,
        _small_hb_data(),
        spec=(
            hb.LocationScaleHierarchicalBootstrapSpec(
                n_simulations=2,
                seed=19,
                interval_level=0.9,
                max_refit_rows=100,
            )
        ),
    )

    assert result.n_groups == 2

    assert len(result.refit_ledger) == 2

    assert len(result.bootstrap_fingerprint_sha256) == 64


# ============================================================
# HIERARCHICAL RESULT IDENTITY
# ============================================================


def test_hb_result_type():
    with pytest.raises(TypeError):
        hb._validate_result_identity(object())


def test_hb_result_family():
    result = replace(
        _hb_result(),
        model_family="other",
    )

    with pytest.raises(SchemaError):
        hb._validate_result_identity(result)


@pytest.mark.parametrize(
    "field",
    [
        "model_fingerprint_sha256",
        ("base_model_certificate_fingerprint_sha256"),
        "input_fingerprint_sha256",
        ("refit_ledger_fingerprint_sha256"),
        ("summary_fingerprint_sha256"),
        ("bootstrap_fingerprint_sha256"),
    ],
)
def test_hb_result_sha(
    field,
):
    result = replace(
        _hb_result(),
        **{field: "bad"},
    )

    with pytest.raises(SchemaError):
        hb._validate_result_identity(result)


def test_hb_result_counts():
    result = replace(
        _hb_result(),
        n_groups=1,
    )

    with pytest.raises(SchemaError):
        hb._validate_result_identity(result)


def test_hb_result_budget():
    result = replace(
        _hb_result(),
        spec=(
            hb.LocationScaleHierarchicalBootstrapSpec(
                n_simulations=3,
                max_refit_rows=10,
            )
        ),
    )

    with pytest.raises(SchemaError):
        hb._validate_result_identity(result)


def test_hb_result_ledger_mutation():
    result = replace(
        _hb_result(),
        refit_ledger_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        hb._validate_result_identity(result)


def test_hb_result_summary_mutation():
    result = _hb_result()

    changed = result.summary.copy()

    changed.loc[
        0,
        "bootstrap_mean",
    ] += 0.1

    result = replace(
        result,
        summary=changed,
    )

    with pytest.raises(SchemaError):
        hb._validate_result_identity(result)


def test_hb_result_fingerprint_mutation():
    result = replace(
        _hb_result(),
        bootstrap_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        hb._validate_result_identity(result)


def test_hb_accessors_defensive():
    result = _hb_result()

    summary = result.parameters()

    replicates = result.replicates()

    summary.loc[
        0,
        "observed",
    ] += 10

    replicates.loc[
        0,
        ("location_fixed::Intercept"),
    ] += 10

    assert (
        result.summary.loc[
            0,
            "observed",
        ]
        != summary.loc[
            0,
            "observed",
        ]
    )


# ============================================================
# HIERARCHICAL CERTIFICATE
# ============================================================


def _hb_certificate():
    return hb.build_location_scale_hierarchical_bootstrap_certificate(_hb_result())


def test_hb_certificate_roundtrip():
    certificate = _hb_certificate()

    hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_type():
    with pytest.raises(TypeError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate([])


def test_hb_certificate_schema():
    certificate = _hb_certificate()

    certificate["schema"] = "wrong"

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_fingerprint():
    certificate = _hb_certificate()

    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_boundary():
    certificate = _hb_certificate()

    certificate["claim_boundary"]["causal_effects_established"] = True

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_bootstrap_schema():
    certificate = _hb_certificate()

    certificate["bootstrap"]["schema"] = "wrong"

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_invalid_spec():
    certificate = _hb_certificate()

    certificate["bootstrap"]["spec"]["n_simulations"] = 1

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_family():
    certificate = _hb_certificate()

    certificate["bootstrap"]["model_family"] = "other"

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_sha():
    certificate = _hb_certificate()

    certificate["bootstrap"]["input_fingerprint_sha256"] = "bad"

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_counts():
    certificate = _hb_certificate()

    certificate["bootstrap"]["n_groups"] = 1

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_ledger_fingerprint():
    certificate = _hb_certificate()

    certificate["bootstrap"]["refit_ledger_fingerprint_sha256"] = "0" * 64

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_summary_length():
    certificate = _hb_certificate()

    certificate["summary"] = []

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_summary_schema():
    certificate = _hb_certificate()

    certificate["summary"][0]["extra"] = True

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_summary_inconsistent():
    certificate = _hb_certificate()

    certificate["summary"][0]["bootstrap_mean"] += 0.1

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_certificate_identity_fingerprint():
    certificate = _hb_certificate()

    certificate["bootstrap_fingerprint_sha256"] = "0" * 64

    _resign(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_hb_freeze(
    tmp_path,
):
    result = _hb_result()

    target = tmp_path / "bootstrap.json"

    assert (
        hb.freeze_location_scale_hierarchical_bootstrap_certificate(
            result,
            target,
        )
        == target
    )

    with pytest.raises(FileExistsError):
        hb.freeze_location_scale_hierarchical_bootstrap_certificate(
            result,
            target,
        )

    hb.freeze_location_scale_hierarchical_bootstrap_certificate(
        result,
        target,
        overwrite=True,
    )


# ============================================================
# MONTE CARLO BASIC HELPERS
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        0.5,
        1.0,
        np.nan,
        np.inf,
    ],
)
def test_mc_spec_invalid(
    value,
):
    with pytest.raises(ValueError):
        mc.LocationScaleBootstrapMonteCarloSpec(confidence_level=value)


def test_mc_spec_float_normalization():
    spec = mc.LocationScaleBootstrapMonteCarloSpec(confidence_level=np.float64(0.9))

    assert isinstance(
        spec.confidence_level,
        float,
    )


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            SHA_A,
            True,
        ),
        (
            "A" * 64,
            False,
        ),
        (
            "a" * 63,
            False,
        ),
        (
            None,
            False,
        ),
    ],
)
def test_mc_sha(
    value,
    expected,
):
    assert mc._is_sha256_hex(value) is expected


def test_mc_jackknife_small():
    with pytest.raises(SchemaError):
        mc._jackknife_sd_mcse(
            np.asarray(
                [
                    1.0,
                    2.0,
                ]
            )
        )


def test_mc_jackknife_nonfinite():
    with pytest.raises(SchemaError):
        mc._jackknife_sd_mcse(
            np.asarray(
                [
                    1.0,
                    np.nan,
                    3.0,
                ]
            )
        )


def test_mc_jackknife_constant():
    value = mc._jackknife_sd_mcse(
        np.asarray(
            [
                1.0,
                1.0,
                1.0,
                1.0,
            ]
        )
    )

    assert value == pytest.approx(0.0)


def test_mc_quantile_empty():
    with pytest.raises(SchemaError):
        mc._order_statistic_quantile_band(
            np.asarray([]),
            probability=0.1,
            confidence_level=0.9,
        )


def test_mc_quantile_nonfinite():
    with pytest.raises(SchemaError):
        mc._order_statistic_quantile_band(
            np.asarray(
                [
                    1.0,
                    np.nan,
                ]
            ),
            probability=0.1,
            confidence_level=0.9,
        )


@pytest.mark.parametrize(
    "probability",
    [
        0,
        1,
        -0.1,
        1.1,
    ],
)
def test_mc_quantile_probability(
    probability,
):
    with pytest.raises(ValueError):
        mc._order_statistic_quantile_band(
            np.arange(
                20,
                dtype=float,
            ),
            probability=probability,
            confidence_level=0.9,
        )


def test_mc_quantile_valid():
    result = mc._order_statistic_quantile_band(
        np.arange(
            100,
            dtype=float,
        ),
        probability=0.5,
        confidence_level=0.9,
    )

    assert result["rank_lower"] <= result["rank_upper"]

    assert result["binomial_coverage"] >= 0.9


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            None,
            None,
        ),
        (
            1,
            1.0,
        ),
        (
            1.25,
            1.25,
        ),
    ],
)
def test_mc_optional_float_valid(
    value,
    expected,
):
    assert (
        mc._canonical_optional_float(
            value,
            context="fixture",
        )
        == expected
    )


@pytest.mark.parametrize(
    "value",
    [
        True,
        "bad",
        np.nan,
        np.inf,
    ],
)
def test_mc_optional_float_invalid(
    value,
):
    with pytest.raises(SchemaError):
        mc._canonical_optional_float(
            value,
            context="fixture",
        )


# ============================================================
# MONTE CARLO ASSESSMENT
# ============================================================


def _mc_result():
    return mc.assess_location_scale_bootstrap_monte_carlo(
        _hb_result(n_simulations=3),
        spec=(mc.LocationScaleBootstrapMonteCarloSpec(confidence_level=0.90)),
    )


def test_mc_assess_type():
    with pytest.raises(TypeError):
        mc.assess_location_scale_bootstrap_monte_carlo(object())


def test_mc_assessment_real_calculations():
    result = _mc_result()

    assert result.n_simulations == 3

    assert len(result.diagnostics) == 2

    frame = result.parameters()

    assert np.isfinite(
        frame[
            [
                "bootstrap_mean",
                "bootstrap_se",
                "mean_mcse",
            ]
        ].to_numpy(dtype=float)
    ).all()


# ============================================================
# MONTE CARLO DIAGNOSTIC CANONICALIZATION
# ============================================================


def test_mc_diagnostics_length():
    result = _mc_result()

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            [],
            n_simulations=(result.n_simulations),
            parameter_ids=(result.parameter_ids),
        )


def test_mc_diagnostics_identity():
    result = _mc_result()

    rows = [deepcopy(row) for row in result.diagnostics]

    rows[0]["parameter_id"] = "other"

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            rows,
            n_simulations=(result.n_simulations),
            parameter_ids=(result.parameter_ids),
        )


def test_mc_diagnostics_simulation_count():
    result = _mc_result()

    rows = [deepcopy(row) for row in result.diagnostics]

    rows[0]["n_simulations"] += 1

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            rows,
            n_simulations=(result.n_simulations),
            parameter_ids=(result.parameter_ids),
        )


@pytest.mark.parametrize(
    "field",
    [
        "bootstrap_mean",
        "bootstrap_se",
        "mean_mcse",
        ("bootstrap_se_mcse_jackknife"),
        "interval_lower",
        ("interval_lower_probability"),
        ("interval_lower_mc_binomial_coverage"),
        "interval_upper",
        ("interval_upper_probability"),
        ("interval_upper_mc_binomial_coverage"),
    ],
)
def test_mc_diagnostics_numeric(
    field,
):
    result = _mc_result()

    rows = [deepcopy(row) for row in result.diagnostics]

    rows[0][field] = np.nan

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            rows,
            n_simulations=(result.n_simulations),
            parameter_ids=(result.parameter_ids),
        )


@pytest.mark.parametrize(
    "field",
    [
        ("interval_lower_mc_rank_lower"),
        ("interval_lower_mc_rank_upper"),
        ("interval_upper_mc_rank_lower"),
        ("interval_upper_mc_rank_upper"),
    ],
)
def test_mc_diagnostics_rank(
    field,
):
    result = _mc_result()

    rows = [deepcopy(row) for row in result.diagnostics]

    rows[0][field] = -1

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            rows,
            n_simulations=(result.n_simulations),
            parameter_ids=(result.parameter_ids),
        )


@pytest.mark.parametrize(
    "field",
    [
        ("interval_lower_mc_band_lower"),
        ("interval_lower_mc_band_upper"),
        ("interval_upper_mc_band_lower"),
        ("interval_upper_mc_band_upper"),
    ],
)
def test_mc_diagnostics_optional(
    field,
):
    result = _mc_result()

    rows = [deepcopy(row) for row in result.diagnostics]

    rows[0][field] = "bad"

    with pytest.raises(SchemaError):
        mc._canonical_diagnostics(
            rows,
            n_simulations=(result.n_simulations),
            parameter_ids=(result.parameter_ids),
        )


# ============================================================
# MONTE CARLO RESULT IDENTITY
# ============================================================


def test_mc_result_type():
    with pytest.raises(TypeError):
        mc._validate_result_identity(object())


def test_mc_source_json_invalid():
    result = replace(
        _mc_result(),
        source_bootstrap_certificate_json="{",
    )

    with pytest.raises(SchemaError):
        mc._source_certificate_from_result(result)


def test_mc_source_lineage():
    result = replace(
        _mc_result(),
        source_bootstrap_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        mc._source_certificate_from_result(result)


def test_mc_result_diagnostics_mutation():
    result = _mc_result()

    rows = [deepcopy(row) for row in result.diagnostics]

    rows[0]["mean_mcse"] += 0.1

    result = replace(
        result,
        diagnostics=tuple(rows),
    )

    with pytest.raises(SchemaError):
        mc._validate_result_identity(result)


def test_mc_result_diagnostics_fingerprint():
    result = replace(
        _mc_result(),
        diagnostics_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        mc._validate_result_identity(result)


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "model_family",
            "other",
        ),
        (
            "bootstrap_interval_level",
            0.8,
        ),
        (
            "n_simulations",
            99,
        ),
        (
            "parameter_ids",
            ("other",),
        ),
    ],
)
def test_mc_result_identity_fields(
    field,
    value,
):
    result = replace(
        _mc_result(),
        **{field: value},
    )

    with pytest.raises(SchemaError):
        mc._validate_result_identity(result)


def test_mc_result_bad_assessment_sha():
    result = replace(
        _mc_result(),
        assessment_fingerprint_sha256=("bad"),
    )

    with pytest.raises(SchemaError):
        mc._validate_result_identity(result)


def test_mc_result_assessment_mismatch():
    result = replace(
        _mc_result(),
        assessment_fingerprint_sha256=("0" * 64),
    )

    with pytest.raises(SchemaError):
        mc._validate_result_identity(result)


# ============================================================
# MONTE CARLO CERTIFICATE
# ============================================================


def _mc_certificate():
    return mc.build_location_scale_bootstrap_monte_carlo_certificate(_mc_result())


def test_mc_certificate_roundtrip():
    certificate = _mc_certificate()

    mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_type():
    with pytest.raises(TypeError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate([])


def test_mc_certificate_schema():
    certificate = _mc_certificate()

    certificate["schema"] = "wrong"

    _resign(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_fingerprint():
    certificate = _mc_certificate()

    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_boundary():
    certificate = _mc_certificate()

    certificate["claim_boundary"]["causal_effects_established"] = True

    _resign(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_assessment_schema():
    certificate = _mc_certificate()

    certificate["assessment"]["schema"] = "wrong"

    _resign(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_invalid_spec():
    certificate = _mc_certificate()

    certificate["assessment"]["spec"]["confidence_level"] = 1.0

    _resign(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_diagnostics():
    certificate = _mc_certificate()

    certificate["diagnostics"][0]["mean_mcse"] += 0.1

    _resign(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_assessment_identity():
    certificate = _mc_certificate()

    certificate["assessment"]["model_family"] = "other"

    _resign(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_certificate_assessment_fingerprint():
    certificate = _mc_certificate()

    certificate["assessment_fingerprint_sha256"] = "0" * 64

    _resign(certificate)

    with pytest.raises(SchemaError):
        mc.validate_location_scale_bootstrap_monte_carlo_certificate(certificate)


def test_mc_freeze(
    tmp_path,
):
    result = _mc_result()

    target = tmp_path / "monte-carlo.json"

    assert (
        mc.freeze_location_scale_bootstrap_monte_carlo_certificate(
            result,
            target,
        )
        == target
    )

    with pytest.raises(FileExistsError):
        mc.freeze_location_scale_bootstrap_monte_carlo_certificate(
            result,
            target,
        )

    mc.freeze_location_scale_bootstrap_monte_carlo_certificate(
        result,
        target,
        overwrite=True,
    )
