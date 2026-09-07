"""Immutable validation for the Hollywood2 source-token v3 portability migration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .hollywood2_token_evidence import (
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2,
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3,
)
from .hollywood2_token_portability_evidence import (
    PORTABILITY_EVIDENCE_FINGERPRINT as V2_PORTABILITY_EVIDENCE_FINGERPRINT,
)
from .hollywood2_token_portability_evidence import (
    V1_CANONICAL_REPORT_FILE_SHA256,
    V1_CANONICAL_REPORT_FINGERPRINT,
    V1_FROZEN_SUMMARY_FINGERPRINT,
    V2_CANONICAL_REPORT_FILE_SHA256,
    V2_CANONICAL_REPORT_FINGERPRINT,
)

PORTABILITY_V3_EVIDENCE_FINGERPRINT = (
    "b95ad7fd276117639eb6075fa05a5247fec307b479d218b2a3d43600d1b60d14"
)
V3_CANONICAL_REPORT_FINGERPRINT = (
    "8af10b2a110aeb193b17c6d86200e2f51139499b0fbcc14d10ebeb52213d753d"
)
V3_CANONICAL_REPORT_FILE_SHA256 = (
    "1082f248dbeafeca2038246ccf2caaa0caf96a83437dfede5e56bb541bdd5ea2"
)
V3_DIAGNOSTIC_RUN_ID = 34067228621
V3_DIAGNOSTIC_JOB_ID = 101578013917
V3_DIAGNOSTIC_HEAD_SHA = "7f29107ef42ed41cbf8eff548a8f60d3526ddd70"
V3_DIAGNOSTIC_ARTIFACT_ID = 9999556442
V3_DIAGNOSTIC_ARTIFACT_ZIP_SHA256 = (
    "4ef7df23e0f6c899128a5201c3deb773707b200c8d67c5781e501c85a56cd552"
)
V3_DIAGNOSTIC_REPORT_FILE_SHA256 = (
    "e9e580cef30eacb4c7e11a67c05eda422e5f2894123f47fbd775480090b033cf"
)
V3_DIAGNOSTIC_CONTENT_FINGERPRINT = (
    "7f5df70782f09fd2d22b891c6bd29ecf9459f1fd5c8fd256ead1b720c6caf301"
)
V3_DIAGNOSTIC_LIVE_RAW_REPORT_FILE_SHA256 = (
    "506d31ce063e6ebc981001f8d5eb0ec80cd60a7491c66624d6657e5750d63f85"
)
V3_DIAGNOSTIC_LIVE_RAW_REPORT_FINGERPRINT = (
    "d4e821b75bd75b34ee06e428ed8656a332c6ed36a9fb07fbd782c94fde357712"
)
V3_DIAGNOSTIC_MAX_ABS_RAW_METRIC_DELTA = 4.107825191113079e-15
V3_DIAGNOSTIC_MAX_DELTA_PATH = (
    "metrics.source_token_fold_metrics[5].multiclass_brier_score"
)


def portability_v3_evidence_fingerprint(record: dict[str, Any]) -> str:
    """Return the deterministic fingerprint of a v3 evidence record body."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return benchmark_fingerprint(body)


def _load_record(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return dict(source)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _contract_fields(record: dict[str, Any]) -> dict[str, Any]:
    try:
        return {
            key: record[key]
            for key in (
                "method",
                "metric_float_decimal_places",
                "nonfinite_metric_floats_permitted",
                "benchmark_model_protocol_numeric_values_rounded",
            )
        }
    except KeyError as exc:
        raise BenchmarkIntegrityError(
            "Hollywood2 v3 portability contract metadata is incomplete."
        ) from exc


def validate_hollywood2_source_token_portability_v3_evidence(
    source: str | Path | dict[str, Any],
) -> dict[str, Any]:
    """Validate the fail-closed v2→v3 cross-worker full-report evidence record."""
    record = _load_record(source)
    if record.get("record_type") != (
        "hollywood2-source-token-numeric-portability-evidence-v3"
    ):
        raise BenchmarkIntegrityError("Unexpected Hollywood2 v3 portability record type.")
    if record.get("status") != "verified-cross-worker-full-report-portability-migration":
        raise BenchmarkIntegrityError("Hollywood2 v3 portability migration is not verified.")

    if record.get("evidence_fingerprint_sha256") != PORTABILITY_V3_EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError("Hollywood2 v3 evidence fingerprint is not reviewed.")
    if portability_v3_evidence_fingerprint(record) != PORTABILITY_V3_EVIDENCE_FINGERPRINT:
        raise BenchmarkIntegrityError("Hollywood2 v3 evidence content drifted.")

    migration = record.get("migration")
    if not isinstance(migration, dict):
        raise BenchmarkIntegrityError("Hollywood2 v3 migration metadata is missing.")
    before = migration.get("from_contract")
    after = migration.get("to_contract")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise BenchmarkIntegrityError("Hollywood2 v3 portability contracts are missing.")

    if _contract_fields(before) != HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2:
        raise BenchmarkIntegrityError("Historical Hollywood2 v2 contract drifted.")
    if _contract_fields(after) != HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3:
        raise BenchmarkIntegrityError("Current Hollywood2 v3 contract drifted.")
    if before.get("canonical_source_report_fingerprint_sha256") != (
        V2_CANONICAL_REPORT_FINGERPRINT
    ):
        raise BenchmarkIntegrityError("Historical Hollywood2 v2 report identity drifted.")
    if before.get("canonical_source_report_file_sha256") != V2_CANONICAL_REPORT_FILE_SHA256:
        raise BenchmarkIntegrityError("Historical Hollywood2 v2 report bytes drifted.")
    if before.get("portability_evidence_fingerprint_sha256") != (
        V2_PORTABILITY_EVIDENCE_FINGERPRINT
    ):
        raise BenchmarkIntegrityError("Historical Hollywood2 v2 evidence identity drifted.")
    if after.get("canonical_source_report_fingerprint_sha256") != (
        V3_CANONICAL_REPORT_FINGERPRINT
    ):
        raise BenchmarkIntegrityError("Hollywood2 v3 report identity drifted.")
    if after.get("canonical_source_report_file_sha256") != V3_CANONICAL_REPORT_FILE_SHA256:
        raise BenchmarkIntegrityError("Hollywood2 v3 report bytes drifted.")

    historical = record.get("historical_evidence")
    if not isinstance(historical, dict):
        raise BenchmarkIntegrityError("Hollywood2 v3 historical evidence is missing.")
    historical_expected = {
        "v1_frozen_summary_report_fingerprint_sha256": V1_FROZEN_SUMMARY_FINGERPRINT,
        "v1_canonical_report_fingerprint_sha256": V1_CANONICAL_REPORT_FINGERPRINT,
        "v1_canonical_report_file_sha256": V1_CANONICAL_REPORT_FILE_SHA256,
        "v1_evidence_rewritten": False,
        "v2_evidence_rewritten": False,
    }
    for key, expected in historical_expected.items():
        if historical.get(key) != expected:
            raise BenchmarkIntegrityError(f"Hollywood2 historical evidence drifted at {key}.")

    observations = record.get("portability_observations")
    if not isinstance(observations, dict):
        raise BenchmarkIntegrityError("Hollywood2 v3 portability observations are missing.")
    failed_v2 = observations.get("v2_live_binding_failure")
    diagnostic = observations.get("full_report_diagnostic")
    if not isinstance(failed_v2, dict) or not isinstance(diagnostic, dict):
        raise BenchmarkIntegrityError("Hollywood2 v3 portability observation details are missing.")

    expected_failed_v2 = {
        "workflow_run_id": 34066070468,
        "head_sha": "0dd3d08d44e8e74551b3301ef035e5ad0d4dadc3",
        "frozen_python_runtime_verified": True,
        "pinned_source_commit_verified": True,
        "empirical_compute_succeeded": True,
        "v2_exact_binding_failed": True,
        "observed_v2_report_fingerprint_sha256": (
            "ccace72355353cd9cd3cb633067c68db1d8a0cdb02f63335ece003301e74db5c"
        ),
    }
    if failed_v2 != expected_failed_v2:
        raise BenchmarkIntegrityError("Hollywood2 v2 live-binding failure lineage drifted.")

    expected_diagnostic = {
        "workflow_run_id": V3_DIAGNOSTIC_RUN_ID,
        "job_id": V3_DIAGNOSTIC_JOB_ID,
        "head_sha": V3_DIAGNOSTIC_HEAD_SHA,
        "artifact_id": V3_DIAGNOSTIC_ARTIFACT_ID,
        "artifact_zip_sha256": V3_DIAGNOSTIC_ARTIFACT_ZIP_SHA256,
        "diagnostic_report_file_sha256": V3_DIAGNOSTIC_REPORT_FILE_SHA256,
        "diagnostic_content_fingerprint_sha256": V3_DIAGNOSTIC_CONTENT_FINGERPRINT,
        "live_raw_report_file_sha256": V3_DIAGNOSTIC_LIVE_RAW_REPORT_FILE_SHA256,
        "live_raw_report_fingerprint_sha256": V3_DIAGNOSTIC_LIVE_RAW_REPORT_FINGERPRINT,
        "max_abs_raw_metric_delta": V3_DIAGNOSTIC_MAX_ABS_RAW_METRIC_DELTA,
        "max_abs_raw_metric_delta_path": V3_DIAGNOSTIC_MAX_DELTA_PATH,
        "highest_precision_with_exact_full_report_match": 13,
        "precision_14_exact_full_report_match": False,
        "precision_13_exact_full_report_match": True,
        "precision_13_report_fingerprint_sha256": V3_CANONICAL_REPORT_FINGERPRINT,
        "precision_13_report_file_sha256": V3_CANONICAL_REPORT_FILE_SHA256,
    }
    if diagnostic != expected_diagnostic:
        raise BenchmarkIntegrityError("Hollywood2 v3 full-report diagnostic lineage drifted.")

    reviewed = record.get("reviewed_source_verified_artifacts")
    if not isinstance(reviewed, dict):
        raise BenchmarkIntegrityError("Hollywood2 reviewed source artifacts are missing.")
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
    if reviewed.get("v3_recanonicalized_reviewed_reports_byte_identical") is not True:
        raise BenchmarkIntegrityError("Hollywood2 v3 reviewed-artifact replay is not verified.")
    if reviewed.get("v3_cross_worker_full_report_match_verified") is not True:
        raise BenchmarkIntegrityError(
            "Hollywood2 v3 cross-worker full-report match is not verified."
        )

    boundary = record.get("scientific_boundary")
    if not isinstance(boundary, dict):
        raise BenchmarkIntegrityError("Hollywood2 v3 scientific boundary is missing.")
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
        "v2_evidence_rewritten",
    )
    if any(boundary.get(key) is not False for key in required_false):
        raise BenchmarkIntegrityError(
            "Hollywood2 v3 evidence cannot promote scientific, rights, or mapping claims."
        )
    return record
