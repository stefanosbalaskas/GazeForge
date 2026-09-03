"""Human-human agreement for native-rate manually labelled eye-event corpora."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import BenchmarkDatasetCard, build_benchmark_report
from .evaluation import sample_label_agreement
from .event_evaluation import EventLevelEvaluation, evaluate_sample_event_predictions
from .exceptions import SchemaError
from .native_event import (
    NativeEventBenchmarkSpec,
    NativeEventPreparedBenchmark,
    file_sha256,
    load_native_event_spec,
    load_native_event_table,
    prepare_native_event_benchmark,
)

_KEYS = ("participant_id", "trial_id", "timestamp_ms")
_EXCLUDED_SAMPLE_LABEL = "__excluded_from_analysis__"


@dataclass(slots=True)
class NativeEventAnnotatorAgreementRun:
    """Verified annotation streams, aligned samples, and fingerprinted agreement report."""

    left: NativeEventPreparedBenchmark
    right: NativeEventPreparedBenchmark
    aligned: pd.DataFrame
    left_reference_events: EventLevelEvaluation
    right_reference_events: EventLevelEvaluation
    report: dict[str, Any]


def _json_safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def _verify_same_native_samples(
    left: pd.DataFrame,
    right: pd.DataFrame,
) -> pd.DataFrame:
    """Align two annotation streams and prove they describe the same native gaze samples."""
    required = [*_KEYS, "x_px", "y_px", "event_label"]
    for name, frame in (("left", left), ("right", right)):
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise SchemaError(f"{name} annotator stream is missing columns: {missing}")
        if frame.duplicated(list(_KEYS)).any():
            raise SchemaError(f"{name} annotator stream contains duplicate sample keys.")

    aligned = left[required].merge(
        right[required],
        on=list(_KEYS),
        how="inner",
        suffixes=("_left", "_right"),
        validate="one_to_one",
    )
    if len(aligned) != len(left) or len(aligned) != len(right):
        raise SchemaError(
            "Native annotator agreement requires complete one-to-one sample alignment; "
            f"left_rows={len(left)}, right_rows={len(right)}, aligned_rows={len(aligned)}."
        )
    for coordinate in ("x_px", "y_px"):
        left_values = pd.to_numeric(aligned[f"{coordinate}_left"], errors="coerce").to_numpy(float)
        right_values = pd.to_numeric(aligned[f"{coordinate}_right"], errors="coerce").to_numpy(float)
        if not np.all(np.isclose(left_values, right_values, equal_nan=True, rtol=0.0, atol=1e-9)):
            raise SchemaError(
                "Annotator streams do not contain the same underlying native gaze samples: "
                f"{coordinate} differs after key alignment."
            )
    return aligned.sort_values(list(_KEYS), kind="stable").reset_index(drop=True)


def _analysis_sample_agreement(
    aligned: pd.DataFrame,
    *,
    excluded_labels: tuple[str, ...],
) -> dict[str, Any]:
    excluded = {str(label).strip().lower() for label in excluded_labels}
    left_labels = aligned["event_label_left"].astype(str).str.strip()
    right_labels = aligned["event_label_right"].astype(str).str.strip()
    retained = ~left_labels.str.lower().isin(excluded) & ~right_labels.str.lower().isin(excluded)
    subset = aligned.loc[retained, [*_KEYS, "event_label_left", "event_label_right"]].copy()
    if subset.empty:
        raise SchemaError("No paired samples remain after agreement exclusions.")
    left = subset.rename(columns={"event_label_left": "event_label"})
    right = subset.rename(columns={"event_label_right": "event_label"})
    result = sample_label_agreement(left, right)
    result.update(
        {
            "n_excluded_pairwise_samples": int((~retained).sum()),
            "retained_fraction": float(retained.mean()),
            "excluded_labels": sorted(excluded),
        }
    )
    return result


def _event_metrics(result: EventLevelEvaluation) -> dict[str, Any]:
    return {
        "summary": dict(result.summary),
        "per_class": _json_safe_records(result.per_class),
        "design": dict(result.design),
    }


def run_native_event_annotator_agreement(
    data: pd.DataFrame,
    spec: NativeEventBenchmarkSpec,
    *,
    left_annotator: str,
    right_annotator: str,
    event_min_iou: float = 0.50,
    source_file_name: str | None = None,
    source_file_sha256: str | None = None,
) -> NativeEventAnnotatorAgreementRun:
    """Quantify native sample-label and event-boundary agreement between two human annotators.

    Both annotation streams undergo the same native-rate verification used by model validation.
    Excluded labels are preserved during event segmentation so undefined/noise runs remain hard
    temporal separators rather than being deleted first and joining adjacent events.
    """
    left_name = str(left_annotator).strip()
    right_name = str(right_annotator).strip()
    if not left_name or not right_name:
        raise ValueError("left_annotator and right_annotator must be non-empty.")
    if left_name == right_name:
        raise ValueError("Human-human agreement requires two distinct annotators.")
    if spec.human_annotator_count < 2:
        raise SchemaError(
            "The evidence specification declares fewer than two human annotators."
        )
    if "annotator_id" not in spec.column_map:
        raise SchemaError(
            "Native human-human agreement requires column_map['annotator_id']."
        )
    min_iou = float(event_min_iou)
    if not np.isfinite(min_iou) or not 0.0 <= min_iou <= 1.0:
        raise ValueError("event_min_iou must be finite and in [0, 1].")

    # Preserve excluded labels through native verification and alignment. They are supplied to the
    # event segmenter later, where they remain temporal separators before exclusion.
    verification_spec = replace(spec, analysis_excluded_labels=())
    left = prepare_native_event_benchmark(
        data,
        verification_spec,
        annotator=left_name,
        source_file_name=source_file_name,
        source_file_sha256=source_file_sha256,
    )
    right = prepare_native_event_benchmark(
        data,
        verification_spec,
        annotator=right_name,
        source_file_name=source_file_name,
        source_file_sha256=source_file_sha256,
    )
    left_rate = float(left.preparation_report["observed_sampling_rate_hz"])
    right_rate = float(right.preparation_report["observed_sampling_rate_hz"])
    if not np.isclose(left_rate, right_rate, rtol=1e-9, atol=1e-9):
        raise SchemaError(
            "Annotator streams produced different observed native sampling rates: "
            f"left={left_rate:.6g} Hz, right={right_rate:.6g} Hz."
        )

    aligned = _verify_same_native_samples(left.data, right.data)
    overall_sample = sample_label_agreement(left.data, right.data)
    analysis_sample = _analysis_sample_agreement(
        aligned,
        excluded_labels=spec.analysis_excluded_labels,
    )

    event_input = aligned[[*_KEYS, "event_label_left", "event_label_right"]].copy()
    left_reference_events = evaluate_sample_event_predictions(
        event_input,
        true_label_col="event_label_left",
        predicted_label_col="event_label_right",
        sampling_rate_hz=left_rate,
        excluded_labels=spec.analysis_excluded_labels,
        min_iou=min_iou,
    )
    right_reference_events = evaluate_sample_event_predictions(
        event_input,
        true_label_col="event_label_right",
        predicted_label_col="event_label_left",
        sampling_rate_hz=left_rate,
        excluded_labels=spec.analysis_excluded_labels,
        min_iou=min_iou,
    )

    reference_strength = (
        "expert-human-reference"
        if spec.annotation_origin == "expert-manual"
        else "human-reference"
    )
    card = BenchmarkDatasetCard(
        name=f"{spec.name}-human-agreement",
        version=spec.version,
        source=spec.source,
        license=spec.license,
        task="native-rate human-human sample-label and event-boundary agreement",
        sampling_rates_hz=[left_rate],
        participant_count=int(left.data["participant_id"].nunique()),
        stimulus_count=int(left.data["trial_id"].nunique()),
        split_unit="participant_id",
        validation_scope="native-device-empirical-human-agreement",
        annotation_origin=spec.annotation_origin,
        sampling_origin="native",
        reference_strength=reference_strength,
        human_annotator_count=int(spec.human_annotator_count),
        reference_description=spec.reference_description,
        notes=[
            f"Tracker/device declaration: {spec.tracker_model}.",
            "Both annotation streams passed independent native-rate verification.",
            "Human-human agreement characterizes reference variability; neither annotator is treated as error-free.",
            *spec.notes,
        ],
    )
    protocol = {
        "left_annotator": left_name,
        "right_annotator": right_name,
        "sampling_rate_hz": left_rate,
        "event_min_iou": min_iou,
        "excluded_labels": sorted(
            {str(label).strip().lower() for label in spec.analysis_excluded_labels}
        ),
        "sample_alignment": "complete_one_to_one_participant_trial_timestamp",
        "underlying_gaze_identity_verified": True,
        "resampling": None,
        "source_file_name": source_file_name,
        "source_file_sha256": source_file_sha256,
        "spec_fingerprint_sha256": left.preparation_report["spec_fingerprint_sha256"],
        "left_source_frame_fingerprint_sha256": left.preparation_report[
            "source_frame_fingerprint_sha256"
        ],
        "right_source_frame_fingerprint_sha256": right.preparation_report[
            "source_frame_fingerprint_sha256"
        ],
        "role_note": (
            "Left/right reference designations are bookkeeping only for human-human agreement; "
            "directional event precision/recall are reported in both directions."
        ),
    }
    metrics = {
        "sample_agreement_all_labels": overall_sample,
        "sample_agreement_analysis_labels": analysis_sample,
        "event_agreement_left_as_reference": _event_metrics(left_reference_events),
        "event_agreement_right_as_reference": _event_metrics(right_reference_events),
        "n_aligned_samples": int(len(aligned)),
    }
    report = build_benchmark_report(
        benchmark=card,
        metrics=metrics,
        model={"models": []},
        protocol=protocol,
    )
    return NativeEventAnnotatorAgreementRun(
        left=left,
        right=right,
        aligned=aligned,
        left_reference_events=left_reference_events,
        right_reference_events=right_reference_events,
        report=report,
    )


def run_native_event_file_annotator_agreement(
    data_path: str | Path,
    spec_path: str | Path,
    *,
    left_annotator: str,
    right_annotator: str,
    event_min_iou: float = 0.50,
) -> NativeEventAnnotatorAgreementRun:
    """Load, fingerprint, verify, and compare two native human annotation streams."""
    data_file = Path(data_path)
    spec = load_native_event_spec(spec_path)
    data = load_native_event_table(data_file)
    return run_native_event_annotator_agreement(
        data,
        spec,
        left_annotator=left_annotator,
        right_annotator=right_annotator,
        event_min_iou=event_min_iou,
        source_file_name=data_file.name,
        source_file_sha256=file_sha256(data_file),
    )
