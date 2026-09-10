import inspect
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
from test_visus_preexecution_protocol import _FakeRuntime, _fixture, _freeze
from test_visus_protocol_batch import _run as _run_batch

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.visus_intake import prepare_visus_canonical_aoi_intake
from gazeforge.visus_protocol_batch import run_visus_grounded_sam2_protocol_batch
from gazeforge.visus_protocol_validation import (
    run_visus_protocol_bound_validation_suite,
    validate_visus_protocol_bound_validation_run,
)


def _reference(batch):
    rows = []
    for stimulus_id, plan in batch.plans_by_stimulus.items():
        label = plan.labels[0]
        for frame_index in (0, 1):
            rows.append(
                {
                    "source_path": f"aoi/{stimulus_id}.xml",
                    "stimulus_id": stimulus_id,
                    "annotation_stream_id": "published_curated",
                    "frame_index": frame_index,
                    "aoi_id": f"human-{stimulus_id}",
                    "label": label,
                    "xmin": 1.0,
                    "ymin": 1.0,
                    "xmax": 4.0,
                    "ymax": 4.0,
                }
            )
    return prepare_visus_canonical_aoi_intake(
        batch.audit,
        pd.DataFrame(rows),
        extraction_basis="Reviewed fixture extraction from exact audited AOI XML files.",
        frame_index_base=0,
    )


def _case(tmp_path: Path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    reference = _reference(batch)
    run = run_visus_protocol_bound_validation_suite(
        batch,
        reference,
        tmp_path / "validation",
    )
    return run, batch, reference


def _resign(record, field):
    body = {key: value for key, value in record.items() if key != field}
    record[field] = benchmark_fingerprint(body)


def _rewrite_binding(run):
    _resign(run.binding, "binding_fingerprint_sha256")
    run.binding_fingerprint_sha256 = run.binding["binding_fingerprint_sha256"]
    run.binding_path.write_text(
        json.dumps(run.binding, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_protocol_bound_validation_runs_existing_suite_from_frozen_settings(tmp_path):
    run, batch, _ = _case(tmp_path)

    protocol = run.suite.manifest["protocol"]
    handoff = batch.report["frozen_evaluation_handoff"]
    assert protocol["reference_stream_id"] == handoff["reference_stream_id"]
    assert protocol["timestamp_grid_basis"] == handoff["timestamp_grid_basis"]
    assert protocol["max_interpolation_gap_ms"] == handoff["max_interpolation_gap_ms"]
    assert protocol["min_iou"] == handoff["min_iou"]
    assert protocol["require_label_match"] == handoff["require_label_match"]
    assert protocol["prediction_emission_grid_used"] is False
    assert run.binding_path.is_file()


def test_protocol_bound_validation_binds_exact_batch_prediction_intake(tmp_path):
    run, batch, _ = _case(tmp_path)

    assert run.binding["protocol_fingerprint_sha256"] == (
        batch.protocol_run.protocol_fingerprint_sha256
    )
    assert run.binding["protocol_batch_fingerprint_sha256"] == batch.batch_fingerprint_sha256
    assert run.binding["prediction_csv_sha256"] == batch.report["prediction_output"]["sha256"]
    assert run.binding["prediction_intake"]["report_fingerprint_sha256"] == (
        batch.prediction_intake.report["report_fingerprint_sha256"]
    )
    assert run.binding["prediction_intake"]["canonical_table_fingerprint_sha256"] == (
        batch.prediction_intake.report["canonical_table_fingerprint_sha256"]
    )
    assert run.suite.manifest["source"]["model_prediction_intake_fingerprint_sha256"] == (
        batch.prediction_intake.report["report_fingerprint_sha256"]
    )


def test_protocol_bound_validation_binds_exact_human_reference_intake(tmp_path):
    run, _, reference = _case(tmp_path)

    assert run.binding["human_reference"]["report_fingerprint_sha256"] == (
        reference.report["report_fingerprint_sha256"]
    )
    assert run.binding["human_reference"]["canonical_table_fingerprint_sha256"] == (
        reference.report["canonical_table_fingerprint_sha256"]
    )
    assert run.binding["human_reference"]["reference_stream_id"] == "published_curated"


def test_protocol_bound_validation_computes_metrics_without_promoting_claims(tmp_path):
    run, _, _ = _case(tmp_path)

    assert run.binding["model_human_validation_executed"] is True
    assert run.binding["diagnostic_match_rows_included"] is True
    assert "matches" in run.suite.reports["model_human_validation"]["metrics"]
    for field in (
        "formal_preregistration_verified",
        "empirical_performance_claim_created",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
        "frozen_evidence_created",
    ):
        assert run.binding[field] is False
    assert run.binding["source_authority_certificate_required_separately"] is True
    assert run.binding["source_authority_certificate_bound_by_this_layer"] is False


def test_protocol_bound_validation_does_not_infer_human_human_agreement(tmp_path):
    run, _, _ = _case(tmp_path)

    assert run.binding["human_human_agreement_executed"] is False
    assert run.binding["human_human_report_fingerprint_sha256"] is None
    assert run.suite.manifest["protocol"]["independent_annotation_streams_verified"] is False
    assert run.suite.manifest["protocol"]["human_human_agreement_included"] is False


def test_public_handoff_api_exposes_no_posthoc_scoring_controls():
    parameters = inspect.signature(run_visus_protocol_bound_validation_suite).parameters
    for forbidden in (
        "reference_stream_id",
        "timestamps_by_stimulus",
        "timestamp_grid_basis",
        "max_interpolation_gap_ms",
        "min_iou",
        "require_label_match",
        "overlap_rule",
        "include_matches",
        "human_agreement_streams",
    ):
        assert forbidden not in parameters


def test_validator_rereads_protocol_bound_batch_prediction_csv(tmp_path):
    run, batch, _ = _case(tmp_path)
    batch.prediction_path.write_bytes(batch.prediction_path.read_bytes() + b"tamper")

    with pytest.raises(BenchmarkIntegrityError, match="prediction CSV bytes drifted"):
        validate_visus_protocol_bound_validation_run(run)


def test_validator_rereads_frozen_preexecution_protocol(tmp_path):
    run, batch, _ = _case(tmp_path)
    payload = json.loads(batch.protocol_run.protocol_path.read_text(encoding="utf-8"))
    payload["evaluation"]["min_iou"] = 0.75
    batch.protocol_run.protocol_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_protocol_bound_validation_run(run)


def test_validator_rereads_binding_manifest_file(tmp_path):
    run, _, _ = _case(tmp_path)
    payload = json.loads(run.binding_path.read_text(encoding="utf-8"))
    payload["status"] = "tampered"
    run.binding_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="binding file drifted"):
        validate_visus_protocol_bound_validation_run(run)


def test_validator_rereads_frozen_suite_children(tmp_path):
    run, _, _ = _case(tmp_path)
    child_path = run.suite.report_paths["model_human_validation"]
    payload = json.loads(child_path.read_text(encoding="utf-8"))
    payload["protocol"]["min_iou"] = 0.75
    child_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        validate_visus_protocol_bound_validation_run(run)


def test_validator_rejects_resigned_suite_setting_drift_from_frozen_protocol(tmp_path):
    run, _, _ = _case(tmp_path)
    manifest = run.suite.manifest
    manifest["protocol"]["min_iou"] = 0.75
    _resign(manifest, "suite_fingerprint_sha256")
    run.suite.suite_fingerprint_sha256 = manifest["suite_fingerprint_sha256"]
    run.suite.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkIntegrityError, match="frozen setting 'min_iou'"):
        validate_visus_protocol_bound_validation_run(run)


def test_validator_rejects_resigned_binding_claim_promotion(tmp_path):
    run, _, _ = _case(tmp_path)
    run.binding["empirical_performance_claim_created"] = True
    _rewrite_binding(run)

    with pytest.raises(BenchmarkIntegrityError, match="current frozen lineage"):
        validate_visus_protocol_bound_validation_run(run)


def test_validator_rejects_resigned_binding_batch_identity_drift(tmp_path):
    run, _, _ = _case(tmp_path)
    run.binding["protocol_batch_fingerprint_sha256"] = "f" * 64
    _rewrite_binding(run)

    with pytest.raises(BenchmarkIntegrityError, match="current frozen lineage"):
        validate_visus_protocol_bound_validation_run(run)


def test_reference_intake_must_share_batch_source_identity(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    reference = _reference(batch)
    reference.report["source_manifest_fingerprint_sha256"] = "e" * 64
    _resign(reference.report, "report_fingerprint_sha256")

    with pytest.raises(BenchmarkIntegrityError, match="does not share"):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            tmp_path / "validation",
        )


def test_reference_intake_must_contain_frozen_reference_stream(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    reference = _reference(batch)
    reference.by_stream = {"different_stream": reference.by_stream["published_curated"]}

    with pytest.raises(BenchmarkIntegrityError, match="keyframe mapping drifted"):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            tmp_path / "validation",
        )


def test_reference_canonical_table_mutation_is_rejected(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    reference = _reference(batch)
    reference.canonical.loc[0, "xmin"] += 0.25

    with pytest.raises(BenchmarkIntegrityError, match="canonical table fingerprint"):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            tmp_path / "validation",
        )


def test_reference_keyframe_mapping_mutation_is_rejected(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    reference = _reference(batch)
    first = reference.by_stream["published_curated"]["S01"][0]
    reference.by_stream["published_curated"]["S01"][0] = replace(first, xmin=1.25)

    with pytest.raises(BenchmarkIntegrityError, match="keyframe mapping drifted"):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            tmp_path / "validation",
        )


def test_prediction_canonical_table_mutation_is_rejected(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    batch.prediction_intake.canonical.loc[0, "xmin"] += 0.25
    reference = _reference(batch)

    with pytest.raises(BenchmarkIntegrityError, match="canonical table fingerprint"):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            tmp_path / "validation",
        )


def test_prediction_keyframe_mapping_mutation_is_rejected(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    first = batch.prediction_intake.by_stimulus["S01"][0]
    batch.prediction_intake.by_stimulus["S01"][0] = replace(first, xmin=first.xmin + 0.25)
    reference = _reference(batch)

    with pytest.raises(BenchmarkIntegrityError, match="keyframe mapping drifted"):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            tmp_path / "validation",
        )


def test_unplanned_fixation_assignment_is_rejected(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    reference = _reference(batch)
    fixations = {
        stimulus: pd.DataFrame({"timestamp_ms": [0.0], "x_px": [2.0], "y_px": [2.0]})
        for stimulus in batch.plans_by_stimulus
    }

    with pytest.raises(BenchmarkIntegrityError, match="frozen pre-execution plan"):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            tmp_path / "validation",
            fixations_by_stimulus=fixations,
        )


def test_planned_fixation_assignment_requires_fixation_inputs(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    audit, plans, timestamps, _ = _fixture(root)
    frozen = _freeze(
        root,
        audit,
        plans,
        timestamps,
        fixation_assignment_planned=True,
    )
    batch = run_visus_grounded_sam2_protocol_batch(
        frozen,
        audit,
        plans,
        root / "batch",
        runtime=_FakeRuntime(),
    )
    reference = _reference(batch)

    with pytest.raises(BenchmarkIntegrityError, match="frozen pre-execution plan"):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            tmp_path / "validation",
        )


def test_planned_fixation_assignment_executes_with_complete_inputs(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    audit, plans, timestamps, _ = _fixture(root)
    frozen = _freeze(
        root,
        audit,
        plans,
        timestamps,
        fixation_assignment_planned=True,
    )
    batch = run_visus_grounded_sam2_protocol_batch(
        frozen,
        audit,
        plans,
        root / "batch",
        runtime=_FakeRuntime(),
    )
    reference = _reference(batch)
    fixations = {
        stimulus: pd.DataFrame(
            {
                "timestamp_ms": [0.0, 40.0],
                "x_px": [2.0, 2.0],
                "y_px": [2.0, 2.0],
            }
        )
        for stimulus in batch.plans_by_stimulus
    }

    run = run_visus_protocol_bound_validation_suite(
        batch,
        reference,
        tmp_path / "validation",
        fixations_by_stimulus=fixations,
    )

    assert run.suite.manifest["protocol"]["fixation_assignment_enabled"] is True
    assert run.binding["frozen_evaluation"]["fixation_assignment_planned"] is True
    assert run.suite.reports["model_human_validation"]["metrics"][
        "fixation_assignment_agreement"
    ] is not None


def test_existing_binding_output_fails_closed_without_overwrite(tmp_path):
    run, batch, reference = _case(tmp_path)

    with pytest.raises(FileExistsError):
        run_visus_protocol_bound_validation_suite(
            batch,
            reference,
            run.output_dir,
        )


def test_explicit_overwrite_recreates_same_binding(tmp_path):
    run, batch, reference = _case(tmp_path)
    first = run.binding_path.read_bytes()

    replacement = run_visus_protocol_bound_validation_suite(
        batch,
        reference,
        run.output_dir,
        overwrite=True,
    )

    assert replacement.binding_path.read_bytes() == first
    assert replacement.binding == run.binding


def test_binding_is_deterministic_across_output_directories(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    reference = _reference(batch)

    first = run_visus_protocol_bound_validation_suite(
        batch,
        reference,
        tmp_path / "first",
    )
    second = run_visus_protocol_bound_validation_suite(
        batch,
        reference,
        tmp_path / "second",
    )

    assert first.binding == second.binding
    assert first.binding_fingerprint_sha256 == second.binding_fingerprint_sha256


def test_output_path_must_be_directory(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    batch, _, _, _, _ = _run_batch(root)
    reference = _reference(batch)
    target = tmp_path / "occupied"
    target.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        run_visus_protocol_bound_validation_suite(batch, reference, target)
