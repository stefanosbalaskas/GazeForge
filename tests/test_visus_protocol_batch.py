import json
from dataclasses import replace
from pathlib import Path

import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.visus_protocol_batch import (
    run_visus_grounded_sam2_protocol_batch,
    validate_visus_protocol_bound_batch_run,
)
from test_visus_preexecution_protocol import _FakeRuntime, _fixture, _freeze


def _resign(record, field):
    body = {key: value for key, value in record.items() if key != field}
    record[field] = benchmark_fingerprint(body)


def _resign_batch(run):
    _resign(run.report, "batch_fingerprint_sha256")
    run.batch_fingerprint_sha256 = run.report["batch_fingerprint_sha256"]
    run.report_path.write_text(
        json.dumps(run.report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run(tmp_path: Path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    runtime = _FakeRuntime()
    batch = run_visus_grounded_sam2_protocol_batch(
        frozen,
        audit,
        plans,
        tmp_path / "batch",
        runtime=runtime,
    )
    return batch, audit, plans, frozen, runtime


def test_batch_executes_complete_frozen_stimulus_set_once(tmp_path):
    batch, _, _, frozen, runtime = _run(tmp_path)

    assert runtime.detect_calls == 11
    assert runtime.propagate_calls == 11
    assert list(batch.per_stimulus) == [f"S{index:02d}" for index in range(1, 12)]
    assert batch.report["protocol_fingerprint_sha256"] == frozen.protocol_fingerprint_sha256
    assert batch.report["execution"]["stimulus_count"] == 11
    assert batch.report["execution"]["all_protocol_bindings_verified"] is True
    assert batch.report["execution"]["all_frame_derivations_mechanically_verified"] is True
    assert len(batch.predictions) == 24
    assert batch.report["prediction_output"]["row_count"] == 24
    assert batch.report["prediction_output"]["track_count"] == 12
    assert batch.prediction_path.is_file()
    assert batch.report_path.is_file()


def test_batch_handoff_uses_existing_prediction_intake_without_evaluation_grid(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)

    assert batch.prediction_intake.report["status"] == "verified-prediction-intake"
    assert batch.prediction_intake.report["evaluation_timestamp_grid_generated"] is False
    assert batch.report["prediction_intake"]["evaluation_timestamp_grid_generated"] is False
    assert batch.report["frozen_evaluation_handoff"]["prediction_emission_grid_used"] is False
    assert batch.report["frozen_evaluation_handoff"]["min_iou"] == pytest.approx(0.50)
    assert batch.report["frozen_evaluation_handoff"]["reference_stream_id"] == (
        "published_curated"
    )


def test_batch_preserves_all_scientific_claim_boundaries(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)

    for field in (
        "formal_preregistration_verified",
        "empirical_performance_claim_created",
        "model_human_validation_executed",
        "human_human_agreement_claimed",
        "dataset_source_authority_promoted",
        "dataset_rights_promoted",
        "frozen_evidence_created",
    ):
        assert batch.report[field] is False


def test_batch_output_is_deterministic_for_same_frozen_inputs(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)

    first = run_visus_grounded_sam2_protocol_batch(
        frozen,
        audit,
        plans,
        tmp_path / "first",
        runtime=_FakeRuntime(),
    )
    second = run_visus_grounded_sam2_protocol_batch(
        frozen,
        audit,
        plans,
        tmp_path / "second",
        runtime=_FakeRuntime(),
    )

    assert first.prediction_path.read_bytes() == second.prediction_path.read_bytes()
    assert first.report == second.report
    assert first.batch_fingerprint_sha256 == second.batch_fingerprint_sha256


def test_batch_rejects_missing_plan_before_backend_execution(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    changed = dict(plans)
    changed.pop("S11")
    runtime = _FakeRuntime()

    with pytest.raises(SchemaError, match="missing"):
        run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            changed,
            tmp_path / "batch",
            runtime=runtime,
        )
    assert runtime.detect_calls == 0
    assert runtime.propagate_calls == 0


def test_batch_rejects_extra_plan_before_backend_execution(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    changed = dict(plans)
    changed["S99"] = replace(changed["S11"], stimulus_id="S99")
    runtime = _FakeRuntime()

    with pytest.raises(SchemaError, match="extra"):
        run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            changed,
            tmp_path / "batch",
            runtime=runtime,
        )
    assert runtime.detect_calls == 0


def test_batch_rejects_wrong_plan_type_before_backend_execution(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    changed = dict(plans)
    changed["S01"] = "not-a-plan"
    runtime = _FakeRuntime()

    with pytest.raises(TypeError, match="VisusGroundedSAM2StimulusPlan"):
        run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            changed,
            tmp_path / "batch",
            runtime=runtime,
        )
    assert runtime.detect_calls == 0


def test_batch_rejects_protocol_file_tamper_before_backend_execution(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    payload = json.loads(frozen.protocol_path.read_text(encoding="utf-8"))
    payload["evaluation"]["min_iou"] = 0.75
    frozen.protocol_path.write_text(json.dumps(payload), encoding="utf-8")
    runtime = _FakeRuntime()

    with pytest.raises(BenchmarkIntegrityError):
        run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            plans,
            tmp_path / "batch",
            runtime=runtime,
        )
    assert runtime.detect_calls == 0
    assert runtime.propagate_calls == 0


def test_batch_rejects_checkpoint_drift_before_backend_execution(tmp_path):
    audit, plans, timestamps, checkpoint = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tamper")
    runtime = _FakeRuntime()

    with pytest.raises(BenchmarkIntegrityError):
        run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            plans,
            tmp_path / "batch",
            runtime=runtime,
        )
    assert runtime.detect_calls == 0


def test_validator_rereads_frozen_protocol_and_current_frame_bytes(tmp_path):
    batch, _, plans, frozen, _ = _run(tmp_path)
    frame = plans["S01"].derivation.frame_dir / "000000.jpg"
    frame.write_bytes(frame.read_bytes() + b"tamper")

    with pytest.raises(BenchmarkIntegrityError):
        validate_visus_protocol_bound_batch_run(batch)

    assert frozen.protocol_path.is_file()


def test_validator_rereads_batch_manifest_file(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    payload = json.loads(batch.report_path.read_text(encoding="utf-8"))
    payload["status"] = "tampered"
    batch.report_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="report file drifted"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_prediction_csv_byte_drift(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    batch.prediction_path.write_bytes(batch.prediction_path.read_bytes() + b"tamper")

    with pytest.raises(BenchmarkIntegrityError, match="prediction CSV bytes drifted"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_in_memory_prediction_table_drift(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    batch.predictions.loc[0, "xmin"] = float(batch.predictions.loc[0, "xmin"]) + 0.25

    with pytest.raises(BenchmarkIntegrityError, match="prediction table drifted"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_reordered_per_stimulus_ledger(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    batch.per_stimulus = dict(reversed(list(batch.per_stimulus.items())))

    with pytest.raises(BenchmarkIntegrityError, match="per-stimulus order drifted"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_recomputed_protocol_binding_to_different_protocol(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    binding = batch.per_stimulus["S01"].protocol_binding
    binding["protocol_fingerprint_sha256"] = "f" * 64
    _resign(binding, "binding_fingerprint_sha256")

    with pytest.raises(BenchmarkIntegrityError, match="different protocol"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_recomputed_protocol_binding_claim_promotion(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    binding = batch.per_stimulus["S01"].protocol_binding
    binding["empirical_performance_claim_created"] = True
    _resign(binding, "binding_fingerprint_sha256")

    with pytest.raises(BenchmarkIntegrityError, match="improperly promotes"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_recomputed_frame_binding_claim_promotion(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    binding = batch.per_stimulus["S01"].frame_derivation_binding
    binding["dataset_rights_implied"] = True
    _resign(binding, "binding_fingerprint_sha256")

    with pytest.raises(BenchmarkIntegrityError, match="improperly promotes"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_recomputed_evaluation_handoff_drift(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    batch.report["frozen_evaluation_handoff"]["min_iou"] = 0.75
    _resign_batch(batch)

    with pytest.raises(BenchmarkIntegrityError, match="evaluation handoff drifted"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_recomputed_source_lineage_drift(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    batch.report["source"]["source_manifest_fingerprint_sha256"] = "e" * 64
    _resign_batch(batch)

    with pytest.raises(BenchmarkIntegrityError, match="source lineage drifted"):
        validate_visus_protocol_bound_batch_run(batch)


def test_validator_rejects_batch_claim_promotion_even_when_resigned(tmp_path):
    batch, _, _, _, _ = _run(tmp_path)
    batch.report["model_human_validation_executed"] = True
    _resign_batch(batch)

    with pytest.raises(BenchmarkIntegrityError, match="cannot promote"):
        validate_visus_protocol_bound_batch_run(batch)


def test_existing_outputs_fail_closed_without_overwrite(tmp_path):
    batch, audit, plans, frozen, _ = _run(tmp_path)
    runtime = _FakeRuntime()

    with pytest.raises(FileExistsError, match="output already exists"):
        run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            plans,
            batch.output_dir,
            runtime=runtime,
        )
    assert runtime.detect_calls == 0


def test_explicit_overwrite_recreates_same_artifacts(tmp_path):
    batch, audit, plans, frozen, _ = _run(tmp_path)
    first_prediction = batch.prediction_path.read_bytes()
    first_report = batch.report
    runtime = _FakeRuntime()

    replacement = run_visus_grounded_sam2_protocol_batch(
        frozen,
        audit,
        plans,
        batch.output_dir,
        runtime=runtime,
        overwrite=True,
    )

    assert runtime.detect_calls == 11
    assert replacement.prediction_path.read_bytes() == first_prediction
    assert replacement.report == first_report


def test_output_path_must_be_a_directory(tmp_path):
    audit, plans, timestamps, _ = _fixture(tmp_path)
    frozen = _freeze(tmp_path, audit, plans, timestamps)
    target = tmp_path / "not-a-directory"
    target.write_text("occupied\n", encoding="utf-8")
    runtime = _FakeRuntime()

    with pytest.raises(NotADirectoryError):
        run_visus_grounded_sam2_protocol_batch(
            frozen,
            audit,
            plans,
            target,
            runtime=runtime,
        )
    assert runtime.detect_calls == 0
