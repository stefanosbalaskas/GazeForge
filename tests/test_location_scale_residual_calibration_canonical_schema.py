from copy import deepcopy

import pandas as pd
import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import SchemaError
from gazeforge.location_scale_residual_calibration import (
    _CERTIFICATE_SCHEMA,
    _CLAIM_BOUNDARY,
    _DIAGNOSTIC_SCHEMA,
    _METRIC_ORDER,
    _SUMMARY_COLUMNS,
    LocationScaleResidualCalibrationSpec,
    validate_location_scale_residual_calibration_certificate,
)
from gazeforge.provenance import fingerprint_frame


def _canonical_certificate() -> dict:
    spec = LocationScaleResidualCalibrationSpec(
        n_simulations=60,
        seed=91,
        envelope_level=0.90,
        max_simulated_residual_draws=10_000,
    )
    summary = pd.DataFrame(
        [
            {
                "metric": metric,
                "observed": 0.0,
                "simulation_mean": 0.0,
                "envelope_lower": -1.0,
                "envelope_upper": 1.0,
                "simulation_percentile": 0.5,
                "outside_envelope": False,
            }
            for metric in _METRIC_ORDER
        ],
        columns=_SUMMARY_COLUMNS,
    )
    diagnostic = {
        "schema": _DIAGNOSTIC_SCHEMA,
        "spec": spec.to_dict(),
        "model_family": "independent_location_scale",
        "model_fingerprint_sha256": "1" * 64,
        "base_model_certificate_fingerprint_sha256": "2" * 64,
        "input_fingerprint_sha256": "3" * 64,
        "n_obs": 10,
        "n_groups": 2,
        "residuals_fingerprint_sha256": "4" * 64,
        "summary_fingerprint_sha256": fingerprint_frame(summary),
    }
    body = {
        "schema": _CERTIFICATE_SCHEMA,
        "diagnostic": diagnostic,
        "diagnostic_fingerprint_sha256": benchmark_fingerprint(diagnostic),
        "summary": summary.to_dict(orient="records"),
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return {
        **body,
        "certificate_fingerprint_sha256": benchmark_fingerprint(body),
    }


def _resign(certificate: dict, *, diagnostic_changed: bool = False) -> None:
    if diagnostic_changed:
        certificate["diagnostic_fingerprint_sha256"] = benchmark_fingerprint(
            certificate["diagnostic"]
        )
    body = {
        key: value
        for key, value in certificate.items()
        if key != "certificate_fingerprint_sha256"
    }
    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)


def test_canonical_residual_calibration_certificate_validates() -> None:
    validate_location_scale_residual_calibration_certificate(_canonical_certificate())


def test_resigned_unknown_top_level_field_fails_closed() -> None:
    attacked = deepcopy(_canonical_certificate())
    attacked["device_validity_established"] = True
    _resign(attacked)

    with pytest.raises(SchemaError, match="noncanonical schema"):
        validate_location_scale_residual_calibration_certificate(attacked)


def test_resigned_unknown_diagnostic_field_fails_closed() -> None:
    attacked = deepcopy(_canonical_certificate())
    attacked["diagnostic"]["empirical_validity_established"] = True
    _resign(attacked, diagnostic_changed=True)

    with pytest.raises(SchemaError, match="noncanonical schema"):
        validate_location_scale_residual_calibration_certificate(attacked)
