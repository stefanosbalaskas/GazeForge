from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

import pytest

import gazeforge.correlated_location_scale as correlated
import gazeforge.hierarchical_location_scale as hierarchical
import gazeforge.location_random_slope_scale as random_slope
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError

Validator = Callable[[dict[str, Any]], None]
Factory = Callable[[], dict[str, Any]]


def _sign(body: dict[str, Any]) -> dict[str, Any]:
    return {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }


def _resign(certificate: dict[str, Any], *, model_changed: bool = False) -> None:
    if model_changed:
        certificate["model_fingerprint_sha256"] = benchmark_fingerprint(
            certificate["model"]
        )
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def _hierarchical_certificate() -> dict[str, Any]:
    spec = hierarchical.HierarchicalLocationScaleSpec(
        outcome_col="y",
        group_col="participant",
        quadrature_points=3,
    )
    model = {
        "spec": spec.to_dict(),
        "location_fixed_effects": {"Intercept": 0.0},
        "scale_fixed_effects": {"Intercept": 0.0},
        "tau_location": 0.5,
        "tau_log_scale": 0.25,
        "log_likelihood": -10.0,
        "n_obs": 8,
        "n_groups": 2,
        "group_effects_fingerprint_sha256": "a" * 64,
        "input_fingerprint_sha256": "b" * 64,
    }
    body = {
        "schema": hierarchical._CERTIFICATE_SCHEMA,
        "model": model,
        "model_fingerprint_sha256": benchmark_fingerprint(model),
        "optimizer": {
            "converged": True,
            "status": 0,
            "message": "CONVERGENCE",
            "iterations": 2,
        },
        "claim_boundary": dict(hierarchical._CLAIM_BOUNDARY),
    }
    return _sign(body)


def _correlated_certificate() -> dict[str, Any]:
    spec = correlated.CorrelatedLocationScaleSpec(
        outcome_col="y",
        group_col="participant",
        quadrature_points=3,
    )
    model = {
        "spec": spec.to_dict(),
        "location_fixed_effects": {"Intercept": 0.0},
        "scale_fixed_effects": {"Intercept": 0.0},
        "tau_location": 0.5,
        "tau_log_scale": 0.25,
        "rho_location_log_scale": 0.1,
        "log_likelihood": -10.0,
        "n_obs": 8,
        "n_groups": 2,
        "group_effects_fingerprint_sha256": "a" * 64,
        "input_fingerprint_sha256": "b" * 64,
    }
    body = {
        "schema": correlated._CERTIFICATE_SCHEMA,
        "model": model,
        "model_fingerprint_sha256": benchmark_fingerprint(model),
        "optimizer": {
            "converged": True,
            "status": 0,
            "message": "CONVERGENCE",
            "iterations": 2,
        },
        "claim_boundary": dict(correlated._CLAIM_BOUNDARY),
    }
    return _sign(body)


def _random_slope_certificate() -> dict[str, Any]:
    spec = random_slope.LocationRandomSlopeScaleSpec(
        outcome_col="y",
        group_col="participant",
        random_slope_predictor="x",
        location_predictors=("x",),
        quadrature_points=3,
        min_group_size=4,
    )
    model = {
        "spec": spec.to_dict(),
        "location_fixed_effects": {"Intercept": 0.0, "x": 0.5},
        "scale_fixed_effects": {"Intercept": 0.0},
        "tau_location_intercept": 0.5,
        "tau_location_slope": 0.3,
        "tau_log_scale": 0.25,
        "population_random_effect_correlations": "independent",
        "log_likelihood": -10.0,
        "n_obs": 8,
        "n_groups": 2,
        "group_effects_fingerprint_sha256": "a" * 64,
        "input_fingerprint_sha256": "b" * 64,
    }
    body = {
        "schema": random_slope._CERTIFICATE_SCHEMA,
        "model": model,
        "model_fingerprint_sha256": benchmark_fingerprint(model),
        "optimizer": {
            "converged": True,
            "status": 0,
            "message": "CONVERGENCE",
            "iterations": 2,
        },
        "claim_boundary": dict(random_slope._CLAIM_BOUNDARY),
    }
    return _sign(body)


CASES: tuple[tuple[str, Factory, Validator], ...] = (
    (
        "hierarchical",
        _hierarchical_certificate,
        hierarchical.validate_hierarchical_location_scale_certificate,
    ),
    (
        "correlated",
        _correlated_certificate,
        correlated.validate_correlated_location_scale_certificate,
    ),
    (
        "random_slope",
        _random_slope_certificate,
        random_slope.validate_location_random_slope_scale_certificate,
    ),
)


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
def test_canonical_handbuilt_certificate_is_valid(
    name: str,
    factory: Factory,
    validator: Validator,
) -> None:
    del name
    validator(factory())


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
def test_resigned_unknown_top_level_field_fails_closed(
    name: str,
    factory: Factory,
    validator: Validator,
) -> None:
    del name
    attacked = copy.deepcopy(factory())
    attacked["device_validity_established"] = True
    _resign(attacked)
    with pytest.raises(SchemaError):
        validator(attacked)


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
def test_resigned_unknown_model_field_fails_closed(
    name: str,
    factory: Factory,
    validator: Validator,
) -> None:
    del name
    attacked = copy.deepcopy(factory())
    attacked["model"]["causal_effect_established"] = True
    _resign(attacked, model_changed=True)
    with pytest.raises(SchemaError):
        validator(attacked)


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
def test_resigned_unknown_optimizer_field_fails_closed(
    name: str,
    factory: Factory,
    validator: Validator,
) -> None:
    del name
    attacked = copy.deepcopy(factory())
    attacked["optimizer"]["scientifically_validated"] = True
    _resign(attacked)
    with pytest.raises(SchemaError):
        validator(attacked)


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
@pytest.mark.parametrize("bad_value", [True, "0.5"])
def test_resigned_noncanonical_fixed_effect_type_fails_closed(
    name: str,
    factory: Factory,
    validator: Validator,
    bad_value: object,
) -> None:
    del name
    attacked = copy.deepcopy(factory())
    attacked["model"]["location_fixed_effects"]["Intercept"] = bad_value
    _resign(attacked, model_changed=True)
    with pytest.raises(SchemaError):
        validator(attacked)


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
def test_resigned_string_optimizer_iterations_fails_closed(
    name: str,
    factory: Factory,
    validator: Validator,
) -> None:
    del name
    attacked = copy.deepcopy(factory())
    attacked["optimizer"]["iterations"] = "2"
    _resign(attacked)
    with pytest.raises(SchemaError):
        validator(attacked)


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
@pytest.mark.parametrize("bad_status", [True, "0"])
def test_resigned_noninteger_optimizer_status_fails_closed(
    name: str,
    factory: Factory,
    validator: Validator,
    bad_status: object,
) -> None:
    del name
    attacked = copy.deepcopy(factory())
    attacked["optimizer"]["status"] = bad_status
    _resign(attacked)
    with pytest.raises(SchemaError):
        validator(attacked)


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
def test_resigned_negative_optimizer_iterations_fails_closed(
    name: str,
    factory: Factory,
    validator: Validator,
) -> None:
    del name
    attacked = copy.deepcopy(factory())
    attacked["optimizer"]["iterations"] = -1
    _resign(attacked)
    with pytest.raises(SchemaError):
        validator(attacked)


@pytest.mark.parametrize(("name", "factory", "validator"), CASES)
def test_resigned_nonstring_optimizer_message_fails_closed(
    name: str,
    factory: Factory,
    validator: Validator,
) -> None:
    del name
    attacked = copy.deepcopy(factory())
    attacked["optimizer"]["message"] = 0
    _resign(attacked)
    with pytest.raises(SchemaError):
        validator(attacked)
