"""Frozen-evidence contract for Lund2013 ↔ Hollywood2EM cross-dataset validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .benchmarks import (
    BenchmarkDatasetCard,
    benchmark_fingerprint,
    build_benchmark_report,
    freeze_benchmark_report,
)
from .cross_dataset import CrossDatasetEventPrepared, CrossDatasetEventValidation
from .exceptions import BenchmarkIntegrityError
from .source_audit_lineage import SourceAuditLineageReceipt

CROSS_DATASET_EVIDENCE_SCHEMA = "gazeforge-cross-dataset-event-validation-v1"
CROSS_DATASET_VALIDATION_SCOPE = "cross-dataset-external-generalisation"
CROSS_DATASET_BENCHMARK_NAME = "Lund2013-Hollywood2EM-cross-dataset-events"
CROSS_DATASET_EXPECTED_DATASETS = ("Hollywood2EM", "Lund2013")
CROSS_DATASET_REPORT_FILENAME = "lund-hollywood2-cross-dataset-report.json"

_TOP_LEVEL_KEYS = frozenset(
    {"benchmark", "model", "protocol", "metrics", "report_fingerprint_sha256"}
)
_PROTOCOL_KEYS = frozenset(
    {
        "evidence_schema",
        "validation_design",
        "dataset_reports",
        "hollywood2_source_audit_lineage",
        "cross_dataset_validation_fingerprint_sha256",
        "scientific_boundary",
    }
)
_BOUNDARY = {
    "derived_60hz_evidence": True,
    "native_60hz_validity_claim_created": False,
    "gp3_validity_claim_created": False,
    "universal_cross_dataset_generalizability_claim_created": False,
    "human_reference_ground_truth_promoted": False,
    "source_rights_expanded": False,
    "raw_source_redistribution_authorized": False,
}


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _require_text(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkIntegrityError(f"Cross-dataset {field_name} must be non-empty text.")
    return value.strip()


def _require_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Cross-dataset {field_name} must be a JSON object.")
    return dict(value)


def _require_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> None:
    observed = frozenset(value)
    if observed != expected:
        raise BenchmarkIntegrityError(
            f"Cross-dataset {label} schema drifted; "
            f"missing={sorted(expected - observed)}, extra={sorted(observed - expected)}."
        )


def _summary_records(validation: CrossDatasetEventValidation) -> list[dict[str, Any]]:
    return validation.summary.to_dict(orient="records")


def _validation_fingerprint(
    prepared: CrossDatasetEventPrepared,
    validation: CrossDatasetEventValidation,
) -> str:
    payload = {
        "design": validation.design,
        "dataset_reports": prepared.dataset_reports,
        "summary": _summary_records(validation),
    }
    return benchmark_fingerprint(payload)


def _validate_design(design: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(design)
    if value.get("design") != "harmonised_cross_dataset_event_benchmark":
        raise BenchmarkIntegrityError("Cross-dataset preparation design is invalid.")
    if value.get("validation_design") != "leave_one_dataset_out":
        raise BenchmarkIntegrityError("Cross-dataset validation must be leave-one-dataset-out.")
    dataset_ids = value.get("dataset_ids")
    valid_dataset_ids = (
        isinstance(dataset_ids, list)
        and tuple(sorted(map(str, dataset_ids))) == CROSS_DATASET_EXPECTED_DATASETS
    )
    if not valid_dataset_ids:
        raise BenchmarkIntegrityError(
            "Cross-dataset Frozen Evidence requires exactly Lund2013 and Hollywood2EM."
        )
    if float(value.get("target_sampling_rate_hz", -1.0)) != 60.0:
        raise BenchmarkIntegrityError(
            "Cross-dataset Frozen Evidence requires derived 60 Hz analysis."
        )
    if value.get("require_resolved_participants") is not True:
        raise BenchmarkIntegrityError("Cross-dataset participant identities must be resolved.")
    if value.get("require_verified_coordinates") is not True:
        raise BenchmarkIntegrityError("Cross-dataset coordinate units must be verified.")
    if value.get("require_source_audits") is not True:
        raise BenchmarkIntegrityError("Cross-dataset source-audit enforcement must remain enabled.")
    models = value.get("models")
    if not isinstance(models, list) or tuple(map(str, models)) != (
        "RandomForest",
        "ContextMLP",
    ):
        raise BenchmarkIntegrityError(
            "Cross-dataset Frozen Evidence requires the matched RandomForest/ContextMLP design."
        )
    return value


def _validate_dataset_reports(reports: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(reports)
    if tuple(sorted(value)) != CROSS_DATASET_EXPECTED_DATASETS:
        raise BenchmarkIntegrityError(
            "Cross-dataset dataset_reports must contain exactly Lund2013 and Hollywood2EM."
        )
    for dataset_id in CROSS_DATASET_EXPECTED_DATASETS:
        report = _require_mapping(
            value[dataset_id], field_name=f"dataset_reports.{dataset_id}"
        )
        if report.get("participant_identity_resolved") is not True:
            raise BenchmarkIntegrityError(
                f"Cross-dataset {dataset_id} participant identities are not resolved."
            )
        if report.get("coordinate_unit_verified") is not True:
            raise BenchmarkIntegrityError(
                f"Cross-dataset {dataset_id} coordinate units are not verified."
            )
        if report.get("sampling_origin_at_analysis") != "resampled":
            raise BenchmarkIntegrityError(
                f"Cross-dataset {dataset_id} must be independently resampled to 60 Hz."
            )
        if float(report.get("target_sampling_rate_hz", -1.0)) != 60.0:
            raise BenchmarkIntegrityError(
                f"Cross-dataset {dataset_id} target sampling rate must be 60 Hz."
            )

    hollywood = _require_mapping(
        value["Hollywood2EM"], field_name="dataset_reports.Hollywood2EM"
    )
    if hollywood.get("source_audit_status") != "verified":
        raise BenchmarkIntegrityError(
            "Hollywood2EM must retain verified source-audit status in Frozen Evidence."
        )
    for key in (
        "source_audit_lineage_receipt_fingerprint_sha256",
        "source_audit_report_fingerprint_sha256",
        "source_audit_spec_fingerprint_sha256",
        "source_manifest_fingerprint_sha256",
    ):
        if not _valid_sha256(hollywood.get(key)):
            raise BenchmarkIntegrityError(
                f"Hollywood2EM cross-dataset provenance fingerprint {key} is invalid."
            )
    return value


def _validate_hollywood_lineage(
    payload: Mapping[str, Any], dataset_reports: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        receipt = SourceAuditLineageReceipt.from_dict(payload)
    except (BenchmarkIntegrityError, TypeError, ValueError) as exc:
        raise BenchmarkIntegrityError(
            "Cross-dataset Hollywood2EM source-audit lineage receipt is invalid."
        ) from exc
    if receipt.dataset_key != "hollywood2em":
        raise BenchmarkIntegrityError(
            "Cross-dataset Frozen Evidence requires a Hollywood2EM lineage receipt."
        )
    receipt_dict = receipt.to_dict()
    hollywood = _require_mapping(
        dataset_reports["Hollywood2EM"], field_name="dataset_reports.Hollywood2EM"
    )
    comparisons = {
        "source_audit_lineage_receipt_fingerprint_sha256": receipt_dict[
            "receipt_fingerprint_sha256"
        ],
        "source_audit_report_fingerprint_sha256": receipt.audit_report_fingerprint_sha256,
        "source_audit_spec_fingerprint_sha256": receipt.authorized_spec_fingerprint_sha256,
        "source_manifest_fingerprint_sha256": receipt.source_manifest_fingerprints_sha256[
            "source"
        ],
    }
    for field_name, expected in comparisons.items():
        if str(hollywood.get(field_name, "")) != str(expected):
            raise BenchmarkIntegrityError(
                "Cross-dataset Hollywood2EM runner provenance disagrees with the exact "
                f"source-audit lineage receipt for {field_name}."
            )
    return receipt_dict


def _validate_summary(summary: Any) -> list[dict[str, Any]]:
    if not isinstance(summary, list) or len(summary) != 4:
        raise BenchmarkIntegrityError(
            "Cross-dataset Frozen Evidence requires four model × held-out-dataset summary rows."
        )
    rows: list[dict[str, Any]] = []
    observed: set[tuple[str, str]] = set()
    for item in summary:
        row = _require_mapping(item, field_name="metrics.summary row")
        model = str(row.get("model", ""))
        held_out = str(row.get("held_out_dataset", ""))
        if model not in {"RandomForest", "ContextMLP"}:
            raise BenchmarkIntegrityError("Cross-dataset summary contains an unexpected model.")
        if held_out not in set(CROSS_DATASET_EXPECTED_DATASETS):
            raise BenchmarkIntegrityError(
                "Cross-dataset summary contains an unexpected held-out dataset."
            )
        key = (model, held_out)
        if key in observed:
            raise BenchmarkIntegrityError(
                "Cross-dataset summary contains a duplicate model/fold row."
            )
        observed.add(key)
        if int(row.get("n_test_rows", 0)) <= 0:
            raise BenchmarkIntegrityError("Cross-dataset summary n_test_rows must be positive.")
        rows.append(row)
    expected = {
        (model, dataset)
        for model in ("RandomForest", "ContextMLP")
        for dataset in CROSS_DATASET_EXPECTED_DATASETS
    }
    if observed != expected:
        raise BenchmarkIntegrityError(
            "Cross-dataset summary does not cover the complete matched design."
        )
    return rows


def build_lund_hollywood2_cross_dataset_report(
    prepared: CrossDatasetEventPrepared,
    validation: CrossDatasetEventValidation,
    *,
    hollywood2_lineage: SourceAuditLineageReceipt,
    benchmark_version: str,
) -> dict[str, Any]:
    """Build one frozen report from the guarded Lund↔Hollywood2 runner outputs."""
    if not isinstance(prepared, CrossDatasetEventPrepared):
        raise TypeError("prepared must be CrossDatasetEventPrepared.")
    if not isinstance(validation, CrossDatasetEventValidation):
        raise TypeError("validation must be CrossDatasetEventValidation.")
    if not isinstance(hollywood2_lineage, SourceAuditLineageReceipt):
        raise TypeError("hollywood2_lineage must be SourceAuditLineageReceipt.")

    version = _require_text(benchmark_version, field_name="benchmark_version")
    design = _validate_design(validation.design)
    dataset_reports = _validate_dataset_reports(prepared.dataset_reports)
    lineage = _validate_hollywood_lineage(hollywood2_lineage.to_dict(), dataset_reports)
    summary = _validate_summary(_summary_records(validation))

    expected_validation_fingerprint = _validation_fingerprint(prepared, validation)
    if validation.report_fingerprint_sha256 != expected_validation_fingerprint:
        raise BenchmarkIntegrityError(
            "Cross-dataset validation fingerprint no longer matches the guarded runner output."
        )

    benchmark = BenchmarkDatasetCard(
        name=CROSS_DATASET_BENCHMARK_NAME,
        version=version,
        source="Lund2013 + audited Hollywood2EM",
        license="mixed-source; see audited dataset provenance",
        task="leave-one-dataset-out eye-event generalisation",
        sampling_rates_hz=[60.0],
        split_unit="dataset_id",
        validation_scope=CROSS_DATASET_VALIDATION_SCOPE,
        annotation_origin="expert-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
        reference_description=(
            "Derived-60-Hz human event references with Hollywood2EM source-audit lineage."
        ),
        notes=[
            "This report is not native-60-Hz or GP3 validation.",
            "Hollywood2EM source rights are not expanded by this report.",
        ],
    )
    report = build_benchmark_report(
        benchmark=benchmark,
        model={"models": ["RandomForest", "ContextMLP"]},
        protocol={
            "evidence_schema": CROSS_DATASET_EVIDENCE_SCHEMA,
            "validation_design": design,
            "dataset_reports": dataset_reports,
            "hollywood2_source_audit_lineage": lineage,
            "cross_dataset_validation_fingerprint_sha256": expected_validation_fingerprint,
            "scientific_boundary": dict(_BOUNDARY),
        },
        metrics={"summary": summary},
    )
    return validate_cross_dataset_frozen_report(report)


def validate_cross_dataset_frozen_report(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one closed-schema Lund↔Hollywood2 Frozen Evidence report."""
    value = dict(report)
    _require_exact_keys(value, _TOP_LEVEL_KEYS, label="report")
    body = {
        key: value[key]
        for key in ("benchmark", "model", "protocol", "metrics")
    }
    observed_report_fingerprint = value.get("report_fingerprint_sha256")
    if not _valid_sha256(observed_report_fingerprint):
        raise BenchmarkIntegrityError("Cross-dataset report fingerprint is invalid.")
    if observed_report_fingerprint != benchmark_fingerprint(body):
        raise BenchmarkIntegrityError("Cross-dataset report fingerprint mismatch.")

    benchmark = _require_mapping(value.get("benchmark"), field_name="benchmark")
    if benchmark.get("name") != CROSS_DATASET_BENCHMARK_NAME:
        raise BenchmarkIntegrityError("Cross-dataset benchmark name is invalid.")
    if benchmark.get("validation_scope") != CROSS_DATASET_VALIDATION_SCOPE:
        raise BenchmarkIntegrityError("Cross-dataset validation scope is invalid.")
    if benchmark.get("annotation_origin") != "expert-manual":
        raise BenchmarkIntegrityError(
            "Cross-dataset annotation origin must remain expert-manual."
        )
    if benchmark.get("sampling_origin") != "resampled":
        raise BenchmarkIntegrityError("Cross-dataset sampling origin must remain resampled.")
    if benchmark.get("reference_strength") != "derived-human-reference":
        raise BenchmarkIntegrityError(
            "Cross-dataset reference strength must remain derived-human-reference."
        )
    rates = benchmark.get("sampling_rates_hz")
    if not isinstance(rates, list) or len(rates) != 1 or float(rates[0]) != 60.0:
        raise BenchmarkIntegrityError(
            "Cross-dataset benchmark rate must be exactly 60 Hz derived."
        )

    model = _require_mapping(value.get("model"), field_name="model")
    if model.get("models") != ["RandomForest", "ContextMLP"]:
        raise BenchmarkIntegrityError("Cross-dataset model inventory drifted.")

    protocol = _require_mapping(value.get("protocol"), field_name="protocol")
    _require_exact_keys(protocol, _PROTOCOL_KEYS, label="protocol")
    if protocol.get("evidence_schema") != CROSS_DATASET_EVIDENCE_SCHEMA:
        raise BenchmarkIntegrityError("Cross-dataset evidence schema is invalid.")
    design = _validate_design(
        _require_mapping(
            protocol.get("validation_design"), field_name="validation_design"
        )
    )
    dataset_reports = _validate_dataset_reports(
        _require_mapping(
            protocol.get("dataset_reports"), field_name="dataset_reports"
        )
    )
    lineage = _validate_hollywood_lineage(
        _require_mapping(
            protocol.get("hollywood2_source_audit_lineage"),
            field_name="hollywood2_source_audit_lineage",
        ),
        dataset_reports,
    )
    if protocol.get("scientific_boundary") != _BOUNDARY:
        raise BenchmarkIntegrityError("Cross-dataset scientific claim boundary drifted.")

    metrics = _require_mapping(value.get("metrics"), field_name="metrics")
    if frozenset(metrics) != frozenset({"summary"}):
        raise BenchmarkIntegrityError("Cross-dataset metrics schema drifted.")
    summary = _validate_summary(metrics["summary"])
    expected_validation_fingerprint = benchmark_fingerprint(
        {
            "design": design,
            "dataset_reports": dataset_reports,
            "summary": summary,
        }
    )
    observed_validation_fingerprint = protocol.get(
        "cross_dataset_validation_fingerprint_sha256"
    )
    if observed_validation_fingerprint != expected_validation_fingerprint:
        raise BenchmarkIntegrityError(
            "Cross-dataset report is not bound to the exact guarded validation result."
        )
    hollywood = dataset_reports["Hollywood2EM"]
    if (
        lineage["receipt_fingerprint_sha256"]
        != hollywood["source_audit_lineage_receipt_fingerprint_sha256"]
    ):
        raise BenchmarkIntegrityError(
            "Cross-dataset report lineage receipt fingerprint disagrees with runner provenance."
        )
    return value


def load_cross_dataset_frozen_report(path: str | Path) -> dict[str, Any]:
    """Load and validate one serialized cross-dataset Frozen Evidence report."""
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise BenchmarkIntegrityError(
            "Cross-dataset Frozen Evidence report must be a regular file."
        )
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            "Cross-dataset Frozen Evidence report is invalid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "Cross-dataset Frozen Evidence report must contain an object."
        )
    return validate_cross_dataset_frozen_report(payload)


def freeze_cross_dataset_frozen_report(
    report: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Freeze one validated cross-dataset report and revalidate the written bytes."""
    validated = validate_cross_dataset_frozen_report(report)
    target = freeze_benchmark_report(validated, path, overwrite=overwrite)
    load_cross_dataset_frozen_report(target)
    return target
