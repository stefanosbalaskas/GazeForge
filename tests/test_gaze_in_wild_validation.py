import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.io import savemat

from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError
from gazeforge.gaze_in_wild_audit import (
    GazeInWildLabelFileRecord,
    GazeInWildProcessFileRecord,
    GazeInWildSourceAuditSpec,
    audit_gaze_in_wild_source,
)
from gazeforge.gaze_in_wild_validation import (
    prepare_gaze_in_wild_benchmark,
    run_gaze_in_wild_model_validation,
)


def _write_process(path: Path, *, n: int = 60) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = np.arange(n, dtype=float)
    por = np.vstack([300.0 + 2.0 * sample, 200.0 + np.sin(sample / 5.0) * 20.0])
    confidence = np.ones(n, dtype=float)
    savemat(path, {"ProcessData": {"ETG": {"POR": por, "Confidence": confidence}}})


def _write_label(path: Path, *, labeller: int, rate_hz: float, n: int = 60) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = np.concatenate(
        [
            np.full(20, 1, dtype=int),
            np.full(20, 3, dtype=int),
            np.full(20, 2, dtype=int),
        ]
    )
    times = np.arange(n, dtype=float) / rate_hz
    savemat(path, {"LabelData": {"T": times, "Labels": labels, "LbrIdx": labeller}})


def _digest(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def _fixture(
    root: Path,
    *,
    coordinate_unit: str = "pixels",
    pixel_kinematics_compatible: bool = True,
):
    label_root = root / "LabelData"
    process_root = root / "ProcessData"
    rates = {"P01": 120.0, "P02": 100.0, "P03": 90.0}
    label_records = []
    process_records = []
    for participant, rate in rates.items():
        process_relative = f"{participant}_task.mat"
        label_relative = f"{participant}_task_Lbr_1.mat"
        _write_process(process_root / process_relative)
        _write_label(label_root / label_relative, labeller=1, rate_hz=rate)
        process_digest, process_bytes = _digest(process_root / process_relative)
        label_digest, label_bytes = _digest(label_root / label_relative)
        process_records.append(
            GazeInWildProcessFileRecord(
                path=process_relative,
                sha256=process_digest,
                bytes=process_bytes,
            )
        )
        label_records.append(
            GazeInWildLabelFileRecord(
                path=label_relative,
                sha256=label_digest,
                bytes=label_bytes,
                participant_id=participant,
                trial_id="task",
                labeller_id=1,
                process_path=process_relative,
            )
        )

    spec = GazeInWildSourceAuditSpec(
        dataset_name="Gaze-in-the-Wild",
        dataset_version="validation-fixture",
        source="https://example.invalid/gaze-in-wild",
        source_revision="fixture-revision",
        license="Verified research-use terms for fixture only.",
        reuse_terms_source="https://example.invalid/terms",
        dataset_status="empirical",
        reuse_terms_verified=True,
        analysis_use_permitted=True,
        redistribution_status="restricted",
        participant_mapping_verified=True,
        participant_mapping_basis="Fixture manifest.",
        coordinate_unit=coordinate_unit,
        coordinate_unit_verified=True,
        coordinate_verification_basis="Fixture coordinate declaration.",
        pixel_kinematics_compatible=pixel_kinematics_compatible,
        label_files=label_records,
        process_files=process_records,
    )
    return audit_gaze_in_wild_source(label_root, process_root, spec)


def _task_mapping() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P01", "P02", "P03"],
            "trial_id": ["task", "task", "task"],
            "task_label": ["indoor", "outdoor", "indoor"],
        }
    )


def test_prepare_gaze_in_wild_uses_each_file_rate_before_common_downsampling(tmp_path):
    audit = _fixture(tmp_path)
    prepared = prepare_gaze_in_wild_benchmark(
        audit,
        labeller_id=1,
        target_sampling_rate_hz=60.0,
        min_label_purity=0.60,
        task_mapping=_task_mapping(),
    )

    report = prepared.preparation_report
    assert report["source_sampling_rates_hz"] == pytest.approx([90.0, 100.0, 120.0])
    assert report["analysis_sampling_rate_hz"] == 60.0
    assert report["sampling_origin"] == "resampled"
    assert report["participant_count"] == 3
    assert report["ambiguous_rows"] >= 0
    assert prepared.dataset_card.reference_strength == "derived-human-reference"
    assert set(prepared.data["analysis_sampling_rate_hz"]) == {60.0}
    assert set(prepared.data["task_label"]) == {"indoor", "outdoor"}
    assert len(report["task_mapping"]["mapping_fingerprint_sha256"]) == 64
    assert report["task_mapping"]["task_labels_inferred_from_filenames"] is False
    assert all(
        item["resampling"]["invalid_source_samples_are_not_bridged"]
        for item in report["files"]
    )


def test_model_validation_is_participant_disjoint_and_reports_class_and_task_sensitivity(tmp_path):
    audit = _fixture(tmp_path)
    run = run_gaze_in_wild_model_validation(
        audit,
        labeller_id=1,
        target_sampling_rate_hz=60.0,
        min_label_purity=0.60,
        task_mapping=_task_mapping(),
        n_splits=3,
        n_estimators=20,
        hidden_layer_sizes=(8,),
        temporal_solver="lbfgs",
        temporal_max_iter=80,
        calibration_bins=4,
    )

    assert set(run.comparison.summary["model"]) == {"I-VT", "RandomForest", "ContextMLP"}
    assert run.comparison.design["group_col"] == "participant_id"
    assert run.comparison.design["n_splits"] == 3
    assert len(run.paired_model_differences.summary) > 0
    assert set(run.sample_event_class_performance["event_label"]) == {
        "fixation",
        "pursuit",
        "saccade",
    }
    assert not run.event_class_performance.empty
    assert run.task_performance is not None
    assert run.task_performance.design["models_refit_by_stratum"] is False
    assert run.report["protocol"]["event_class_sensitivity"]["models_refit_by_event_class"] is False
    assert len(run.report["report_fingerprint_sha256"]) == 64

    for _, part in run.comparison.predictions.groupby("comparison_model"):
        counts = part.groupby("participant_id")["validation_fold"].nunique()
        assert counts.max() == 1


def test_prepare_rejects_upsampling_any_selected_file(tmp_path):
    audit = _fixture(tmp_path)
    with pytest.raises(SchemaError, match="refuses upsampling"):
        prepare_gaze_in_wild_benchmark(
            audit,
            labeller_id=1,
            target_sampling_rate_hz=110.0,
        )


def test_prepare_requires_verified_pixel_kinematics_compatibility(tmp_path):
    audit = _fixture(
        tmp_path,
        coordinate_unit="normalized",
        pixel_kinematics_compatible=False,
    )
    with pytest.raises(SchemaError, match="pixel-kinematics"):
        prepare_gaze_in_wild_benchmark(audit, labeller_id=1)


def test_task_mapping_must_exactly_cover_selected_trials(tmp_path):
    audit = _fixture(tmp_path)
    incomplete = _task_mapping().iloc[:2].copy()
    with pytest.raises(SchemaError, match="exactly cover"):
        prepare_gaze_in_wild_benchmark(
            audit,
            labeller_id=1,
            task_mapping=incomplete,
        )


def test_model_preparation_revalidates_source_audit_fingerprint(tmp_path):
    audit = _fixture(tmp_path)
    audit.report["identity"]["participant_count"] = 999
    with pytest.raises(BenchmarkIntegrityError, match="fingerprint"):
        prepare_gaze_in_wild_benchmark(audit, labeller_id=1)
