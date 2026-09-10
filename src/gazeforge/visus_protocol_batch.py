"""Complete protocol-bound Grounded-SAM-2 batch assembly for VISUS."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmarks import benchmark_fingerprint
from .exceptions import BenchmarkIntegrityError, SchemaError
from .grounded_sam2 import (
    HuggingFaceGroundedSAM2Runtime,
    grounded_sam2_to_visus_prediction_table,
    validate_grounded_sam2_run,
)
from .provenance import fingerprint_frame
from .visus_audit import VisusSourceAuditRun
from .visus_prediction import (
    VisusDynamicAOIPredictionIntakeRun,
    prepare_visus_dynamic_aoi_predictions,
)
from .visus_preexecution_protocol import (
    VisusGroundedSAM2PreexecutionProtocolRun,
    VisusGroundedSAM2StimulusPlan,
    VisusProtocolBoundGroundedSAM2Run,
    load_visus_grounded_sam2_preexecution_protocol,
    replay_visus_grounded_sam2_preexecution_protocol,
    run_grounded_sam2_from_preexecution_protocol,
)

_BATCH_SCHEMA = "gazeforge-visus-grounded-sam2-protocol-batch-v1"
_PREDICTION_FILENAME = "visus-grounded-sam2-predictions.csv"
_REPORT_FILENAME = "visus-grounded-sam2-protocol-batch.json"


@dataclass(slots=True)
class VisusProtocolBoundGroundedSAM2BatchRun:
    """Complete VISUS model predictions assembled from protocol-bound executions."""

    protocol_run: VisusGroundedSAM2PreexecutionProtocolRun
    audit: VisusSourceAuditRun
    plans_by_stimulus: dict[str, VisusGroundedSAM2StimulusPlan]
    output_dir: Path
    prediction_path: Path
    report_path: Path
    predictions: pd.DataFrame
    prediction_intake: VisusDynamicAOIPredictionIntakeRun
    per_stimulus: dict[str, VisusProtocolBoundGroundedSAM2Run]
    report: dict[str, Any]
    batch_fingerprint_sha256: str


def _file_sha256(path: Path, *, label: str) -> tuple[int, str]:
    if path.is_symlink():
        raise BenchmarkIntegrityError(f"{label} must not be a symbolic link.")
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    if size <= 0:
        raise BenchmarkIntegrityError(f"{label} cannot be empty.")
    return size, digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value).strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _revalidate_fingerprint(record: Mapping[str, Any], field: str, *, label: str) -> str:
    claimed = str(record.get(field, ""))
    body = {key: value for key, value in record.items() if key != field}
    if not _valid_sha256(claimed) or benchmark_fingerprint(body) != claimed:
        raise BenchmarkIntegrityError(f"{label} fingerprint does not revalidate.")
    return claimed


def _load_exact_protocol(
    protocol_run: VisusGroundedSAM2PreexecutionProtocolRun,
) -> dict[str, Any]:
    if not isinstance(protocol_run, VisusGroundedSAM2PreexecutionProtocolRun):
        raise TypeError(
            "protocol_run must be a VisusGroundedSAM2PreexecutionProtocolRun instance."
        )
    loaded = load_visus_grounded_sam2_preexecution_protocol(protocol_run.protocol_path)
    if (
        loaded.protocol_fingerprint_sha256 != protocol_run.protocol_fingerprint_sha256
        or loaded.protocol != protocol_run.protocol
    ):
        raise BenchmarkIntegrityError(
            "Frozen VISUS pre-execution protocol changed before batch execution."
        )
    return loaded.protocol


def _stimulus_ids(protocol: Mapping[str, Any]) -> list[str]:
    records = protocol.get("stimuli")
    if not isinstance(records, list) or not records:
        raise BenchmarkIntegrityError("Frozen VISUS protocol contains no stimulus plans.")
    values = [str(record.get("stimulus_id", "")).strip() for record in records]
    if any(not value for value in values) or len(values) != len(set(values)):
        raise BenchmarkIntegrityError(
            "Frozen VISUS protocol stimulus identities are invalid or duplicated."
        )
    return values


def _timestamps_from_protocol(protocol: Mapping[str, Any]) -> dict[str, list[float]]:
    evaluation = protocol.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise BenchmarkIntegrityError("Frozen VISUS protocol evaluation section is missing.")
    records = evaluation.get("timestamp_grids")
    if not isinstance(records, list) or not records:
        raise BenchmarkIntegrityError("Frozen VISUS protocol timestamp grids are missing.")
    result: dict[str, list[float]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise BenchmarkIntegrityError("Frozen VISUS timestamp-grid record is malformed.")
        stimulus_id = str(record.get("stimulus_id", "")).strip()
        values = record.get("timestamps_ms")
        if not stimulus_id or not isinstance(values, list):
            raise BenchmarkIntegrityError("Frozen VISUS timestamp-grid record is incomplete.")
        result[stimulus_id] = [float(value) for value in values]
    if list(result) != _stimulus_ids(protocol):
        raise BenchmarkIntegrityError(
            "Frozen VISUS timestamp-grid order does not match the stimulus plan."
        )
    return result


def _require_exact_plans(
    plans_by_stimulus: Mapping[str, VisusGroundedSAM2StimulusPlan],
    stimulus_ids: list[str],
) -> None:
    if not isinstance(plans_by_stimulus, Mapping):
        raise TypeError("plans_by_stimulus must be a mapping.")
    observed = {str(key) for key in plans_by_stimulus}
    expected = set(stimulus_ids)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if missing or extra:
        raise SchemaError(
            "Protocol-bound VISUS batch requires exactly one plan for every frozen stimulus: "
            f"missing={missing}, extra={extra}."
        )
    for stimulus_id in stimulus_ids:
        plan = plans_by_stimulus[stimulus_id]
        if not isinstance(plan, VisusGroundedSAM2StimulusPlan):
            raise TypeError(
                f"Plan for {stimulus_id!r} must be a VisusGroundedSAM2StimulusPlan."
            )
        if str(plan.stimulus_id).strip() != stimulus_id:
            raise SchemaError(
                "VISUS batch plan mapping key must equal the plan stimulus_id: "
                f"key={stimulus_id!r}, plan={plan.stimulus_id!r}."
            )


def _preflight_output_dir(output_dir: Path, *, overwrite: bool) -> tuple[Path, Path]:
    prediction_path = output_dir / _PREDICTION_FILENAME
    report_path = output_dir / _REPORT_FILENAME
    if output_dir.exists() and not output_dir.is_dir():
        raise NotADirectoryError(output_dir)
    if not overwrite:
        existing = [path for path in (prediction_path, report_path) if path.exists()]
        if existing:
            raise FileExistsError(
                "VISUS protocol-bound batch output already exists: "
                + ", ".join(str(path) for path in existing)
            )
    output_dir.mkdir(parents=True, exist_ok=True)
    return prediction_path, report_path


def _write_prediction_csv(table: pd.DataFrame, path: Path) -> tuple[int, str]:
    temporary = path.with_name(path.name + ".tmp")
    table.to_csv(temporary, index=False, lineterminator="\n", float_format="%.17g")
    temporary.replace(path)
    return _file_sha256(path, label="VISUS protocol-bound prediction CSV")


def _load_report_file(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise BenchmarkIntegrityError("VISUS protocol batch report must not be a symbolic link.")
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkIntegrityError("VISUS protocol batch report is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("VISUS protocol batch report must be a JSON object.")
    return payload


def _binding_record(
    stimulus_id: str,
    run: VisusProtocolBoundGroundedSAM2Run,
    *,
    expected_protocol_fingerprint: str,
    row_count: int,
    track_count: int,
) -> dict[str, Any]:
    if not isinstance(run, VisusProtocolBoundGroundedSAM2Run):
        raise TypeError(
            f"Protocol-bound execution for {stimulus_id!r} has the wrong run type."
        )
    if run.stimulus_id != stimulus_id:
        raise BenchmarkIntegrityError(
            f"Protocol-bound execution identity mismatch for {stimulus_id!r}."
        )
    validate_grounded_sam2_run(run.backend_run)
    backend_fp = str(run.backend_run.report.get("report_fingerprint_sha256", ""))
    protocol_binding = dict(run.protocol_binding)
    frame_binding = dict(run.frame_derivation_binding)
    protocol_fp = _revalidate_fingerprint(
        protocol_binding,
        "binding_fingerprint_sha256",
        label=f"VISUS protocol binding for {stimulus_id}",
    )
    frame_fp = _revalidate_fingerprint(
        frame_binding,
        "binding_fingerprint_sha256",
        label=f"VISUS frame-derivation binding for {stimulus_id}",
    )
    if protocol_binding.get("protocol_fingerprint_sha256") != expected_protocol_fingerprint:
        raise BenchmarkIntegrityError(
            f"VISUS protocol binding references a different protocol for {stimulus_id!r}."
        )
    if protocol_binding.get("grounded_sam2_report_fingerprint_sha256") != backend_fp:
        raise BenchmarkIntegrityError(
            f"VISUS protocol binding references a different backend run for {stimulus_id!r}."
        )
    if frame_binding.get("grounded_sam2_report_fingerprint_sha256") != backend_fp:
        raise BenchmarkIntegrityError(
            f"VISUS frame binding references a different backend run for {stimulus_id!r}."
        )
    if (
        frame_binding.get("frame_derivation_report_fingerprint_sha256")
        != protocol_binding.get("frame_derivation_report_fingerprint_sha256")
    ):
        raise BenchmarkIntegrityError(
            f"VISUS protocol/frame bindings disagree on derivation identity for {stimulus_id!r}."
        )
    if protocol_binding.get("protocol_validated_before_backend_call") is not True:
        raise BenchmarkIntegrityError(
            f"VISUS batch execution lacks pre-inference protocol validation for {stimulus_id!r}."
        )
    if protocol_binding.get("local_execution_order_verified") is not True:
        raise BenchmarkIntegrityError(
            f"VISUS batch execution lacks local execution-order proof for {stimulus_id!r}."
        )
    if frame_binding.get("frame_derivation_mechanically_verified") is not True:
        raise BenchmarkIntegrityError(
            f"VISUS batch execution lacks mechanical frame derivation for {stimulus_id!r}."
        )
    for field in (
        "formal_preregistration_verified",
        "empirical_performance_claim_created",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
    ):
        if protocol_binding.get(field) is not False:
            raise BenchmarkIntegrityError(
                f"VISUS protocol binding improperly promotes {field} for {stimulus_id!r}."
            )
    for field in (
        "empirical_performance_claim_created",
        "dataset_source_authority_implied",
        "dataset_rights_implied",
        "grounded_sam2_backend_alone_claims_derivation_verification",
    ):
        if frame_binding.get(field) is not False:
            raise BenchmarkIntegrityError(
                f"VISUS frame binding improperly promotes {field} for {stimulus_id!r}."
            )
    return {
        "stimulus_id": stimulus_id,
        "row_count": int(row_count),
        "track_count": int(track_count),
        "grounded_sam2_report_fingerprint_sha256": backend_fp,
        "frame_derivation_report_fingerprint_sha256": frame_binding[
            "frame_derivation_report_fingerprint_sha256"
        ],
        "frame_manifest_fingerprint_sha256": frame_binding[
            "frame_manifest_fingerprint_sha256"
        ],
        "source_video_sha256": frame_binding["source_video_sha256"],
        "frame_derivation_binding_fingerprint_sha256": frame_fp,
        "protocol_binding_fingerprint_sha256": protocol_fp,
    }


def _prediction_basis(protocol_fingerprint: str) -> str:
    return (
        "GazeForge complete protocol-bound Grounding DINO + SAM 2 batch from "
        f"pre-execution protocol {protocol_fingerprint}"
    )


def _source_summary(protocol: Mapping[str, Any]) -> dict[str, Any]:
    source = protocol["source"]
    return {
        "source_audit_report_fingerprint_sha256": source[
            "source_audit_report_fingerprint_sha256"
        ],
        "source_audit_spec_fingerprint_sha256": source[
            "source_audit_spec_fingerprint_sha256"
        ],
        "source_manifest_fingerprint_sha256": source[
            "source_manifest_fingerprint_sha256"
        ],
    }


def _model_summary(protocol: Mapping[str, Any]) -> dict[str, Any]:
    policy = protocol["global_model_policy"]
    return {
        "name": policy["model_name"],
        "version": policy["model_version"],
        "grounding_model_id": policy["grounding_model_id"],
        "grounding_model_revision": policy["grounding_model_revision"],
        "sam2_code_revision": policy["sam2_code_revision"],
        "sam2_model_cfg": policy["sam2_model_cfg"],
        "sam2_checkpoint_sha256": policy["sam2_checkpoint_sha256"],
        "box_threshold": policy["box_threshold"],
        "text_threshold": policy["text_threshold"],
    }


def _evaluation_handoff(protocol: Mapping[str, Any]) -> dict[str, Any]:
    evaluation = protocol["evaluation"]
    return {
        "reference_stream_id": evaluation["reference_stream_id"],
        "timestamp_grid_basis": evaluation["timestamp_grid_basis"],
        "timestamp_grid_fingerprints": [
            {
                "stimulus_id": record["stimulus_id"],
                "timestamp_grid_fingerprint_sha256": record[
                    "timestamp_grid_fingerprint_sha256"
                ],
            }
            for record in evaluation["timestamp_grids"]
        ],
        "max_interpolation_gap_ms": evaluation["max_interpolation_gap_ms"],
        "min_iou": evaluation["min_iou"],
        "require_label_match": evaluation["require_label_match"],
        "fixation_assignment_planned": evaluation["fixation_assignment_planned"],
        "overlap_rule": evaluation["overlap_rule"],
        "prediction_emission_grid_used": False,
    }


def _intake_summary(
    prediction_intake: VisusDynamicAOIPredictionIntakeRun,
) -> dict[str, Any]:
    intake_report = prediction_intake.report
    intake_fp = _revalidate_fingerprint(
        intake_report,
        "report_fingerprint_sha256",
        label="VISUS prediction-intake report",
    )
    return {
        "status": intake_report.get("status"),
        "report_fingerprint_sha256": intake_fp,
        "input_table_fingerprint_sha256": intake_report.get(
            "input_table_fingerprint_sha256"
        ),
        "canonical_table_fingerprint_sha256": intake_report.get(
            "canonical_table_fingerprint_sha256"
        ),
        "complete_audited_stimulus_coverage_required": intake_report.get(
            "complete_audited_stimulus_coverage_required"
        ),
        "evaluation_timestamp_grid_generated": intake_report.get(
            "evaluation_timestamp_grid_generated"
        ),
    }


def _report_body(
    *,
    protocol: Mapping[str, Any],
    protocol_fingerprint: str,
    prediction_path: Path,
    prediction_bytes: int,
    prediction_sha256: str,
    predictions: pd.DataFrame,
    prediction_intake: VisusDynamicAOIPredictionIntakeRun,
    execution_records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": _BATCH_SCHEMA,
        "status": "verified-protocol-bound-batch-output",
        "batch_scope": (
            "complete-frozen-visus-stimulus-set-to-canonical-model-prediction-table"
        ),
        "protocol_fingerprint_sha256": protocol_fingerprint,
        "source": _source_summary(protocol),
        "model": _model_summary(protocol),
        "execution": {
            "stimulus_count": len(execution_records),
            "stimulus_ids": [record["stimulus_id"] for record in execution_records],
            "all_protocol_bindings_verified": True,
            "all_frame_derivations_mechanically_verified": True,
            "records": execution_records,
        },
        "prediction_output": {
            "filename": prediction_path.name,
            "bytes": int(prediction_bytes),
            "sha256": prediction_sha256,
            "row_count": int(len(predictions)),
            "track_count": int(
                predictions[["stimulus_id", "aoi_id"]].drop_duplicates().shape[0]
            ),
            "table_fingerprint_sha256": fingerprint_frame(predictions),
        },
        "prediction_intake": _intake_summary(prediction_intake),
        "frozen_evaluation_handoff": _evaluation_handoff(protocol),
        "formal_preregistration_verified": False,
        "empirical_performance_claim_created": False,
        "model_human_validation_executed": False,
        "human_human_agreement_claimed": False,
        "dataset_source_authority_promoted": False,
        "dataset_rights_promoted": False,
        "frozen_evidence_created": False,
        "claim_limits": [
            (
                "This batch proves complete protocol-bound prediction assembly; it does not "
                "measure model performance."
            ),
            (
                "Prediction emission frames remain separate from the frozen external "
                "model-human evaluation grids."
            ),
            (
                "Source authority, rights, formal preregistration, independent human streams, "
                "model-human validity, and Frozen Evidence remain separate gates."
            ),
        ],
    }


def run_visus_grounded_sam2_protocol_batch(
    protocol_run: VisusGroundedSAM2PreexecutionProtocolRun,
    audit: VisusSourceAuditRun,
    plans_by_stimulus: Mapping[str, VisusGroundedSAM2StimulusPlan],
    output_dir: str | Path,
    *,
    runtime: Any = None,
    overwrite: bool = False,
) -> VisusProtocolBoundGroundedSAM2BatchRun:
    """Execute every frozen VISUS stimulus exactly once and freeze prediction lineage."""
    protocol = _load_exact_protocol(protocol_run)
    stimulus_ids = _stimulus_ids(protocol)
    _require_exact_plans(plans_by_stimulus, stimulus_ids)
    replay_visus_grounded_sam2_preexecution_protocol(
        protocol_run,
        audit,
        plans_by_stimulus,
        _timestamps_from_protocol(protocol),
    )
    prediction_path, report_path = _preflight_output_dir(
        Path(output_dir),
        overwrite=bool(overwrite),
    )

    selected_runtime = runtime
    if selected_runtime is None:
        selected_runtime = HuggingFaceGroundedSAM2Runtime()

    per_stimulus: dict[str, VisusProtocolBoundGroundedSAM2Run] = {}
    tables: list[pd.DataFrame] = []
    execution_records: list[dict[str, Any]] = []
    for stimulus_id in stimulus_ids:
        bound = run_grounded_sam2_from_preexecution_protocol(
            protocol_run,
            audit,
            plans_by_stimulus[stimulus_id],
            runtime=selected_runtime,
        )
        if stimulus_id in per_stimulus:
            raise BenchmarkIntegrityError(
                f"VISUS protocol batch attempted duplicate execution for {stimulus_id!r}."
            )
        table = grounded_sam2_to_visus_prediction_table(
            bound.backend_run,
            stimulus_id=stimulus_id,
        )
        if table.empty:
            raise BenchmarkIntegrityError(
                f"VISUS protocol batch produced no prediction rows for {stimulus_id!r}."
            )
        per_stimulus[stimulus_id] = bound
        tables.append(table)
        execution_records.append(
            _binding_record(
                stimulus_id,
                bound,
                expected_protocol_fingerprint=protocol_run.protocol_fingerprint_sha256,
                row_count=len(table),
                track_count=int(table["aoi_id"].nunique()),
            )
        )

    if list(per_stimulus) != stimulus_ids:
        raise BenchmarkIntegrityError(
            "VISUS protocol batch did not execute the exact frozen stimulus order."
        )
    predictions = pd.concat(tables, ignore_index=True)
    predictions = predictions.sort_values(
        ["stimulus_id", "aoi_id", "frame_index"],
        kind="stable",
    ).reset_index(drop=True)
    observed_stimuli = predictions["stimulus_id"].drop_duplicates().tolist()
    if observed_stimuli != stimulus_ids:
        raise BenchmarkIntegrityError(
            "VISUS protocol batch prediction table does not exactly cover frozen stimuli."
        )

    policy = protocol["global_model_policy"]
    prediction_intake = prepare_visus_dynamic_aoi_predictions(
        audit,
        predictions,
        model_name=policy["model_name"],
        model_version=policy["model_version"],
        prediction_basis=_prediction_basis(protocol_run.protocol_fingerprint_sha256),
        prediction_coordinate_unit=audit.spec.coordinate_unit,
        frame_index_base=int(policy["frame_index_base"]),
        model_artifact_sha256=None,
        require_complete_stimulus_coverage=True,
    )
    if prediction_intake.report.get("evaluation_timestamp_grid_generated") is not False:
        raise BenchmarkIntegrityError(
            "VISUS protocol batch prediction intake generated an evaluation grid."
        )

    prediction_bytes, prediction_sha = _write_prediction_csv(
        predictions,
        prediction_path,
    )
    body = _report_body(
        protocol=protocol,
        protocol_fingerprint=protocol_run.protocol_fingerprint_sha256,
        prediction_path=prediction_path,
        prediction_bytes=prediction_bytes,
        prediction_sha256=prediction_sha,
        predictions=predictions,
        prediction_intake=prediction_intake,
        execution_records=execution_records,
    )
    report = {**body, "batch_fingerprint_sha256": benchmark_fingerprint(body)}
    temporary = report_path.with_name(report_path.name + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(report_path)

    run = VisusProtocolBoundGroundedSAM2BatchRun(
        protocol_run=protocol_run,
        audit=audit,
        plans_by_stimulus={key: plans_by_stimulus[key] for key in stimulus_ids},
        output_dir=Path(output_dir),
        prediction_path=prediction_path,
        report_path=report_path,
        predictions=predictions,
        prediction_intake=prediction_intake,
        per_stimulus=per_stimulus,
        report=report,
        batch_fingerprint_sha256=report["batch_fingerprint_sha256"],
    )
    return validate_visus_protocol_bound_batch_run(run)


def validate_visus_protocol_bound_batch_run(
    run: VisusProtocolBoundGroundedSAM2BatchRun,
) -> VisusProtocolBoundGroundedSAM2BatchRun:
    """Revalidate the batch artifact and all frozen protocol/source/model lineage."""
    if not isinstance(run, VisusProtocolBoundGroundedSAM2BatchRun):
        raise TypeError("run must be a VisusProtocolBoundGroundedSAM2BatchRun instance.")

    protocol = _load_exact_protocol(run.protocol_run)
    stimulus_ids = _stimulus_ids(protocol)
    _require_exact_plans(run.plans_by_stimulus, stimulus_ids)
    replay_visus_grounded_sam2_preexecution_protocol(
        run.protocol_run,
        run.audit,
        run.plans_by_stimulus,
        _timestamps_from_protocol(protocol),
    )

    report = run.report
    if report.get("schema") != _BATCH_SCHEMA:
        raise BenchmarkIntegrityError("VISUS protocol batch schema drifted.")
    if report.get("status") != "verified-protocol-bound-batch-output":
        raise BenchmarkIntegrityError("VISUS protocol batch status drifted.")
    claimed = _revalidate_fingerprint(
        report,
        "batch_fingerprint_sha256",
        label="VISUS protocol batch report",
    )
    if claimed != run.batch_fingerprint_sha256:
        raise BenchmarkIntegrityError("VISUS protocol batch fingerprint object drifted.")
    if _load_report_file(run.report_path) != report:
        raise BenchmarkIntegrityError("VISUS protocol batch report file drifted.")
    if run.report_path.name != _REPORT_FILENAME:
        raise BenchmarkIntegrityError("VISUS protocol batch report filename drifted.")
    if run.prediction_path.name != _PREDICTION_FILENAME:
        raise BenchmarkIntegrityError("VISUS protocol batch prediction filename drifted.")

    if report.get("protocol_fingerprint_sha256") != run.protocol_run.protocol_fingerprint_sha256:
        raise BenchmarkIntegrityError("VISUS protocol batch protocol identity drifted.")
    if report.get("source") != _source_summary(protocol):
        raise BenchmarkIntegrityError("VISUS protocol batch source lineage drifted.")
    if report.get("model") != _model_summary(protocol):
        raise BenchmarkIntegrityError("VISUS protocol batch model policy drifted.")
    if report.get("frozen_evaluation_handoff") != _evaluation_handoff(protocol):
        raise BenchmarkIntegrityError("VISUS protocol batch evaluation handoff drifted.")

    for field in (
        "formal_preregistration_verified",
        "empirical_performance_claim_created",
        "model_human_validation_executed",
        "human_human_agreement_claimed",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
        "frozen_evidence_created",
    ):
        if report.get(field) is not False:
            raise BenchmarkIntegrityError(f"VISUS protocol batch cannot promote {field}.")

    output = report.get("prediction_output")
    execution = report.get("execution")
    intake_summary = report.get("prediction_intake")
    if not all(isinstance(value, Mapping) for value in (output, execution, intake_summary)):
        raise BenchmarkIntegrityError("VISUS protocol batch report sections are missing.")
    assert isinstance(output, Mapping)
    assert isinstance(execution, Mapping)
    assert isinstance(intake_summary, Mapping)

    if execution.get("stimulus_count") != len(stimulus_ids):
        raise BenchmarkIntegrityError("VISUS protocol batch stimulus count drifted.")
    if list(execution.get("stimulus_ids", [])) != stimulus_ids:
        raise BenchmarkIntegrityError("VISUS protocol batch stimulus order drifted.")
    if execution.get("all_protocol_bindings_verified") is not True:
        raise BenchmarkIntegrityError("VISUS protocol batch lost protocol-binding verification.")
    if execution.get("all_frame_derivations_mechanically_verified") is not True:
        raise BenchmarkIntegrityError("VISUS protocol batch lost frame-derivation verification.")
    if list(run.per_stimulus) != stimulus_ids:
        raise BenchmarkIntegrityError("VISUS protocol batch per-stimulus order drifted.")

    size, digest = _file_sha256(
        run.prediction_path,
        label="VISUS protocol-bound prediction CSV",
    )
    if size != output.get("bytes") or digest != output.get("sha256"):
        raise BenchmarkIntegrityError("VISUS protocol batch prediction CSV bytes drifted.")
    if fingerprint_frame(run.predictions) != output.get("table_fingerprint_sha256"):
        raise BenchmarkIntegrityError("VISUS protocol batch prediction table drifted.")
    if len(run.predictions) != output.get("row_count"):
        raise BenchmarkIntegrityError("VISUS protocol batch prediction row count drifted.")
    observed_tracks = int(
        run.predictions[["stimulus_id", "aoi_id"]].drop_duplicates().shape[0]
    )
    if observed_tracks != output.get("track_count"):
        raise BenchmarkIntegrityError("VISUS protocol batch prediction track count drifted.")
    if run.predictions["stimulus_id"].drop_duplicates().tolist() != stimulus_ids:
        raise BenchmarkIntegrityError("VISUS protocol batch prediction coverage/order drifted.")

    records = execution.get("records")
    if not isinstance(records, list) or len(records) != len(stimulus_ids):
        raise BenchmarkIntegrityError("VISUS protocol batch execution ledger drifted.")
    record_ids = [str(record.get("stimulus_id", "")) for record in records]
    if record_ids != stimulus_ids:
        raise BenchmarkIntegrityError("VISUS protocol batch execution identities drifted.")
    for stimulus_id, stored in zip(stimulus_ids, records, strict=True):
        subset = run.predictions.loc[run.predictions["stimulus_id"] == stimulus_id]
        observed = _binding_record(
            stimulus_id,
            run.per_stimulus[stimulus_id],
            expected_protocol_fingerprint=run.protocol_run.protocol_fingerprint_sha256,
            row_count=len(subset),
            track_count=int(subset["aoi_id"].nunique()),
        )
        if observed != stored:
            raise BenchmarkIntegrityError(
                f"VISUS protocol batch lineage drifted for {stimulus_id!r}."
            )

    intake = run.prediction_intake.report
    if _intake_summary(run.prediction_intake) != dict(intake_summary):
        raise BenchmarkIntegrityError("VISUS protocol batch prediction-intake summary drifted.")
    if intake.get("input_table_fingerprint_sha256") != fingerprint_frame(run.predictions):
        raise BenchmarkIntegrityError(
            "VISUS protocol batch prediction intake is not bound to the batch table."
        )
    if intake.get("source_audit_report_fingerprint_sha256") != _source_summary(protocol)[
        "source_audit_report_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError("VISUS protocol batch intake source audit drifted.")
    if intake.get("source_audit_spec_fingerprint_sha256") != _source_summary(protocol)[
        "source_audit_spec_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError("VISUS protocol batch intake source specification drifted.")
    if intake.get("source_manifest_fingerprint_sha256") != _source_summary(protocol)[
        "source_manifest_fingerprint_sha256"
    ]:
        raise BenchmarkIntegrityError("VISUS protocol batch intake source manifest drifted.")
    policy = protocol["global_model_policy"]
    if intake.get("model", {}).get("name") != policy["model_name"]:
        raise BenchmarkIntegrityError("VISUS protocol batch intake model name drifted.")
    if intake.get("model", {}).get("version") != policy["model_version"]:
        raise BenchmarkIntegrityError("VISUS protocol batch intake model version drifted.")
    if intake.get("stimulus_ids") != stimulus_ids:
        raise BenchmarkIntegrityError("VISUS protocol batch intake stimulus coverage drifted.")
    if intake.get("row_count") != len(run.prediction_intake.canonical):
        raise BenchmarkIntegrityError("VISUS protocol batch intake row count drifted.")
    if intake.get("complete_audited_stimulus_coverage_required") is not True:
        raise BenchmarkIntegrityError(
            "VISUS protocol batch prediction intake lost complete-coverage enforcement."
        )
    if intake.get("evaluation_timestamp_grid_generated") is not False:
        raise BenchmarkIntegrityError(
            "VISUS protocol batch prediction intake cannot generate the evaluation grid."
        )
    return run
