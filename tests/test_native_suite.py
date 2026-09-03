from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.native_event import NativeEventBenchmarkSpec
from gazeforge.native_suite import (
    run_native_event_validation_suite,
    validate_native_event_suite_manifest,
)


def _paired_native_data() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    step_ms = 1000.0 / 60.0
    for participant in range(4):
        for trial in range(2):
            x = 400.0 + participant * 20.0
            y = 300.0 + trial * 15.0
            base_rows: list[dict[str, object]] = []
            for sample in range(36):
                phase = (sample // 6) % 2
                event_label = "fixation" if phase == 0 else "saccade"
                if sample == 17:
                    event_label = "undefined"
                if phase == 1:
                    x += 24.0
                else:
                    x += 0.5
                base_rows.append(
                    {
                        "participant": f"P{participant + 1}",
                        "trial": f"T{trial + 1}",
                        "time_ms": sample * step_ms,
                        "gaze_x": x,
                        "gaze_y": y + np.sin(sample / 4.0),
                        "manual_label": event_label,
                    }
                )
            for annotator in ("expert-a", "expert-b"):
                for sample, row in enumerate(base_rows):
                    copied = dict(row)
                    copied["annotator"] = annotator
                    if annotator == "expert-b" and sample in {11, 23}:
                        copied["manual_label"] = (
                            "fixation"
                            if copied["manual_label"] == "saccade"
                            else "saccade"
                        )
                    rows.append(copied)
    return pd.DataFrame(rows)


def _spec() -> NativeEventBenchmarkSpec:
    return NativeEventBenchmarkSpec(
        name="native-suite-test",
        version="test-1",
        source="synthetic-unit-test-only",
        license="test-only",
        tracker_model="GP3-class test fixture",
        expected_sampling_rate_hz=60.0,
        dataset_status="empirical",
        annotation_origin="expert-manual",
        human_annotator_count=2,
        reference_description="Synthetic expert-like streams for software tests only.",
        column_map={
            "participant_id": "participant",
            "trial_id": "trial",
            "timestamp_ms": "time_ms",
            "x_px": "gaze_x",
            "y_px": "gaze_y",
            "event_label": "manual_label",
            "annotator_id": "annotator",
        },
        analysis_excluded_labels=("undefined",),
        notes=["Synthetic fixture; not empirical validation evidence."],
    )


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    data_path = tmp_path / "native.csv"
    spec_path = tmp_path / "spec.json"
    _paired_native_data().to_csv(data_path, index=False)
    spec_path.write_text(
        json.dumps(_spec().to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return data_path, spec_path


def _run_suite(tmp_path: Path):
    data_path, spec_path = _write_inputs(tmp_path)
    return run_native_event_validation_suite(
        data_path,
        spec_path,
        tmp_path / "suite",
        primary_annotator="expert-a",
        sensitivity_annotator="expert-b",
        event_min_iou=0.50,
        n_splits=2,
        ivt_velocity_threshold_px_s=700.0,
        n_estimators=8,
        hidden_layer_sizes=(8,),
        temporal_solver="lbfgs",
        temporal_max_iter=80,
    )


def test_native_event_suite_freezes_three_reports_and_completion_manifest(
    tmp_path: Path,
) -> None:
    run = _run_suite(tmp_path)

    assert set(run.reports) == {
        "human_agreement",
        "primary_annotator_model",
        "annotator_sensitivity_model",
    }
    assert all(path.is_file() for path in run.report_paths.values())
    assert run.manifest_path.is_file()
    assert run.manifest["status"] == "complete"
    assert run.manifest["protocol"]["resampling"] is None
    assert len(run.suite_fingerprint_sha256) == 64

    summary = validate_native_event_suite_manifest(run.output_dir)
    assert summary["status"] == "complete"
    assert summary["report_count"] == 3
    assert summary["reports_verified"] is True
    assert summary["suite_fingerprint_sha256"] == run.suite_fingerprint_sha256


def test_native_event_suite_preflights_existing_outputs(tmp_path: Path) -> None:
    data_path, spec_path = _write_inputs(tmp_path)
    output = tmp_path / "suite"
    output.mkdir()
    (output / "native-human-agreement.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="suite output already exists"):
        run_native_event_validation_suite(
            data_path,
            spec_path,
            output,
            primary_annotator="expert-a",
            sensitivity_annotator="expert-b",
            ivt_velocity_threshold_px_s=700.0,
            n_splits=2,
            n_estimators=8,
            hidden_layer_sizes=(8,),
            temporal_solver="lbfgs",
            temporal_max_iter=80,
        )
    assert not (output / "native-event-suite-manifest.json").exists()


def test_native_event_suite_validator_detects_tampered_child(tmp_path: Path) -> None:
    run = _run_suite(tmp_path)
    child_path = run.report_paths["primary_annotator_model"]
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["metrics"]["analysis_label_counts"]["fixation"] += 1
    child_path.write_text(json.dumps(child, indent=2), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint mismatch"):
        validate_native_event_suite_manifest(run.output_dir)


def test_native_event_suite_rejects_same_annotator(tmp_path: Path) -> None:
    data_path, spec_path = _write_inputs(tmp_path)
    with pytest.raises(ValueError, match="two distinct annotators"):
        run_native_event_validation_suite(
            data_path,
            spec_path,
            tmp_path / "suite",
            primary_annotator="expert-a",
            sensitivity_annotator="expert-a",
            ivt_velocity_threshold_px_s=700.0,
        )


def test_native_event_suite_requires_one_ivt_threshold(tmp_path: Path) -> None:
    data_path, spec_path = _write_inputs(tmp_path)
    with pytest.raises(ValueError, match="exactly one angular or pixel"):
        run_native_event_validation_suite(
            data_path,
            spec_path,
            tmp_path / "suite",
            primary_annotator="expert-a",
            sensitivity_annotator="expert-b",
        )
