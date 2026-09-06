"""Immutable validation for the Hollywood2 source-token numeric portability migration."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .hollywood2_token_evidence import (
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1,
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2,
)

PORTABILITY_EVIDENCE_FINGERPRINT = (
    "3cc1072e1a79e9451b4ef17f98072d7f546f8055096a61842e575e8dbace9272"
)
V1_FROZEN_SUMMARY_FINGERPRINT = (
    "e1f1c030f843e118ebd65520dfab8e872efb4ea3e1d520299a993b0ca00ddabf"
)
V1_CANONICAL_REPORT_FINGERPRINT = (
    "a7a6219d6ffcb1fc6622110887a95f2c9d0646fea6e22d0ada941fe07b90586a"
)
V1_CANONICAL_REPORT_FILE_SHA256 = (
    "a5e22948105321dc97dcffc66926c32a6c93c797722b879e38fd3c6860dde34e"
)
V2_CANONICAL_REPORT_FINGERPRINT = (
    "35bdcca2f13a89805d68db1c3dca7e5106eb9533b8cf66024730031c5366d06d"
)
V2_CANONICAL_REPORT_FILE_SHA256 = (
    "d69b8811bb2c3c11ea21737ddcb308e7c0b601afd8858e8e23248fd243b51f51"
)
HOLLYWOOD2_SOURCE_TOKEN_V1_V2_MAX_ABS_METRIC_DELTA = 1e-14


def portability_evidence_fingerprint(record: dict[str, Any]) -> str:
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return benchmark_fingerprint(body)


def _load_record(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return dict(source)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def validate_hollywood2_v1_v2_metric_equivalence(
    v1_metrics: Any,
    v2_metrics: Any,
) -> float:
    """Validate that v1→v2 differs only within the reviewed serialization bound.

    Structure, keys, list lengths, scalar types, integers, strings, booleans, and nulls must be
    identical. Finite floats may differ by at most 1e-14, which is wider than the observed direct
    v1→v2 maximum (~7.1e-15) but remains narrower than the changed decimal place itself.
    """

    def walk(first: Any, second: Any, path: str) -> float:
        if isinstance(first, dict):
            if not isinstance(second, dict) or set(first) != set(second):
                raise BenchmarkIntegrityError(
                    f"Hollywood2 v1/v2 metric structure drifted at {path}."
                )
            return max(
                (walk(first[key], second[key], f"{path}.{key}") for key in first),
                default=0.0,
            )
        if isinstance(first, list):
            if not isinstance(second, list) or len(first) != len(second):
                raise BenchmarkIntegrityError(
                    f"Hollywood2 v1/v2 metric list structure drifted at {path}."
                )
            return max(
                (
                    walk(item_first, item_second, f"{path}[{index}]")
                    for index, (item_first, item_second) in enumerate(zip(first, second))
                ),
                default=0.0,
            )
        if isinstance(first, float):
            if not isinstance(second, float):
                raise BenchmarkIntegrityError(
                    f"Hollywood2 v1/v2 metric scalar type drifted at {path}."
                )
            if not math.isfinite(first) or not math.isfinite(second):
                raise BenchmarkIntegrityError(
                    f"Hollywood2 v1/v2 metrics must be finite at {path}."
                )
            delta = abs(first - second)
            if delta > HOLLYWOOD2_SOURCE_TOKEN_V1_V2_MAX_ABS_METRIC_DELTA:
                raise BenchmarkIntegrityError(
                    f"Hollywood2 v1/v2 metric delta exceeded portability bound at {path}."
                )
            return delta
        if type(first) is not type(second) or first != second:
            raise BenchmarkIntegrityError(
                f"Hollywood2 v1/v2 non-float metric value drifted at {path}."
            )
        return 0.0

    return walk(v1_metrics, v2_metrics, "metrics")


def validate_hollywood2_source_token_portability_evidence(
    source: str | Path | dict[str, Any],
) -> dict[str, Any]:
    """Validate the fail-closed v1→v2 numeric portability evidence record."""
    record = _load_record(source)
    if record.get("record_type") != (
        "hollywood2-source-token-numeric-portability-evidence-v2"
    ):
        raise BenchmarkIntegrityError("Unexpected Hollywood2 portability evidence record type.")
    if record.get("status") != "verified-reviewed-artifact-portability-migration":
        raise BenchmarkIntegrityError("Hollywood2 portability migration is not verified.")

    observed_fingerprint = portability_evidence_fingerprint(record)
    if record.get("evidence_fingerprint_sha256") != PORTABILITY_EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError(
            "Hollywood2 portability evidence fingerprint is not reviewed."
        )
    if observed_fingerprint != PORTABILITY_EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError("Hollywood2 portability evidence content drifted.")

    migration = record.get("migration")
    if not isinstance(migration, dict):
        raise BenchmarkIntegrityError("Hollywood2 portability migration metadata is missing.")
    before = migration.get("from_contract")
    after = migration.get("to_contract")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise BenchmarkIntegrityError("Hollywood2 portability contracts are missing.")

    before_contract = {
        key: before[key]
        for key in (
            "method",
            "metric_float_decimal_places",
            "nonfinite_metric_floats_permitted",
            "benchmark_model_protocol_numeric_values_rounded",
        )
    }
    after_contract = {
        key: after[key]
        for key in (
            "method",
            "metric_float_decimal_places",
            "nonfinite_metric_floats_permitted",
            "benchmark_model_protocol_numeric_values_rounded",
        )
    }
    if before_contract != HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1:
        raise BenchmarkIntegrityError("Historical Hollywood2 v1 numeric contract drifted.")
    if after_contract != HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2:
        raise BenchmarkIntegrityError("Current Hollywood2 v2 numeric contract drifted.")

    if before.get("frozen_summary_report_fingerprint_sha256") != (
        V1_FROZEN_SUMMARY_FINGERPRINT
    ):
        raise BenchmarkIntegrityError("Historical Hollywood2 frozen-summary identity drifted.")
    if before.get("canonical_source_report_fingerprint_sha256") != (
        V1_CANONICAL_REPORT_FINGERPRINT
    ):
        raise BenchmarkIntegrityError("Historical Hollywood2 v1 report identity drifted.")
    if before.get("canonical_source_report_file_sha256") != (
        V1_CANONICAL_REPORT_FILE_SHA256
    ):
        raise BenchmarkIntegrityError("Historical Hollywood2 v1 report bytes drifted.")
    if after.get("canonical_source_report_fingerprint_sha256") != (
        V2_CANONICAL_REPORT_FINGERPRINT
    ):
        raise BenchmarkIntegrityError("Hollywood2 v2 report identity drifted.")
    if after.get("canonical_source_report_file_sha256") != (
        V2_CANONICAL_REPORT_FILE_SHA256
    ):
        raise BenchmarkIntegrityError("Hollywood2 v2 report bytes drifted.")

    reviewed = record.get("reviewed_source_verified_artifacts")
    if not isinstance(reviewed, dict):
        raise BenchmarkIntegrityError("Hollywood2 reviewed source artifacts are missing.")
    if reviewed.get("v2_recanonicalized_reports_byte_identical") is not True:
        raise BenchmarkIntegrityError(
            "Hollywood2 v2 migration requires byte-identical reviewed artifact replay."
        )
    expected_artifacts = {
        "pre_merge": {
            "workflow_run_id": 33955703630,
            "head_sha": "5180d4e38a2f5929161b7baee6af18c5e9b43c4d",
            "artifact_id": 9966618539,
            "artifact_zip_sha256": (
                "a03b31f0a10f449aaa4212346f768be11797255eea9f9bc897b3baf8f575a8ae"
            ),
            "uncanonicalized_report_fingerprint_sha256": (
                "6d6b7a0c677e278d3503ca5f6c4745430a037ea6b42a3000b93052fa7f2f0cab"
            ),
            "uncanonicalized_report_file_sha256": (
                "0d3e0ad01d47e6f953fc233c2a1c1a491d3a418dd685b96919ccdda0b96aaa63"
            ),
        },
        "exact_merge": {
            "workflow_run_id": 33956874927,
            "head_sha": "e0e47c47e0a2e42a4520bd14a126b23fc3b05644",
            "artifact_id": 9966993646,
            "artifact_zip_sha256": (
                "3780e8d7a761e45e917e0229a02eeca332e9200473ef9a7489b1c41c5019a985"
            ),
            "uncanonicalized_report_fingerprint_sha256": (
                "d0ac2b9fd6e7f888abcba59f558b2424237ba86b789b14be53aa3a9414731bed"
            ),
            "uncanonicalized_report_file_sha256": (
                "94d7393a62f995559f0807a3188e3b4f64fbe18af9db4677e59bc2493b37b1fc"
            ),
        },
    }
    for label, expected in expected_artifacts.items():
        if reviewed.get(label) != expected:
            raise BenchmarkIntegrityError(
                f"Hollywood2 reviewed {label} artifact lineage drifted."
            )

    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, dict):
        raise BenchmarkIntegrityError("Hollywood2 portability scientific boundary is missing.")
    required_false = (
        "scientific_metrics_reestimated",
        "model_configuration_changed",
        "fold_assignment_changed",
        "source_rows_changed",
        "participant_identity_mapping_verified",
        "participant_disjoint_validation_created",
        "participant_generalization_claim",
        "cross_dataset_validation_created",
        "rights_status_changed",
        "raw_source_redistributed_by_gazeforge",
        "v1_evidence_rewritten",
    )
    if any(boundary.get(key) is not False for key in required_false):
        raise BenchmarkIntegrityError(
            "Hollywood2 portability evidence cannot promote scientific, rights, or mapping claims."
        )
    return record
