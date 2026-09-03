from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gazeforge.exceptions import SchemaError
from gazeforge.native_event import (
    NativeEventBenchmarkSpec,
    prepare_native_event_benchmark,
    run_native_event_benchmark,
)


def _native_data(*, rate_hz: float = 60.0) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    step_ms = 1000.0 / rate_hz
    for participant in range(4):
        for trial in range(2):
            x = 400.0 + participant * 20.0
            y = 300.0 + trial * 15.0
            for sample in range(36):
                event_label = "fixation" if (sample // 6) % 2 == 0 else "saccade"
                if event_label == "saccade":
                    x += 22.0
                else:
                    x += 0.5
                rows.append(
                    {
                        "participant_id": f"P{participant + 1}",
                        "trial_id": f"T{trial + 1}",
                        "timestamp_ms": sample * step_ms,
                        "x_px": x,
                        "y_px": y + np.sin(sample / 3.0),
                        "pupil": 3.2 + 0.01 * sample,
                        "event_label": event_label,
                    }
                )
    return pd.DataFrame(rows)


def _spec(**overrides: object) -> NativeEventBenchmarkSpec:
    values: dict[str, object] = {
        "name": "GP3-native-events",
        "version": "test-1",
        "source": "synthetic-unit-test-only",
        "license": "test-only",
        "tracker_model": "GP3-class test fixture",
        "expected_sampling_rate_hz": 60.0,
        "annotation_origin": "expert-manual",
        "human_annotator_count": 2,
        "notes": ["Synthetic rows exercise software guardrails only."],
    }
    values.update(overrides)
    return NativeEventBenchmarkSpec(**values)


def test_prepare_native_event_verifies_rate_without_resampling() -> None:
    prepared = prepare_native_event_benchmark(_native_data(), _spec())

    assert prepared.dataset_card.sampling_origin == "native"
    assert prepared.dataset_card.reference_strength == "expert-human-reference"
    assert prepared.preparation_report["native_rate_verified"] is True
    assert prepared.preparation_report["resampling"] is None
    assert prepared.preparation_report["observed_sampling_rate_hz"] == pytest.approx(60.0)
    assert prepared.preparation_report["participant_count"] == 4


def test_prepare_native_event_rejects_rate_incompatible_data() -> None:
    with pytest.raises(SchemaError, match="Native sampling-rate verification failed"):
        prepare_native_event_benchmark(_native_data(rate_hz=30.0), _spec())


def test_template_spec_cannot_generate_empirical_evidence() -> None:
    with pytest.raises(SchemaError, match="Template benchmark specifications"):
        prepare_native_event_benchmark(
            _native_data(),
            _spec(dataset_status="template"),
        )


def test_multiple_annotators_require_explicit_stream_selection() -> None:
    first = _native_data()
    first["annotator"] = "expert-a"
    second = _native_data()
    second["annotator"] = "expert-b"
    data = pd.concat([first, second], ignore_index=True)
    spec = _spec(
        column_map={
            "participant_id": "participant_id",
            "trial_id": "trial_id",
            "timestamp_ms": "timestamp_ms",
            "x_px": "x_px",
            "y_px": "y_px",
            "event_label": "event_label",
            "annotator_id": "annotator",
        }
    )

    with pytest.raises(SchemaError, match="Multiple annotation streams"):
        prepare_native_event_benchmark(data, spec)

    prepared = prepare_native_event_benchmark(data, spec, annotator="expert-b")
    assert prepared.preparation_report["selected_annotator"] == "expert-b"
    assert len(prepared.data) == len(first)


def test_native_event_run_builds_fingerprinted_matched_fold_report() -> None:
    run = run_native_event_benchmark(
        _native_data(),
        _spec(),
        n_splits=2,
        ivt_velocity_threshold_px_s=700.0,
        n_estimators=8,
        hidden_layer_sizes=(8,),
        temporal_solver="lbfgs",
        temporal_max_iter=80,
    )

    models = {row["model"] for row in run.report["metrics"]["summary"]}
    assert models == {"I-VT", "RandomForest", "ContextMLP"}
    assert run.report["benchmark"]["sampling_origin"] == "native"
    assert run.report["protocol"]["native_intake"]["resampling"] is None
    assert run.report["protocol"]["native_intake"]["native_rate_verified"] is True
    assert len(run.report["report_fingerprint_sha256"]) == 64
