from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest
from test_synthetic_surface import (
    base_spec,
    identity_estimator,
    two_noise_surface,
)

import gazeforge._location_scale_hierarchical_bootstrap_core as hb
import gazeforge.synthetic_surface as surface
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError

# =====================================================================
# HIERARCHICAL BOOTSTRAP CORE
# =====================================================================


def _inventory():
    return hb._canonical_inventory(
        [
            {
                "parameter_id": "location_fixed::Intercept",
                "component": "location_fixed",
                "term": "Intercept",
                "observed": 1.0,
            },
            {
                "parameter_id": "random_sd::location_intercept",
                "component": "random_sd",
                "term": "location_intercept",
                "observed": 0.5,
            },
        ]
    )


def _ledger(inventory=None):
    inventory = inventory or _inventory()

    rows = [
        {
            "simulation_index": 0,
            "population_random_effects_fingerprint_sha256": "1" * 64,
            "simulated_input_fingerprint_sha256": "2" * 64,
            "model_fingerprint_sha256": "3" * 64,
            "model_certificate_fingerprint_sha256": "4" * 64,
            "parameter_estimates": {
                "location_fixed::Intercept": 0.9,
                "random_sd::location_intercept": 0.45,
            },
        },
        {
            "simulation_index": 1,
            "population_random_effects_fingerprint_sha256": "5" * 64,
            "simulated_input_fingerprint_sha256": "6" * 64,
            "model_fingerprint_sha256": "7" * 64,
            "model_certificate_fingerprint_sha256": "8" * 64,
            "parameter_estimates": {
                "location_fixed::Intercept": 1.1,
                "random_sd::location_intercept": 0.55,
            },
        },
    ]

    return hb._canonical_refit_ledger(
        rows,
        inventory=inventory,
        n_simulations=2,
    )


def _bootstrap_certificate():
    spec = hb.LocationScaleHierarchicalBootstrapSpec(
        n_simulations=2,
        seed=11,
        interval_level=0.95,
        max_refit_rows=100,
    )

    inventory = _inventory()
    ledger = _ledger(inventory)

    ledger_fingerprint = benchmark_fingerprint(list(ledger))

    summary = hb._bootstrap_summary(
        inventory,
        ledger,
        interval_level=spec.interval_level,
    )

    summary_fingerprint = hb._summary_fingerprint(summary)

    identity = hb._bootstrap_identity_payload(
        spec=spec,
        model_family="independent_location_scale",
        model_fingerprint="a" * 64,
        base_model_certificate_fingerprint="b" * 64,
        input_fingerprint="c" * 64,
        n_obs=4,
        n_groups=2,
        parameter_inventory=inventory,
        refit_ledger_fingerprint=ledger_fingerprint,
        summary_fingerprint=summary_fingerprint,
    )

    body = {
        "schema": hb._CERTIFICATE_SCHEMA,
        "bootstrap": identity,
        "bootstrap_fingerprint_sha256": benchmark_fingerprint(identity),
        "summary": summary.to_dict(orient="records"),
        "refit_ledger": [dict(row) for row in ledger],
        "claim_boundary": dict(hb._CLAIM_BOUNDARY),
    }

    return {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }


def _resign_bootstrap_certificate(
    certificate,
    *,
    refresh_bootstrap=True,
):
    if refresh_bootstrap:
        certificate["bootstrap_fingerprint_sha256"] = benchmark_fingerprint(
            certificate["bootstrap"]
        )

    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }

    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_bootstrap_valid_synthetic_certificate():
    hb.validate_location_scale_hierarchical_bootstrap_certificate(_bootstrap_certificate())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n_simulations", True),
        ("n_simulations", 1),
        ("n_simulations", 10001),
        ("seed", True),
        ("seed", -1),
        ("interval_level", 0.5),
        ("interval_level", 1.0),
        ("interval_level", np.nan),
        ("max_refit_rows", True),
        ("max_refit_rows", 0),
    ],
)
def test_bootstrap_spec_guards(
    field,
    value,
):
    kwargs = {
        "n_simulations": 2,
        "seed": 1,
        "interval_level": 0.95,
        "max_refit_rows": 100,
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        hb.LocationScaleHierarchicalBootstrapSpec(**kwargs)


def test_bootstrap_fixed_design_valid():
    frame = pd.DataFrame(
        {
            "x": [1.0, 2.0],
        }
    )

    result = hb._fixed_design(
        frame,
        ("x",),
        np.array([1.0, 2.0]),
        equation="Location",
    )

    np.testing.assert_allclose(
        result,
        [3.0, 5.0],
    )


def test_bootstrap_fixed_design_rejects_bad_predictor():
    frame = pd.DataFrame(
        {
            "x": [1.0, np.nan],
        }
    )

    with pytest.raises(SchemaError):
        hb._fixed_design(
            frame,
            ("x",),
            np.array([1.0, 2.0]),
            equation="Location",
        )


@pytest.mark.parametrize(
    "coef",
    [
        np.array([[1.0, 2.0]]),
        np.array([1.0]),
        np.array([1.0, np.nan]),
    ],
)
def test_bootstrap_fixed_design_rejects_bad_coefficients(
    coef,
):
    frame = pd.DataFrame(
        {
            "x": [1.0, 2.0],
        }
    )

    with pytest.raises(SchemaError):
        hb._fixed_design(
            frame,
            ("x",),
            coef,
            equation="Location",
        )


def test_bootstrap_fixed_design_rejects_nonfinite_surface():
    frame = pd.DataFrame(
        {
            "x": [1e308],
        }
    )

    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(SchemaError):
            hb._fixed_design(
                frame,
                ("x",),
                np.array(
                    [
                        1e308,
                        1e308,
                    ]
                ),
                equation="Location",
            )


@pytest.mark.parametrize(
    "rows",
    [
        None,
        [],
        "wrong",
    ],
)
def test_bootstrap_inventory_requires_nonempty_sequence(
    rows,
):
    with pytest.raises(SchemaError):
        hb._canonical_inventory(rows)


def test_bootstrap_inventory_exact_schema():
    with pytest.raises(SchemaError):
        hb._canonical_inventory(
            [
                {
                    "parameter_id": "p",
                    "component": "c",
                    "term": "t",
                    "observed": 1.0,
                    "extra": True,
                }
            ]
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("parameter_id", ""),
        ("component", ""),
        ("term", ""),
        ("observed", True),
        ("observed", np.nan),
    ],
)
def test_bootstrap_inventory_value_guards(
    field,
    value,
):
    row = {
        "parameter_id": "p",
        "component": "c",
        "term": "t",
        "observed": 1.0,
    }

    row[field] = value

    with pytest.raises(SchemaError):
        hb._canonical_inventory([row])


def test_bootstrap_inventory_duplicate_parameter_id():
    row = {
        "parameter_id": "p",
        "component": "c",
        "term": "t",
        "observed": 1.0,
    }

    with pytest.raises(SchemaError):
        hb._canonical_inventory(
            [
                row,
                dict(row),
            ]
        )


def test_bootstrap_population_effects_need_two_groups():
    with pytest.raises(SchemaError):
        hb._draw_population_effects(
            object(),
            ("P1",),
            np.random.default_rng(1),
        )


def test_bootstrap_population_effects_reject_unsupported_result():
    with pytest.raises(TypeError):
        hb._draw_population_effects(
            object(),
            (
                "P1",
                "P2",
            ),
            np.random.default_rng(1),
        )


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"wrong": 1.0},
    ],
)
def test_bootstrap_parameter_estimate_mapping_contract(
    raw,
):
    with pytest.raises(SchemaError):
        hb._canonical_parameter_estimates(
            raw,
            parameter_ids=("p",),
        )


@pytest.mark.parametrize(
    "value",
    [
        True,
        np.nan,
        np.inf,
    ],
)
def test_bootstrap_parameter_estimates_finite(
    value,
):
    with pytest.raises(SchemaError):
        hb._canonical_parameter_estimates(
            {"p": value},
            parameter_ids=("p",),
        )


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [1],
        [1, 2, 3],
    ],
)
def test_bootstrap_ledger_requires_exact_length(
    rows,
):
    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            rows,
            inventory=_inventory(),
            n_simulations=2,
        )


def test_bootstrap_ledger_exact_schema():
    row = {
        "simulation_index": 0,
        "population_random_effects_fingerprint_sha256": "1" * 64,
        "simulated_input_fingerprint_sha256": "2" * 64,
        "model_fingerprint_sha256": "3" * 64,
        "model_certificate_fingerprint_sha256": "4" * 64,
        "parameter_estimates": {
            "location_fixed::Intercept": 1.0,
            "random_sd::location_intercept": 0.5,
        },
        "extra": True,
    }

    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            [
                row,
                {
                    **row,
                    "simulation_index": 1,
                },
            ],
            inventory=_inventory(),
            n_simulations=2,
        )


@pytest.mark.parametrize(
    "index",
    [
        True,
        1,
        -1,
    ],
)
def test_bootstrap_ledger_index_guard(index):
    ledger = [dict(row) for row in _ledger()]

    ledger[0]["simulation_index"] = index

    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            ledger,
            inventory=_inventory(),
            n_simulations=2,
        )


@pytest.mark.parametrize(
    "field",
    [
        "population_random_effects_fingerprint_sha256",
        "simulated_input_fingerprint_sha256",
        "model_fingerprint_sha256",
        "model_certificate_fingerprint_sha256",
    ],
)
def test_bootstrap_ledger_digest_guard(field):
    ledger = [dict(row) for row in _ledger()]

    ledger[0][field] = "bad"

    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            ledger,
            inventory=_inventory(),
            n_simulations=2,
        )


def test_bootstrap_ledger_parameter_mapping_guard():
    ledger = [dict(row) for row in _ledger()]

    ledger[0]["parameter_estimates"] = {
        "wrong": 1.0,
    }

    with pytest.raises(SchemaError):
        hb._canonical_refit_ledger(
            ledger,
            inventory=_inventory(),
            n_simulations=2,
        )


def test_bootstrap_summary_rejects_too_few_replicates():
    inventory = _inventory()

    ledger = (
        {
            "parameter_estimates": {
                "location_fixed::Intercept": 1.0,
                "random_sd::location_intercept": 0.5,
            }
        },
    )

    with pytest.raises(SchemaError):
        hb._bootstrap_summary(
            inventory,
            ledger,
            interval_level=0.95,
        )


def test_bootstrap_summary_rejects_nonfinite_replicates():
    inventory = _inventory()

    ledger = (
        {
            "parameter_estimates": {
                "location_fixed::Intercept": np.nan,
                "random_sd::location_intercept": 0.5,
            }
        },
        {
            "parameter_estimates": {
                "location_fixed::Intercept": 1.0,
                "random_sd::location_intercept": 0.5,
            }
        },
    )

    with pytest.raises(SchemaError):
        hb._bootstrap_summary(
            inventory,
            ledger,
            interval_level=0.95,
        )


def test_bootstrap_summary_fingerprint_type_guard():
    with pytest.raises(TypeError):
        hb._summary_fingerprint(object())


def test_bootstrap_summary_fingerprint_column_guard():
    with pytest.raises(SchemaError):
        hb._summary_fingerprint(
            pd.DataFrame(
                {
                    "wrong": [1],
                }
            )
        )


def test_bootstrap_certificate_requires_dictionary():
    with pytest.raises(TypeError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate([])


def test_bootstrap_certificate_exact_top_level_schema():
    certificate = _bootstrap_certificate()
    certificate["extra"] = True

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_schema_guard():
    certificate = _bootstrap_certificate()
    certificate["schema"] = "wrong"
    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_fingerprint_guard():
    certificate = _bootstrap_certificate()
    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_claim_boundary_guard():
    certificate = _bootstrap_certificate()

    certificate["claim_boundary"]["causal_effects_established"] = True

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_identity_exact_schema():
    certificate = _bootstrap_certificate()
    certificate["bootstrap"]["extra"] = True

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_identity_schema_guard():
    certificate = _bootstrap_certificate()
    certificate["bootstrap"]["schema"] = "wrong"

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_identity_invalid_spec():
    certificate = _bootstrap_certificate()
    certificate["bootstrap"]["spec"]["n_simulations"] = 1

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_identity_model_family_guard():
    certificate = _bootstrap_certificate()
    certificate["bootstrap"]["model_family"] = "unsupported"

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


@pytest.mark.parametrize(
    "field",
    [
        "model_fingerprint_sha256",
        "base_model_certificate_fingerprint_sha256",
        "input_fingerprint_sha256",
        "refit_ledger_fingerprint_sha256",
        "summary_fingerprint_sha256",
    ],
)
def test_bootstrap_identity_digest_guards(
    field,
):
    certificate = _bootstrap_certificate()
    certificate["bootstrap"][field] = "bad"

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


@pytest.mark.parametrize(
    ("n_obs", "n_groups"),
    [
        (True, 2),
        (4, True),
        (1, 1),
        (4, 1),
        (2, 3),
    ],
)
def test_bootstrap_identity_count_guards(
    n_obs,
    n_groups,
):
    certificate = _bootstrap_certificate()

    certificate["bootstrap"]["n_obs"] = n_obs

    certificate["bootstrap"]["n_groups"] = n_groups

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_identity_resource_budget_guard():
    certificate = _bootstrap_certificate()

    certificate["bootstrap"]["n_obs"] = 60

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_inventory_guard():
    certificate = _bootstrap_certificate()

    certificate["bootstrap"]["parameter_inventory"] = []

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_ledger_length_guard():
    certificate = _bootstrap_certificate()

    certificate["refit_ledger"] = certificate["refit_ledger"][:1]

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_ledger_fingerprint_guard():
    certificate = _bootstrap_certificate()

    certificate["bootstrap"]["refit_ledger_fingerprint_sha256"] = "f" * 64

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_summary_requires_list():
    certificate = _bootstrap_certificate()

    certificate["summary"] = {}

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_summary_length_guard():
    certificate = _bootstrap_certificate()

    certificate["summary"] = certificate["summary"][:1]

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_summary_schema_guard():
    certificate = _bootstrap_certificate()

    certificate["summary"][0]["extra"] = True

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_summary_consistency_guard():
    certificate = _bootstrap_certificate()

    certificate["summary"][0]["bootstrap_mean"] += 1.0

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_certificate_summary_fingerprint_guard():
    certificate = _bootstrap_certificate()

    certificate["bootstrap"]["summary_fingerprint_sha256"] = "e" * 64

    _resign_bootstrap_certificate(certificate)

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


def test_bootstrap_identity_fingerprint_guard():
    certificate = _bootstrap_certificate()

    certificate["bootstrap_fingerprint_sha256"] = "d" * 64

    _resign_bootstrap_certificate(
        certificate,
        refresh_bootstrap=False,
    )

    with pytest.raises(SchemaError):
        hb.validate_location_scale_hierarchical_bootstrap_certificate(certificate)


# =====================================================================
# SYNTHETIC SURFACE
# =====================================================================


@pytest.fixture(scope="module")
def synthetic_certificate():
    result = surface.evaluate_synthetic_recovery_surface(
        two_noise_surface(),
        identity_estimator,
        estimator_name="identity-observation-baseline",
        thresholds={
            "coordinate_rmse_px": 30.0,
        },
    )

    return result.surface_certificate


def _surface_copy(certificate):
    return copy.deepcopy(certificate)


def _resign_surface(certificate):
    body = {key: value for key, value in certificate.items() if key != "surface_fingerprint_sha256"}

    certificate["surface_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_surface_float_axis_fallback():
    assert surface._float_axis(
        None,
        1.5,
        name="demo",
    ) == (1.5,)


@pytest.mark.parametrize(
    "values",
    [
        (),
        [],
    ],
)
def test_surface_float_axis_nonempty(values):
    with pytest.raises(ValueError):
        surface._float_axis(
            values,
            1.0,
            name="demo",
        )


@pytest.mark.parametrize(
    "value",
    [
        np.nan,
        np.inf,
    ],
)
def test_surface_float_axis_finite(value):
    with pytest.raises(ValueError):
        surface._float_axis(
            [value],
            1.0,
            name="demo",
        )


def test_surface_integer_axis_fallback():
    assert surface._integer_axis(
        None,
        3,
        name="demo",
    ) == (3,)


def test_surface_integer_axis_nonempty():
    with pytest.raises(ValueError):
        surface._integer_axis(
            [],
            1,
            name="demo",
        )


def test_surface_integer_axis_integer_guard():
    with pytest.raises(ValueError):
        surface._integer_axis(
            [1.5],
            1,
            name="demo",
        )


def test_surface_bias_axis_fallback():
    assert surface._bias_axis(
        None,
        (0.0, 0.0),
    ) == ((0.0, 0.0),)


def test_surface_bias_axis_nonempty():
    with pytest.raises(ValueError):
        surface._bias_axis(
            [],
            (0.0, 0.0),
        )


def test_surface_bias_axis_pair_length():
    with pytest.raises(ValueError):
        surface._bias_axis(
            [
                (1.0,),
            ],
            (0.0, 0.0),
        )


def test_surface_bias_axis_finite():
    with pytest.raises(ValueError):
        surface._bias_axis(
            [
                (
                    np.nan,
                    1.0,
                ),
            ],
            (0.0, 0.0),
        )


def test_surface_spec_requires_base_spec():
    with pytest.raises(TypeError):
        surface.SyntheticGazeSurfaceSpec(
            base_spec=object(),
        )


def test_surface_spec_requires_positive_max_conditions():
    with pytest.raises(ValueError):
        surface.SyntheticGazeSurfaceSpec(
            base_spec=base_spec(),
            max_conditions=0,
        )


def test_surface_spec_from_dict_type_guard():
    with pytest.raises(TypeError):
        surface.SyntheticGazeSurfaceSpec.from_dict([])


def test_surface_expand_type_guard():
    with pytest.raises(TypeError):
        surface.expand_synthetic_gaze_surface(object())


def test_surface_condition_id_collision_guard(
    monkeypatch,
):
    monkeypatch.setattr(
        surface,
        "_condition_fingerprint",
        lambda spec: "a" * 64,
    )

    with pytest.raises(RuntimeError):
        surface.expand_synthetic_gaze_surface(two_noise_surface())


def test_surface_unexpected_expansion_count_guard(
    monkeypatch,
):
    monkeypatch.setattr(
        surface.SyntheticGazeSurfaceSpec,
        "condition_count",
        property(lambda self: 999),
    )

    with pytest.raises(RuntimeError):
        surface.expand_synthetic_gaze_surface(two_noise_surface())


def test_surface_metric_summary_ignores_missing_nonfinite():
    result = surface._metric_summary(
        [
            {
                "metrics": {
                    "coordinate_rmse_px": None,
                }
            },
            {
                "metrics": {
                    "coordinate_rmse_px": np.nan,
                }
            },
        ]
    )

    assert result == {}


def test_surface_threshold_overview_unthresholded():
    overview = surface._threshold_overview(
        [
            {
                "thresholds_passed": None,
            },
            {},
        ]
    )

    assert overview == {
        "thresholded_conditions": 0,
        "passed_conditions": 0,
        "failed_conditions": 0,
        "pass_fraction": None,
        "unthresholded_conditions": 2,
    }


def test_surface_evaluate_requires_callable():
    with pytest.raises(TypeError):
        surface.evaluate_synthetic_recovery_surface(
            two_noise_surface(),
            object(),
            estimator_name="demo",
        )


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
    ],
)
def test_surface_evaluate_requires_estimator_name(
    name,
):
    with pytest.raises(ValueError):
        surface.evaluate_synthetic_recovery_surface(
            two_noise_surface(),
            identity_estimator,
            estimator_name=name,
        )


def test_surface_validator_schema_guard(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["schema"] = "wrong"
    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_fingerprint_shape(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["surface_fingerprint_sha256"] = "bad"

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_fingerprint_mismatch(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["condition_count"] += 1

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_claim_boundary(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["claim_boundary"]["empirical_device_validity"] = True

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_metric_replay_boundary(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["metric_replay_requires_estimator_outputs"] = False

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_spec_type(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["surface_spec"] = []
    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_noncanonical_spec(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["surface_spec"]["design"] = "wrong"

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_inventory_types(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["condition_ledger"] = None
    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )

    certificate = _surface_copy(synthetic_certificate)

    certificate["child_certificates"] = []
    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_condition_count(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["condition_count"] = 999
    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_duplicate_condition_ids(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["condition_ledger"][1]["condition_id"] = certificate["condition_ledger"][0][
        "condition_id"
    ]

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_inventory_mismatch(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    key = next(iter(certificate["child_certificates"]))

    certificate["child_certificates"].pop(key)

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "callback_input",
            "truth",
        ),
        (
            "latent_truth_passed_to_callback",
            True,
        ),
        (
            "artifact_ledger_passed_to_callback",
            True,
        ),
    ],
)
def test_surface_validator_estimator_boundaries(
    synthetic_certificate,
    field,
    value,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["estimator"][field] = value

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def _first_surface_row(
    certificate,
):
    return certificate["condition_ledger"][0]


def test_surface_validator_condition_spec_fingerprint(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    _first_surface_row(certificate)["condition_spec_sha256"] = "0" * 64

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_condition_spec_payload(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    _first_surface_row(certificate)["spec"]["sampling_rate_hz"] = 120.0

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_child_type(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    condition_id = _first_surface_row(certificate)["condition_id"]

    certificate["child_certificates"][condition_id] = None

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "child_certificate_fingerprint_sha256",
            "0" * 64,
        ),
        (
            "run_contract_fingerprint_sha256",
            "0" * 64,
        ),
        (
            "estimate_sha256",
            "0" * 64,
        ),
        (
            "metrics",
            {},
        ),
        (
            "thresholds_passed",
            None,
        ),
    ],
)
def test_surface_validator_row_child_consistency(
    synthetic_certificate,
    field,
    value,
):
    certificate = _surface_copy(synthetic_certificate)

    _first_surface_row(certificate)[field] = value

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_threshold_consistency(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["thresholds"] = {
        "coordinate_rmse_px": 999.0,
    }

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_estimator_identity_consistency(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["estimator"]["name"] = "different-estimator"

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_metric_summary(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["metric_summary"] = {}

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_threshold_overview(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    certificate["threshold_overview"] = {}

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=False,
        )


def test_surface_validator_replay_observed_input_guard(
    synthetic_certificate,
):
    certificate = _surface_copy(synthetic_certificate)

    _first_surface_row(certificate)["observed_input_sha256"] = "0" * 64

    _resign_surface(certificate)

    with pytest.raises(ValueError):
        surface.validate_synthetic_recovery_surface(
            certificate,
            replay_contracts=True,
        )
