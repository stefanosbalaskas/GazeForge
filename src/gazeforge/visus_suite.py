"""Atomic orchestration and verification for audited VISUS dynamic-AOI validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from .benchmarks import benchmark_fingerprint, freeze_benchmark_report
from .dynamic_aoi import DynamicAOIKeyframe
from .exceptions import BenchmarkIntegrityError
from .visus_agreement import run_visus_dynamic_aoi_human_agreement
from .visus_audit import VisusSourceAuditRun
from .visus_intake import VisusCanonicalAOIIntakeRun
from .visus_prediction import VisusDynamicAOIPredictionIntakeRun
from .visus_validation import run_visus_dynamic_aoi_model_validation

_SUITE_NAME = "visus-dynamic-aoi-validation-v1"
_SUITE_MANIFEST_NAME = "visus-dynamic-aoi-suite-manifest.json"
_BASE_REPORT_NAMES = frozenset(
    {
        "human_reference_intake",
        "model_prediction_intake",
        "model_human_validation",
    }
)
_HUMAN_AGREEMENT_NAME = "human_human_agreement"


@dataclass(slots=True)
class VisusDynamicAOIValidationSuiteRun:
    """Frozen VISUS provenance/validation reports plus a completion manifest."""

    output_dir: Path
    report_paths: dict[str, Path]
    reports: dict[str, dict[str, Any]]
    manifest_path: Path
    manifest: dict[str, Any]
    suite_fingerprint_sha256: str


def _report_fingerprint(report: Mapping[str, Any], *, name: str) -> str:
    claimed = report.get("report_fingerprint_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise BenchmarkIntegrityError(f"VISUS suite child {name!r} is missing a valid fingerprint.")
    body = {key: value for key, value in report.items() if key != "report_fingerprint_sha256"}
    if benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(f"VISUS suite child {name!r} fingerprint does not revalidate.")
    return claimed


def _audit_identity(audit: VisusSourceAuditRun) -> dict[str, str]:
    if not isinstance(audit, VisusSourceAuditRun):
        raise TypeError("audit must be a VisusSourceAuditRun instance.")
    if audit.report.get("status") != "verified":
        raise BenchmarkIntegrityError("VISUS source audit is not verified.")
    claimed = str(audit.report.get("report_fingerprint_sha256", ""))
    body = {key: value for key, value in audit.report.items() if key != "report_fingerprint_sha256"}
    if len(claimed) != 64 or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError("VISUS source-audit report fingerprint does not revalidate.")
    spec = str(audit.report.get("spec_fingerprint_sha256", ""))
    if benchmark_fingerprint(audit.spec.to_dict()) != spec:
        raise BenchmarkIntegrityError("VISUS source-audit specification fingerprint does not revalidate.")
    manifest = str(audit.report.get("inventory", {}).get("manifest_fingerprint_sha256", ""))
    if len(manifest) != 64:
        raise BenchmarkIntegrityError("VISUS source audit is missing a manifest fingerprint.")
    return {
        "source_audit_report_fingerprint_sha256": claimed,
        "source_audit_spec_fingerprint_sha256": spec,
        "source_manifest_fingerprint_sha256": manifest,
    }


def _child_source_identity(report: Mapping[str, Any], *, benchmark_report: bool) -> dict[str, str]:
    source: Mapping[str, Any]
    if benchmark_report:
        protocol = report.get("protocol")
        if not isinstance(protocol, Mapping):
            raise BenchmarkIntegrityError("VISUS benchmark child protocol must be an object.")
        source = protocol
    else:
        source = report
    return {
        key: str(source.get(key, ""))
        for key in (
            "source_audit_report_fingerprint_sha256",
            "source_audit_spec_fingerprint_sha256",
            "source_manifest_fingerprint_sha256",
        )
    }


def _verify_intakes(
    audit: VisusSourceAuditRun,
    reference: VisusCanonicalAOIIntakeRun,
    prediction: VisusDynamicAOIPredictionIntakeRun,
) -> tuple[dict[str, str], dict[str, Any]]:
    if not isinstance(reference, VisusCanonicalAOIIntakeRun):
        raise TypeError("reference_intake must be a VisusCanonicalAOIIntakeRun instance.")
    if not isinstance(prediction, VisusDynamicAOIPredictionIntakeRun):
        raise TypeError("prediction_intake must be a VisusDynamicAOIPredictionIntakeRun instance.")
    identity = _audit_identity(audit)
    _report_fingerprint(reference.report, name="human_reference_intake")
    _report_fingerprint(prediction.report, name="model_prediction_intake")
    if reference.report.get("status") != "verified-canonical-intake":
        raise BenchmarkIntegrityError("VISUS human-reference intake is not verified.")
    if prediction.report.get("status") != "verified-prediction-intake":
        raise BenchmarkIntegrityError("VISUS model-prediction intake is not verified.")
    if _child_source_identity(reference.report, benchmark_report=False) != identity:
        raise BenchmarkIntegrityError("VISUS human-reference intake does not share source identity.")
    if _child_source_identity(prediction.report, benchmark_report=False) != identity:
        raise BenchmarkIntegrityError("VISUS model-prediction intake does not share source identity.")
    if prediction.report.get("evaluation_timestamp_grid_generated") is not False:
        raise BenchmarkIntegrityError(
            "VISUS prediction intake must not generate the evaluation timestamp grid."
        )
    model = prediction.report.get("model")
    if not isinstance(model, dict):
        raise BenchmarkIntegrityError("VISUS prediction intake is missing model provenance.")
    name = str(model.get("name", "")).strip()
    version = str(model.get("version", "")).strip()
    if not name or not version:
        raise BenchmarkIntegrityError("VISUS prediction intake model identity is incomplete.")
    return identity, model


def _target_paths(output_dir: Path, *, include_human_agreement: bool) -> dict[str, Path]:
    paths = {
        "human_reference_intake": output_dir / "visus-human-reference-intake.json",
        "model_prediction_intake": output_dir / "visus-model-prediction-intake.json",
        "model_human_validation": output_dir / "visus-model-human-validation.json",
    }
    if include_human_agreement:
        paths[_HUMAN_AGREEMENT_NAME] = output_dir / "visus-human-human-agreement.json"
    return paths


def _preflight(paths: Mapping[str, Path], manifest_path: Path, *, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [path for path in [*paths.values(), manifest_path] if path.exists()]
    if existing:
        raise FileExistsError(
            "VISUS validation suite output already exists: "
            + ", ".join(str(path) for path in existing)
        )


def _safe_child_path(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise BenchmarkIntegrityError("VISUS suite manifest contains an unsafe report path.")
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise BenchmarkIntegrityError("VISUS suite report path escapes the suite directory.")
    return resolved


def _manifest_path(path: str | Path) -> Path:
    source = Path(path)
    return source / _SUITE_MANIFEST_NAME if source.is_dir() else source


def _expected_report_names(protocol: Mapping[str, Any]) -> set[str]:
    expected = set(_BASE_REPORT_NAMES)
    if protocol.get("human_human_agreement_included") is True:
        expected.add(_HUMAN_AGREEMENT_NAME)
    return expected


def _validate_child_semantics(
    name: str,
    report: Mapping[str, Any],
    *,
    source_identity: Mapping[str, str],
    protocol: Mapping[str, Any],
) -> None:
    benchmark_report = name in {"model_human_validation", _HUMAN_AGREEMENT_NAME}
    if _child_source_identity(report, benchmark_report=benchmark_report) != dict(source_identity):
        raise BenchmarkIntegrityError(f"VISUS suite child {name!r} source identity mismatch.")

    if name == "human_reference_intake":
        if report.get("status") != "verified-canonical-intake":
            raise BenchmarkIntegrityError("VISUS reference-intake child is not verified.")
        stream = str(protocol.get("reference_stream_id", ""))
        if stream not in set(report.get("annotation_stream_ids", [])):
            raise BenchmarkIntegrityError("VISUS suite reference stream is absent from intake.")
    elif name == "model_prediction_intake":
        if report.get("status") != "verified-prediction-intake":
            raise BenchmarkIntegrityError("VISUS prediction-intake child is not verified.")
        if report.get("evaluation_timestamp_grid_generated") is not False:
            raise BenchmarkIntegrityError("VISUS prediction child improperly generated a grid.")
        child_model = report.get("model", {})
        if child_model.get("name") != protocol.get("model_name") or child_model.get(
            "version"
        ) != protocol.get("model_version"):
            raise BenchmarkIntegrityError("VISUS prediction child model identity mismatch.")
    elif name == "model_human_validation":
        child_protocol = report.get("protocol", {})
        if child_protocol.get("reference_stream_id") != protocol.get("reference_stream_id"):
            raise BenchmarkIntegrityError("VISUS model-human reference stream mismatch.")
        if child_protocol.get("timestamp_grid_explicit") is not True:
            raise BenchmarkIntegrityError("VISUS model-human child lacks an explicit grid.")
        if child_protocol.get("timestamp_grid_basis") != protocol.get("timestamp_grid_basis"):
            raise BenchmarkIntegrityError("VISUS model-human timestamp-grid basis mismatch.")
        if child_protocol.get("timestamp_grids") != protocol.get("timestamp_grids"):
            raise BenchmarkIntegrityError("VISUS model-human timestamp-grid fingerprints mismatch.")
        if child_protocol.get("human_human_agreement_claimed") is not False:
            raise BenchmarkIntegrityError("VISUS model-human child makes an invalid HH claim.")
        child_model = report.get("model", {})
        if child_model.get("name") != protocol.get("model_name") or child_model.get(
            "version"
        ) != protocol.get("model_version"):
            raise BenchmarkIntegrityError("VISUS model-human child model identity mismatch.")
    elif name == _HUMAN_AGREEMENT_NAME:
        child_protocol = report.get("protocol", {})
        if protocol.get("independent_annotation_streams_verified") is not True:
            raise BenchmarkIntegrityError("VISUS human-agreement child lacks suite independence proof.")
        if child_protocol.get("independent_annotation_streams_verified") is not True:
            raise BenchmarkIntegrityError("VISUS human-agreement child lacks independence proof.")
        if child_protocol.get("human_agreement_reference_not_ground_truth") is not True:
            raise BenchmarkIntegrityError("VISUS human-agreement child must be not-ground-truth.")
        pair = list(protocol.get("human_agreement_stream_ids", []))
        observed = [child_protocol.get("left_stream_id"), child_protocol.get("right_stream_id")]
        if observed != pair:
            raise BenchmarkIntegrityError("VISUS human-agreement stream pair mismatch.")
        if child_protocol.get("timestamp_grid_basis") != protocol.get("timestamp_grid_basis"):
            raise BenchmarkIntegrityError("VISUS human-agreement timestamp-grid basis mismatch.")


def validate_visus_dynamic_aoi_suite_manifest(
    path: str | Path,
    *,
    verify_reports: bool = True,
) -> dict[str, Any]:
    """Validate a VISUS dynamic-AOI suite manifest and its child reports."""
    manifest_path = _manifest_path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError("VISUS suite manifest is not valid JSON.") from exc
    if not isinstance(manifest, dict):
        raise BenchmarkIntegrityError("VISUS suite manifest must be a JSON object.")
    required = {"suite", "status", "source", "protocol", "reports", "suite_fingerprint_sha256"}
    missing = sorted(required - set(manifest))
    if missing:
        raise BenchmarkIntegrityError(f"VISUS suite manifest is missing fields: {missing}")
    if manifest["suite"] != _SUITE_NAME or manifest["status"] != "complete":
        raise BenchmarkIntegrityError("VISUS suite manifest identity/status is invalid.")
    claimed = manifest["suite_fingerprint_sha256"]
    body = {key: value for key, value in manifest.items() if key != "suite_fingerprint_sha256"}
    if not isinstance(claimed, str) or len(claimed) != 64 or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError("VISUS suite manifest fingerprint mismatch.")

    source = manifest["source"]
    protocol = manifest["protocol"]
    records = manifest["reports"]
    if not isinstance(source, dict) or not isinstance(protocol, dict) or not isinstance(records, list):
        raise BenchmarkIntegrityError("VISUS suite source/protocol/reports structure is invalid.")
    source_identity = {
        key: str(source.get(key, ""))
        for key in (
            "source_audit_report_fingerprint_sha256",
            "source_audit_spec_fingerprint_sha256",
            "source_manifest_fingerprint_sha256",
        )
    }
    if any(len(value) != 64 for value in source_identity.values()):
        raise BenchmarkIntegrityError("VISUS suite source fingerprints are incomplete.")

    names: set[str] = set()
    paths: set[str] = set()
    verified: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise BenchmarkIntegrityError("VISUS suite contains an invalid report record.")
        name = str(record.get("name", ""))
        relative = str(record.get("path", ""))
        fingerprint = str(record.get("report_fingerprint_sha256", ""))
        if not name or name in names or not relative or relative in paths or len(fingerprint) != 64:
            raise BenchmarkIntegrityError("VISUS suite report records must be unique and complete.")
        names.add(name)
        paths.add(relative)
        child_path = _safe_child_path(manifest_path.parent, relative)
        if verify_reports:
            if not child_path.is_file():
                raise BenchmarkIntegrityError(f"VISUS suite child report is missing: {relative}")
            try:
                child = json.loads(child_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise BenchmarkIntegrityError(f"VISUS suite child is invalid JSON: {relative}") from exc
            if not isinstance(child, dict):
                raise BenchmarkIntegrityError(f"VISUS suite child must be an object: {relative}")
            observed = _report_fingerprint(child, name=name)
            if observed != fingerprint:
                raise BenchmarkIntegrityError(f"VISUS suite manifest/child fingerprint mismatch: {name}")
            _validate_child_semantics(
                name,
                child,
                source_identity=source_identity,
                protocol=protocol,
            )
        verified.append({"name": name, "path": relative, "report_fingerprint_sha256": fingerprint})

    expected = _expected_report_names(protocol)
    if names != expected:
        raise BenchmarkIntegrityError(
            "VISUS suite report inventory mismatch: "
            f"missing={sorted(expected - names)}, unexpected={sorted(names - expected)}"
        )
    if protocol.get("independent_annotation_streams_verified") is True and (
        protocol.get("human_human_agreement_included") is not True
    ):
        raise BenchmarkIntegrityError(
            "VISUS suite omits human-human agreement despite verified independent streams."
        )
    return {
        "suite": _SUITE_NAME,
        "status": "complete",
        "report_count": len(verified),
        "reports": verified,
        "source": source,
        "protocol": protocol,
        "suite_fingerprint_sha256": claimed,
        "reports_verified": bool(verify_reports),
        "manifest_path": str(manifest_path),
    }


def run_visus_dynamic_aoi_validation_suite(
    audit: VisusSourceAuditRun,
    reference_intake: VisusCanonicalAOIIntakeRun,
    prediction_intake: VisusDynamicAOIPredictionIntakeRun,
    timestamps_by_stimulus: Mapping[str, Sequence[float]],
    output_dir: str | Path,
    *,
    reference_stream_id: str,
    timestamp_grid_basis: str,
    max_interpolation_gap_ms: float,
    min_iou: float = 0.50,
    require_label_match: bool = True,
    fixations_by_stimulus: Mapping[str, pd.DataFrame] | None = None,
    overlap_rule: str = "highest_confidence",
    human_agreement_streams: tuple[str, str] | None = None,
    include_matches: bool = False,
    overwrite: bool = False,
) -> VisusDynamicAOIValidationSuiteRun:
    """Compute, freeze, cross-check, and bind the audited VISUS validation tranche.

    Human-human agreement becomes a required child when the source audit verifies independently
    recoverable streams. When independence is not verified, the suite explicitly records that the
    child is unavailable rather than inferring reliability from the published contributor count.
    """
    identity, model = _verify_intakes(audit, reference_intake, prediction_intake)
    stream = str(reference_stream_id).strip()
    if not stream:
        raise ValueError("reference_stream_id cannot be empty.")
    if stream not in reference_intake.by_stream:
        raise BenchmarkIntegrityError("Selected VISUS reference stream is absent from canonical intake.")

    ready = bool(
        audit.report.get("annotation_provenance", {}).get("human_human_agreement_ready") is True
        and audit.spec.independent_annotation_streams_verified is True
    )
    if ready and human_agreement_streams is None:
        raise BenchmarkIntegrityError(
            "Verified independent VISUS streams are available; a complete suite must include "
            "human-human agreement."
        )
    if not ready and human_agreement_streams is not None:
        raise BenchmarkIntegrityError(
            "VISUS human-human agreement is blocked because independent streams are not verified."
        )

    pair: tuple[str, str] | None = None
    if human_agreement_streams is not None:
        left, right = (str(value).strip() for value in human_agreement_streams)
        if not left or not right or left == right:
            raise ValueError("human_agreement_streams must contain two distinct non-empty IDs.")
        if left not in reference_intake.by_stream or right not in reference_intake.by_stream:
            raise BenchmarkIntegrityError("Human-agreement streams are absent from canonical intake.")
        pair = (left, right)

    output = Path(output_dir)
    report_paths = _target_paths(output, include_human_agreement=pair is not None)
    manifest_path = output / _SUITE_MANIFEST_NAME
    _preflight(report_paths, manifest_path, overwrite=overwrite)

    model_run = run_visus_dynamic_aoi_model_validation(
        audit,
        predicted_by_stimulus=prediction_intake.by_stimulus,
        reference_by_stimulus=reference_intake.by_stream[stream],
        timestamps_by_stimulus=timestamps_by_stimulus,
        reference_stream_id=stream,
        model_name=str(model["name"]),
        model_version=str(model["version"]),
        timestamp_grid_basis=timestamp_grid_basis,
        max_interpolation_gap_ms=max_interpolation_gap_ms,
        min_iou=min_iou,
        require_label_match=require_label_match,
        fixations_by_stimulus=fixations_by_stimulus,
        overlap_rule=overlap_rule,
        include_matches=include_matches,
    )

    reports: dict[str, dict[str, Any]] = {
        "human_reference_intake": reference_intake.report,
        "model_prediction_intake": prediction_intake.report,
        "model_human_validation": model_run.report,
    }
    human_run = None
    if pair is not None:
        human_run = run_visus_dynamic_aoi_human_agreement(
            audit,
            left_by_stimulus=reference_intake.by_stream[pair[0]],
            right_by_stimulus=reference_intake.by_stream[pair[1]],
            timestamps_by_stimulus=timestamps_by_stimulus,
            left_stream_id=pair[0],
            right_stream_id=pair[1],
            timestamp_grid_basis=timestamp_grid_basis,
            max_interpolation_gap_ms=max_interpolation_gap_ms,
            min_iou=min_iou,
            require_label_match=require_label_match,
            fixations_by_stimulus=fixations_by_stimulus,
            overlap_rule=overlap_rule,
            include_matches=include_matches,
        )
        reports[_HUMAN_AGREEMENT_NAME] = human_run.report

    for name, report in reports.items():
        _report_fingerprint(report, name=name)
        benchmark_report = name in {"model_human_validation", _HUMAN_AGREEMENT_NAME}
        if _child_source_identity(report, benchmark_report=benchmark_report) != identity:
            raise BenchmarkIntegrityError(f"VISUS suite child {name!r} source identity mismatch.")

    model_protocol = model_run.report["protocol"]
    protocol = {
        "reference_stream_id": stream,
        "model_name": str(model["name"]),
        "model_version": str(model["version"]),
        "model_artifact_sha256": model.get("artifact_sha256"),
        "timestamp_grid_basis": str(timestamp_grid_basis),
        "timestamp_grids": model_protocol["timestamp_grids"],
        "max_interpolation_gap_ms": float(max_interpolation_gap_ms),
        "min_iou": float(min_iou),
        "require_label_match": bool(require_label_match),
        "fixation_assignment_enabled": fixations_by_stimulus is not None,
        "independent_annotation_streams_verified": ready,
        "human_human_agreement_included": pair is not None,
        "human_agreement_stream_ids": [] if pair is None else list(pair),
        "human_human_unavailable_reason": (
            None
            if ready
            else "source audit does not verify separately recoverable independent annotation streams"
        ),
        "prediction_emission_grid_used": False,
        "completion_rule": "manifest_written_only_after_all_required_child_reports_freeze_and_revalidate",
        "claim_limits": [
            "Suite completion records reproducibility, not generalizable detector validity.",
            "Human agreement is included only when independent streams are source-audit verified.",
            "Neither human stream is treated as error-free ground truth.",
            "No empirical VISUS claim exists until real authoritative inputs are reviewed and frozen.",
        ],
    }
    source = {
        "dataset_name": audit.spec.dataset_name,
        "dataset_version": audit.spec.dataset_version,
        **identity,
        "human_reference_intake_fingerprint_sha256": reference_intake.report[
            "report_fingerprint_sha256"
        ],
        "model_prediction_intake_fingerprint_sha256": prediction_intake.report[
            "report_fingerprint_sha256"
        ],
    }

    for name, report in reports.items():
        _validate_child_semantics(name, report, source_identity=identity, protocol=protocol)
    for name, report in reports.items():
        freeze_benchmark_report(report, report_paths[name], overwrite=overwrite)

    records = [
        {
            "name": name,
            "path": report_paths[name].name,
            "report_fingerprint_sha256": reports[name]["report_fingerprint_sha256"],
        }
        for name in sorted(reports)
    ]
    body = {
        "suite": _SUITE_NAME,
        "status": "complete",
        "source": source,
        "protocol": protocol,
        "reports": records,
    }
    suite_fingerprint = benchmark_fingerprint(body)
    manifest = {**body, "suite_fingerprint_sha256": suite_fingerprint}
    output.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    validate_visus_dynamic_aoi_suite_manifest(manifest_path, verify_reports=True)
    return VisusDynamicAOIValidationSuiteRun(
        output_dir=output,
        report_paths=report_paths,
        reports=reports,
        manifest_path=manifest_path,
        manifest=manifest,
        suite_fingerprint_sha256=suite_fingerprint,
    )
