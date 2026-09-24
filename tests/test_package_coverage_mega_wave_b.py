from __future__ import annotations

import sys
import types

import numpy as np
import pytest

import gazeforge.correlated_location_scale as correlated
import gazeforge.full_covariance_location_random_slope_scale as full
import gazeforge.grounded_sam2 as grounded
import gazeforge.location_random_slope_scale as random_slope
import gazeforge.source_resolution as source_resolution
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError


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


def _random_certificate():
    spec = random_slope.LocationRandomSlopeScaleSpec(
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
        "population_random_effect_correlations": "independent",
        "log_likelihood": -20.0,
        "n_obs": 8,
        "n_groups": 2,
        "group_effects_fingerprint_sha256": "a" * 64,
        "input_fingerprint_sha256": "b" * 64,
    }

    return _seal(random_slope, model)


def _correlated_certificate():
    spec = correlated.CorrelatedLocationScaleSpec(
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
        "rho_location_log_scale": 0.25,
        "log_likelihood": -20.0,
        "n_obs": 6,
        "n_groups": 2,
        "group_effects_fingerprint_sha256": "c" * 64,
        "input_fingerprint_sha256": "d" * 64,
    }

    return _seal(correlated, model)


def _full_certificate():
    spec = full.FullCovarianceLocationRandomSlopeScaleSpec(
        outcome_col="y",
        group_col="g",
        random_slope_predictor="x",
        location_predictors=("x",),
        scale_predictors=("x",),
        quadrature_points=3,
        min_group_size=3,
    )

    _, rho_slope_scale = full._correlation_matrix_from_coordinates(
        0.20,
        0.10,
        0.30,
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
        "rho_location_intercept_slope": 0.20,
        "rho_location_intercept_log_scale": 0.10,
        "rho_location_slope_log_scale": float(rho_slope_scale),
        "partial_rho_location_slope_log_scale_given_intercept": 0.30,
        "log_likelihood": -20.0,
        "n_obs": 8,
        "n_groups": 2,
        "group_effects_fingerprint_sha256": "e" * 64,
        "input_fingerprint_sha256": "f" * 64,
    }

    return _seal(full, model)


FAMILIES = (
    {
        "name": "random-slope",
        "module": random_slope,
        "factory": _random_certificate,
        "validator": random_slope.validate_location_random_slope_scale_certificate,
        "tau_fields": (
            "tau_location_intercept",
            "tau_location_slope",
            "tau_log_scale",
        ),
    },
    {
        "name": "correlated",
        "module": correlated,
        "factory": _correlated_certificate,
        "validator": correlated.validate_correlated_location_scale_certificate,
        "tau_fields": (
            "tau_location",
            "tau_log_scale",
        ),
    },
    {
        "name": "full-covariance",
        "module": full,
        "factory": _full_certificate,
        "validator": full.validate_full_covariance_location_random_slope_scale_certificate,
        "tau_fields": (
            "tau_location_intercept",
            "tau_location_slope",
            "tau_log_scale",
        ),
    },
)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_canonical_location_scale_certificates_validate(family):
    family["validator"](family["factory"]())


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_certificate_exact_top_level_schema(family):
    certificate = family["factory"]()
    certificate["unexpected"] = True

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_certificate_schema_version_guard(family):
    certificate = family["factory"]()
    certificate["schema"] = "wrong"
    _resign(certificate, model_changed=False)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_certificate_fingerprint_guard(family):
    certificate = family["factory"]()
    certificate["certificate_fingerprint_sha256"] = "0" * 64

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_claim_boundary_guard(family):
    certificate = family["factory"]()

    key = next(iter(certificate["claim_boundary"]))
    certificate["claim_boundary"][key] = not certificate["claim_boundary"][key]
    _resign(certificate, model_changed=False)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    ("optimizer_key", "value"),
    [
        ("converged", False),
        ("status", True),
        ("iterations", True),
        ("iterations", -1),
        ("message", 123),
    ],
)
@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_optimizer_metadata_guards(
    family,
    optimizer_key,
    value,
):
    certificate = family["factory"]()
    certificate["optimizer"][optimizer_key] = value
    _resign(certificate, model_changed=False)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_optimizer_schema_guard(family):
    certificate = family["factory"]()
    certificate["optimizer"]["extra"] = True
    _resign(certificate, model_changed=False)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_model_fingerprint_guard(family):
    certificate = family["factory"]()
    certificate["model_fingerprint_sha256"] = "0" * 64
    _resign(certificate, model_changed=False)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quadrature_points", 4),
        ("max_iter", 0),
        ("tolerance", 0.0),
        ("outcome_col", ""),
        ("group_col", ""),
    ],
)
@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_invalid_specs_fail_closed(
    family,
    field,
    value,
):
    certificate = family["factory"]()
    certificate["model"]["spec"][field] = value
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_noncanonical_spec_fails_closed(family):
    certificate = family["factory"]()
    certificate["model"]["spec"]["outcome_col"] = " y "
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_location_terms_follow_spec(family):
    certificate = family["factory"]()
    certificate["model"]["location_fixed_effects"] = {
        "Intercept": 0.1,
    }
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_scale_terms_follow_spec(family):
    certificate = family["factory"]()
    certificate["model"]["scale_fixed_effects"] = []
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "field",
    [
        "group_effects_fingerprint_sha256",
        "input_fingerprint_sha256",
    ],
)
@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_embedded_fingerprints_are_sha256(
    family,
    field,
):
    certificate = family["factory"]()
    certificate["model"][field] = "bad"
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_estimates_are_canonical_numbers(family):
    certificate = family["factory"]()
    certificate["model"]["location_fixed_effects"]["Intercept"] = True
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_estimates_must_be_finite(family):
    certificate = family["factory"]()
    certificate["model"]["location_fixed_effects"]["Intercept"] = np.inf
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_random_effect_sds_must_be_positive(family):
    for field in family["tau_fields"]:
        certificate = family["factory"]()
        certificate["model"][field] = 0.0
        _resign(certificate)

        with pytest.raises(SchemaError):
            family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_n_obs_contract(family):
    certificate = family["factory"]()
    certificate["model"]["n_obs"] = True
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_n_groups_contract(family):
    certificate = family["factory"]()
    certificate["model"]["n_groups"] = 1
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


@pytest.mark.parametrize(
    "family",
    FAMILIES,
    ids=lambda item: item["name"],
)
def test_location_scale_minimum_group_size_contract(family):
    certificate = family["factory"]()
    certificate["model"]["n_obs"] = 1
    _resign(certificate)

    with pytest.raises(SchemaError):
        family["validator"](certificate)


def test_random_slope_certificate_requires_independent_population_effects():
    certificate = _random_certificate()
    certificate["model"]["population_random_effect_correlations"] = "correlated"
    _resign(certificate)

    with pytest.raises(SchemaError):
        random_slope.validate_location_random_slope_scale_certificate(certificate)


@pytest.mark.parametrize(
    "field",
    [
        "tau_location_intercept",
        "tau_location_slope",
    ],
)
def test_random_slope_location_sd_boundary_contract(field):
    certificate = _random_certificate()
    certificate["model"][field] = random_slope._MAX_LOCATION_RANDOM_EFFECT_SD
    _resign(certificate)

    with pytest.raises(SchemaError):
        random_slope.validate_location_random_slope_scale_certificate(certificate)


def test_random_slope_scale_sd_boundary_contract():
    certificate = _random_certificate()
    certificate["model"]["tau_log_scale"] = random_slope._MAX_LOG_SCALE_RANDOM_EFFECT_SD
    _resign(certificate)

    with pytest.raises(SchemaError):
        random_slope.validate_location_random_slope_scale_certificate(certificate)


def test_correlated_rho_requires_open_unit_interval():
    certificate = _correlated_certificate()
    certificate["model"]["rho_location_log_scale"] = 1.0
    _resign(certificate)

    with pytest.raises(SchemaError):
        correlated.validate_correlated_location_scale_certificate(certificate)


def test_correlated_rho_rejects_optimizer_boundary():
    certificate = _correlated_certificate()
    certificate["model"]["rho_location_log_scale"] = correlated._MAX_ABS_CERTIFIABLE_RHO
    _resign(certificate)

    with pytest.raises(SchemaError):
        correlated.validate_correlated_location_scale_certificate(certificate)


def test_correlated_random_effect_sd_boundary():
    certificate = _correlated_certificate()
    certificate["model"]["tau_location"] = correlated._MAX_LOCATION_RANDOM_EFFECT_SD
    _resign(certificate)

    with pytest.raises(SchemaError):
        correlated.validate_correlated_location_scale_certificate(certificate)


def test_full_covariance_rejects_coordinate_boundary():
    certificate = _full_certificate()
    certificate["model"]["rho_location_intercept_slope"] = (
        full._MAX_ABS_CERTIFIABLE_CORRELATION_COORDINATE
    )
    _resign(certificate)

    with pytest.raises(SchemaError):
        full.validate_full_covariance_location_random_slope_scale_certificate(certificate)


def test_full_covariance_rejects_inconsistent_marginal_rho():
    certificate = _full_certificate()
    certificate["model"]["rho_location_slope_log_scale"] += 0.2
    _resign(certificate)

    with pytest.raises(SchemaError):
        full.validate_full_covariance_location_random_slope_scale_certificate(certificate)


def test_full_covariance_wraps_unsupported_population_covariance(
    monkeypatch,
):
    certificate = _full_certificate()

    def fail(*args, **kwargs):
        raise ValueError("forced unsupported covariance")

    monkeypatch.setattr(
        full,
        "_population_covariance",
        fail,
    )

    with pytest.raises(
        SchemaError,
        match="numerically unsupported",
    ):
        full.validate_full_covariance_location_random_slope_scale_certificate(certificate)


# =====================================================================
# Finish the last reachable Grounded-SAM2 branches
# =====================================================================


def test_grounded_duplicate_aoi_frame_identity_is_rejected():
    seeds = [
        grounded.GroundedSAM2Seed(
            object_id=1,
            aoi_id="same",
            label="Target",
            score=0.9,
            box_xyxy=(0.0, 0.0, 2.0, 2.0),
        ),
        grounded.GroundedSAM2Seed(
            object_id=2,
            aoi_id="same",
            label="Target",
            score=0.8,
            box_xyxy=(0.0, 0.0, 2.0, 2.0),
        ),
    ]

    mask = np.ones((5, 5), dtype=bool)

    with pytest.raises(
        SchemaError,
        match="duplicate AOI/frame",
    ):
        grounded._canonical_from_segments(
            {
                0: {
                    1: mask,
                    2: mask,
                }
            },
            seeds=seeds,
            manifest=[
                {
                    "position": 0,
                    "frame_index": 0,
                }
            ],
            frame_rate_hz=25.0,
            frame_index_base=0,
            min_mask_pixels=1,
        )


def test_grounded_optional_import_success_contract(monkeypatch):
    torch_module = types.ModuleType("torch")

    pil_module = types.ModuleType("PIL")
    image_marker = object()
    pil_module.Image = image_marker

    sam2_module = types.ModuleType("sam2")
    sam2_module.__path__ = []

    sam2_build_module = types.ModuleType("sam2.build_sam")
    predictor_marker = object()
    sam2_build_module.build_sam2_video_predictor = predictor_marker

    transformers_module = types.ModuleType("transformers")
    processor_marker = object()
    model_marker = object()
    transformers_module.AutoProcessor = processor_marker
    transformers_module.AutoModelForZeroShotObjectDetection = model_marker

    monkeypatch.setitem(
        sys.modules,
        "torch",
        torch_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "PIL",
        pil_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "sam2",
        sam2_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "sam2.build_sam",
        sam2_build_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        transformers_module,
    )

    observed = grounded.HuggingFaceGroundedSAM2Runtime._imports()

    assert observed == (
        torch_module,
        image_marker,
        predictor_marker,
        processor_marker,
        model_marker,
    )


def test_hollywood_rights_false_path_exhausts_cleanly():
    source_resolution._require_hollywood2_rights(
        {
            "article_cc_by_is_dataset_license": False,
            "repository_license_file_recovered": False,
            "dataset_specific_license_verified": False,
            "open_source_description_is_exact_license_text": False,
        }
    )
