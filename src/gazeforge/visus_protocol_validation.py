"""Protocol-bound handoff from a complete VISUS model batch to the existing validation suite."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError
from .visus_intake import VisusCanonicalAOIIntakeRun
from .visus_protocol_batch import (
    VisusProtocolBoundGroundedSAM2BatchRun,
    validate_visus_protocol_bound_batch_run,
)
from .visus_preexecution_protocol import validation_settings_from_preexecution_protocol
from .visus_suite import (
    VisusDynamicAOIValidationSuiteRun,
    run_visus_dynamic_aoi_validation_suite,
    validate_visus_dynamic_aoi_suite_manifest,
)

_BINDING_SCHEMA = "gazeforge-visus-protocol-bound-validation-v1"
_BINDING_FILENAME = "visus-protocol-bound-validation.json"
_SOURCE_KEYS = (
    "source_audit_report_fingerprint_sha256",
    "source_audit_spec_fingerprint_sha256",
    "source_manifest_fingerprint_sha256",
)


@dataclass(slots=True)
class VisusProtocolBoundValidationRun:
    """Existing VISUS validation suite plus its exact protocol/batch lineage binding."""

    batch: VisusProtocolBoundGroundedSAM2BatchRun
    reference_intake: VisusCanonicalAOIIntakeRun
    suite: VisusDynamicAOIValidationSuiteRun
    output_dir: Path
    binding_path: Path
    binding: dict[str, Any]
    binding_fingerprint_sha256: str


def _valid_sha256(value: Any) -> bool:
    text = str(value).strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _revalidate_fingerprint(
    record: Mapping[str, Any],
    field: str,
    *,
    label: str,
) -> str:
    claimed = str(record.get(field, ""))
    body = {key: value for key, value in record.items() if key != field}
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(f"{label} fingerprint does not revalidate.")
    return claimed


def _source_identity(batch: VisusProtocolBoundGroundedSAM2BatchRun) -> dict[str, str]:
    protocol_source = batch.protocol_run.protocol.get("source")
    if not isinstance(protocol_source, Mapping):
        raise BenchmarkIntegrityError("Frozen VISUS protocol source identity is missing.")
    identity = {key: str(protocol_source.get(key, "")) for key in _SOURCE_KEYS}
    if any(not _valid_sha256(value) for value in identity.values()):
        raise BenchmarkIntegrityError("Frozen VISUS protocol source fingerprints are incomplete.")
    return identity


def _reference_summary(
    batch: VisusProtocolBoundGroundedSAM2BatchRun,
    reference_intake: VisusCanonicalAOIIntakeRun,
) -> dict[str, Any]:
    if not isinstance(reference_intake, VisusCanonicalAOIIntakeRun):
        raise TypeError("reference_intake must be a VisusCanonicalAOIIntakeRun instance.")
    report = reference_intake.report
    if report.get("status") != "verified-canonical-intake":
        raise BenchmarkIntegrityError("VISUS protocol-bound validation requires a verified reference intake.")
    report_fp = _revalidate_fingerprint(
        report,
        "report_fingerprint_sha256",
        label="VISUS human-reference intake",
    )
    identity = _source_identity(batch)
    observed = {key: str(report.get(key, "")) for key in _SOURCE_KEYS}
    if observed != identity:
        raise BenchmarkIntegrityError(
            "VISUS human-reference intake does not share the protocol-bound batch source identity."
        )

    settings = validation_settings_from_preexecution_protocol(batch.protocol_run)
    stream = str(settings["reference_stream_id"])
    if stream not in reference_intake.by_stream:
        raise BenchmarkIntegrityError(
            "Frozen VISUS reference stream is absent from the supplied canonical intake."
        )
    expected_stimuli = list(batch.protocol_run.protocol.get("stimuli", []))
    stimulus_ids = [str(record.get("stimulus_id", "")) for record in expected_stimuli]
    observed_stimuli = sorted(reference_intake.by_stream[stream])
    if observed_stimuli != sorted(stimulus_ids):
        raise BenchmarkIntegrityError(
            "Frozen VISUS reference stream does not exactly cover the protocol stimulus set."
        )
    return {
        "report_fingerprint_sha256": report_fp,
        "input_table_fingerprint_sha256": report.get("input_table_fingerprint_sha256"),
        "canonical_table_fingerprint_sha256": report.get(
            "canonical_table_fingerprint_sha256"
        ),
        "reference_stream_id": stream,
        "annotation_stream_ids": sorted(reference_intake.by_stream),
    }


def _automatic_human_agreement_pair(
    batch: VisusProtocolBoundGroundedSAM2BatchRun,
    reference_intake: VisusCanonicalAOIIntakeRun,
) -> tuple[str, str] | None:
    audit = batch.audit
    ready = bool(
        audit.report.get("annotation_provenance", {}).get("human_human_agreement_ready") is True
        and audit.spec.independent_annotation_streams_verified is True
    )
    if not ready:
        return None
    streams = sorted(reference_intake.by_stream)
    if len(streams) != 2:
        raise BenchmarkIntegrityError(
            "Protocol-bound VISUS validation can automatically select human-human agreement only "
            "when exactly two independently verified canonical streams exist; a larger set must "
            "be frozen explicitly in a future protocol revision."
        )
    return streams[0], streams[1]


def _validate_fixation_plan(
    settings: Mapping[str, Any],
    fixations_by_stimulus: Mapping[str, pd.DataFrame] | None,
) -> None:
    planned = settings.get("fixation_assignment_planned") is True
    supplied = fixations_by_stimulus is not None
    if planned != supplied:
        raise BenchmarkIntegrityError(
            "VISUS fixation-assignment inputs must match the frozen pre-execution plan exactly."
        )


def _timestamp_ledgers_from_protocol(
    batch: VisusProtocolBoundGroundedSAM2BatchRun,
) -> list[dict[str, Any]]:
    evaluation = batch.protocol_run.protocol.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise BenchmarkIntegrityError("Frozen VISUS protocol evaluation section is missing.")
    records = evaluation.get("timestamp_grids")
    if not isinstance(records, list) or not records:
        raise BenchmarkIntegrityError("Frozen VISUS protocol timestamp grids are missing.")
    ledgers: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise BenchmarkIntegrityError("Frozen VISUS timestamp-grid record is malformed.")
        values = record.get("timestamps_ms")
        if not isinstance(values, list) or not values:
            raise BenchmarkIntegrityError("Frozen VISUS timestamp-grid values are missing.")
        ledgers.append(
            {
                "stimulus_id": str(record.get("stimulus_id", "")),
                "n_timestamps": len(values),
                "first_timestamp_ms": float(values[0]),
                "last_timestamp_ms": float(values[-1]),
                "timestamp_grid_fingerprint_sha256": str(
                    record.get("timestamp_grid_fingerprint_sha256", "")
                ),
            }
        )
    return ledgers


def _expected_suite_protocol(
    batch: VisusProtocolBoundGroundedSAM2BatchRun,
    *,
    fixation_assignment_enabled: bool,
    human_pair: tuple[str, str] | None,
) -> dict[str, Any]:
    settings = validation_settings_from_preexecution_protocol(batch.protocol_run)
    model = batch.prediction_intake.report.get("model")
    if not isinstance(model, Mapping):
        raise BenchmarkIntegrityError("VISUS protocol-bound batch model identity is missing.")
    return {
        "reference_stream_id": settings["reference_stream_id"],
        "model_name": model.get("name"),
        "model_version": model.get("version"),
        "timestamp_grid_basis": settings["timestamp_grid_basis"],
        "timestamp_grids": _timestamp_ledgers_from_protocol(batch),
        "max_interpolation_gap_ms": float(settings["max_interpolation_gap_ms"]),
        "min_iou": float(settings["min_iou"]),
        "require_label_match": bool(settings["require_label_match"]),
        "fixation_assignment_enabled": bool(fixation_assignment_enabled),
        "independent_annotation_streams_verified": human_pair is not None,
        "human_human_agreement_included": human_pair is not None,
        "human_agreement_stream_ids": [] if human_pair is None else list(human_pair),
        "prediction_emission_grid_used": False,
    }


def _assert_suite_matches_frozen_protocol(
    batch: VisusProtocolBoundGroundedSAM2BatchRun,
    reference_intake: VisusCanonicalAOIIntakeRun,
    suite: VisusDynamicAOIValidationSuiteRun,
    *,
    fixation_assignment_enabled: bool,
    human_pair: tuple[str, str] | None,
) -> dict[str, Any]:
    verified = validate_visus_dynamic_aoi_suite_manifest(
        suite.manifest_path,
        verify_reports=True,
    )
    if verified["suite_fingerprint_sha256"] != suite.suite_fingerprint_sha256:
        raise BenchmarkIntegrityError(
            "VISUS validation suite object does not match its verified manifest."
        )
    source = verified.get("source")
    protocol = verified.get("protocol")
    if not isinstance(source, Mapping) or not isinstance(protocol, Mapping):
        raise BenchmarkIntegrityError("VISUS validation suite source/protocol sections are missing.")
    identity = _source_identity(batch)
    if {key: str(source.get(key, "")) for key in _SOURCE_KEYS} != identity:
        raise BenchmarkIntegrityError(
            "VISUS validation suite source identity differs from the protocol-bound batch."
        )

    expected = _expected_suite_protocol(
        batch,
        fixation_assignment_enabled=fixation_assignment_enabled,
        human_pair=human_pair,
    )
    for key, value in expected.items():
        if protocol.get(key) != value:
            raise BenchmarkIntegrityError(
                f"VISUS validation suite protocol drifted from the frozen setting {key!r}."
            )

    prediction_fp = batch.prediction_intake.report.get("report_fingerprint_sha256")
    reference_fp = reference_intake.report.get("report_fingerprint_sha256")
    records = {record["name"]: record for record in verified["reports"]}
    if records["model_prediction_intake"]["report_fingerprint_sha256"] != prediction_fp:
        raise BenchmarkIntegrityError(
            "VISUS validation suite is not bound to the protocol-batch prediction intake."
        )
    if records["human_reference_intake"]["report_fingerprint_sha256"] != reference_fp:
        raise BenchmarkIntegrityError(
            "VISUS validation suite is not bound to the supplied human-reference intake."
        )
    return verified


def _binding_body(
    batch: VisusProtocolBoundGroundedSAM2BatchRun,
    reference_summary: Mapping[str, Any],
    suite: VisusDynamicAOIValidationSuiteRun,
    *,
    human_pair: tuple[str, str] | None,
) -> dict[str, Any]:
    settings = validation_settings_from_preexecution_protocol(batch.protocol_run)
    model_human = suite.reports.get("model_human_validation")
    if not isinstance(model_human, Mapping):
        raise BenchmarkIntegrityError("VISUS validation suite is missing model-human results.")
    model_human_fp = str(model_human.get("report_fingerprint_sha256", ""))
    if not _valid_sha256(model_human_fp):
        raise BenchmarkIntegrityError("VISUS model-human report fingerprint is invalid.")
    human_fp = None
    if human_pair is not None:
        human = suite.reports.get("human_human_agreement")
        if not isinstance(human, Mapping):
            raise BenchmarkIntegrityError(
                "VISUS validation suite is missing required human-human agreement."
            )
        human_fp = str(human.get("report_fingerprint_sha256", ""))
        if not _valid_sha256(human_fp):
            raise BenchmarkIntegrityError("VISUS human-human report fingerprint is invalid.")

    return {
        "schema": _BINDING_SCHEMA,
        "status": "verified-protocol-bound-validation",
        "source": _source_identity(batch),
        "protocol_fingerprint_sha256": batch.protocol_run.protocol_fingerprint_sha256,
        "protocol_batch_fingerprint_sha256": batch.batch_fingerprint_sha256,
        "protocol_batch_report_filename": batch.report_path.name,
        "prediction_csv_filename": batch.prediction_path.name,
        "prediction_csv_sha256": batch.report["prediction_output"]["sha256"],
        "prediction_intake_report_fingerprint_sha256": batch.prediction_intake.report[
            "report_fingerprint_sha256"
        ],
        "human_reference": dict(reference_summary),
        "frozen_evaluation": {
            "reference_stream_id": settings["reference_stream_id"],
            "timestamp_grid_basis": settings["timestamp_grid_basis"],
            "timestamp_grid_fingerprints": batch.report["frozen_evaluation_handoff"][
                "timestamp_grid_fingerprints"
            ],
            "max_interpolation_gap_ms": settings["max_interpolation_gap_ms"],
            "min_iou": settings["min_iou"],
            "require_label_match": settings["require_label_match"],
            "fixation_assignment_planned": settings["fixation_assignment_planned"],
            "overlap_rule": settings["overlap_rule"],
            "prediction_emission_grid_used": False,
        },
        "validation_suite_fingerprint_sha256": suite.suite_fingerprint_sha256,
        "model_human_report_fingerprint_sha256": model_human_fp,
        "human_human_report_fingerprint_sha256": human_fp,
        "model_human_validation_executed": True,
        "human_human_agreement_executed": human_pair is not None,
        "diagnostic_match_rows_included": True,
        "source_authority_certificate_required_separately": True,
        "source_authority_certificate_bound_by_this_layer": False,
        "formal_preregistration_verified": False,
        "empirical_performance_claim_created": False,
        "dataset_source_authority_promoted": False,
        "dataset_rights_promoted": False,
        "frozen_evidence_created": False,
        "claim_limits": [
            (
                "This artifact proves that the existing VISUS validation suite consumed the exact "
                "protocol-bound prediction batch and frozen evaluation settings."
            ),
            (
                "Computed model-human metrics are not a publishable empirical claim until the "
                "separate source-authority/rights and scientific-review gates are satisfied."
            ),
            (
                "Human-human agreement is included automatically only when the source audit "
                "verifies exactly two independently recoverable canonical streams."
            ),
            "This layer does not create formal preregistration or Frozen Evidence status.",
        ],
    }


def _write_binding(path: Path, binding: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(binding, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_binding(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise BenchmarkIntegrityError("VISUS protocol-bound validation binding must not be a symlink.")
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError(
            "VISUS protocol-bound validation binding is not valid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "VISUS protocol-bound validation binding must be a JSON object."
        )
    return payload


def run_visus_protocol_bound_validation_suite(
    batch: VisusProtocolBoundGroundedSAM2BatchRun,
    reference_intake: VisusCanonicalAOIIntakeRun,
    output_dir: str | Path,
    *,
    fixations_by_stimulus: Mapping[str, pd.DataFrame] | None = None,
    overwrite: bool = False,
) -> VisusProtocolBoundValidationRun:
    """Run the existing VISUS suite using only settings frozen before model inference.

    No scoring threshold, reference stream, interpolation rule, timestamp grid, or overlap rule is
    accepted as a caller argument here. Those values are recovered from the immutable pre-execution
    protocol carried by ``batch``. Diagnostic match rows are always included. Human-human agreement
    is selected automatically only when exactly two independent streams are source-audit verified.
    """
    batch = validate_visus_protocol_bound_batch_run(batch)
    reference_summary = _reference_summary(batch, reference_intake)
    settings = validation_settings_from_preexecution_protocol(batch.protocol_run)
    _validate_fixation_plan(settings, fixations_by_stimulus)
    human_pair = _automatic_human_agreement_pair(batch, reference_intake)

    output = Path(output_dir)
    if output.exists() and not output.is_dir():
        raise NotADirectoryError(output)
    binding_path = output / _BINDING_FILENAME
    if binding_path.exists() and not overwrite:
        raise FileExistsError(f"VISUS protocol-bound validation output already exists: {binding_path}")

    suite = run_visus_dynamic_aoi_validation_suite(
        batch.audit,
        reference_intake,
        batch.prediction_intake,
        settings["timestamps_by_stimulus"],
        output,
        reference_stream_id=settings["reference_stream_id"],
        timestamp_grid_basis=settings["timestamp_grid_basis"],
        max_interpolation_gap_ms=float(settings["max_interpolation_gap_ms"]),
        min_iou=float(settings["min_iou"]),
        require_label_match=bool(settings["require_label_match"]),
        fixations_by_stimulus=fixations_by_stimulus,
        overlap_rule=settings["overlap_rule"],
        human_agreement_streams=human_pair,
        include_matches=True,
        overwrite=bool(overwrite),
    )
    _assert_suite_matches_frozen_protocol(
        batch,
        reference_intake,
        suite,
        fixation_assignment_enabled=fixations_by_stimulus is not None,
        human_pair=human_pair,
    )

    body = _binding_body(
        batch,
        reference_summary,
        suite,
        human_pair=human_pair,
    )
    binding = {
        **body,
        "binding_fingerprint_sha256": benchmark_fingerprint(body),
    }
    output.mkdir(parents=True, exist_ok=True)
    _write_binding(binding_path, binding)
    run = VisusProtocolBoundValidationRun(
        batch=batch,
        reference_intake=reference_intake,
        suite=suite,
        output_dir=output,
        binding_path=binding_path,
        binding=binding,
        binding_fingerprint_sha256=binding["binding_fingerprint_sha256"],
    )
    return validate_visus_protocol_bound_validation_run(run)


def validate_visus_protocol_bound_validation_run(
    run: VisusProtocolBoundValidationRun,
) -> VisusProtocolBoundValidationRun:
    """Replay every available lineage check for one protocol-bound VISUS validation run."""
    if not isinstance(run, VisusProtocolBoundValidationRun):
        raise TypeError("run must be a VisusProtocolBoundValidationRun instance.")
    batch = validate_visus_protocol_bound_batch_run(run.batch)
    reference_summary = _reference_summary(batch, run.reference_intake)
    settings = validation_settings_from_preexecution_protocol(batch.protocol_run)
    fixation_enabled = settings["fixation_assignment_planned"] is True
    human_pair = _automatic_human_agreement_pair(batch, run.reference_intake)

    binding = run.binding
    if binding.get("schema") != _BINDING_SCHEMA:
        raise BenchmarkIntegrityError("VISUS protocol-bound validation schema drifted.")
    if binding.get("status") != "verified-protocol-bound-validation":
        raise BenchmarkIntegrityError("VISUS protocol-bound validation status drifted.")
    claimed = _revalidate_fingerprint(
        binding,
        "binding_fingerprint_sha256",
        label="VISUS protocol-bound validation binding",
    )
    if claimed != run.binding_fingerprint_sha256:
        raise BenchmarkIntegrityError("VISUS protocol-bound validation fingerprint object drifted.")
    if _load_binding(run.binding_path) != binding:
        raise BenchmarkIntegrityError("VISUS protocol-bound validation binding file drifted.")
    if run.binding_path.name != _BINDING_FILENAME:
        raise BenchmarkIntegrityError("VISUS protocol-bound validation binding filename drifted.")

    _assert_suite_matches_frozen_protocol(
        batch,
        run.reference_intake,
        run.suite,
        fixation_assignment_enabled=fixation_enabled,
        human_pair=human_pair,
    )
    expected = _binding_body(
        batch,
        reference_summary,
        run.suite,
        human_pair=human_pair,
    )
    observed = {key: value for key, value in binding.items() if key != "binding_fingerprint_sha256"}
    if observed != expected:
        raise BenchmarkIntegrityError(
            "VISUS protocol-bound validation binding no longer matches current frozen lineage."
        )
    if binding.get("model_human_validation_executed") is not True:
        raise BenchmarkIntegrityError("VISUS protocol-bound validation lost execution status.")
    for field in (
        "formal_preregistration_verified",
        "empirical_performance_claim_created",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
        "frozen_evidence_created",
    ):
        if binding.get(field) is not False:
            raise BenchmarkIntegrityError(
                f"VISUS protocol-bound validation cannot promote {field}."
            )
    if binding.get("source_authority_certificate_required_separately") is not True:
        raise BenchmarkIntegrityError(
            "VISUS protocol-bound validation cannot bypass the source-authority gate."
        )
    if binding.get("source_authority_certificate_bound_by_this_layer") is not False:
        raise BenchmarkIntegrityError(
            "VISUS protocol-bound validation cannot self-certify source authority."
        )
    return run
