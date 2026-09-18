"""Run the shortest package-wide GazeForge tour.

This deterministic example shows how one gaze table moves through the core public
workflow: canonicalisation, non-destructive QC, transparent eye-event labelling,
researcher-defined AOIs, semantic scanpaths, and provenance. The generated bundle
uses synthetic/demo data and is not empirical validation evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from gazeforge import (
    AOI,
    AuditTrail,
    __version__,
    ai_flag_anomalies,
    aois_to_frame,
    canonicalize_gaze,
    fingerprint_frame,
    ivt_classify_events,
    map_fixations_to_aois,
    samples_to_event_intervals,
    score_trial_quality,
    simulate_gaze,
    to_semantic_scanpaths,
)

SAMPLING_RATE_HZ = 60.0
SCREEN_SIZE_PX = (1920, 1080)
EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"


def _fixation_centroids(
    event_samples: pd.DataFrame,
    event_intervals: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    fixations = event_intervals.loc[event_intervals["event_label"] == "fixation"]

    for event in fixations.itertuples(index=False):
        samples = event_samples.loc[
            (event_samples["participant_id"] == event.participant_id)
            & (event_samples["trial_id"] == event.trial_id)
            & (event_samples["timestamp_ms"] >= event.start_ms)
            & (event_samples["timestamp_ms"] < event.end_ms)
        ]
        x = pd.to_numeric(samples["x_px"], errors="coerce")
        y = pd.to_numeric(samples["y_px"], errors="coerce")
        valid = x.notna() & y.notna()
        if not valid.any():
            continue
        rows.append(
            {
                "participant_id": event.participant_id,
                "trial_id": event.trial_id,
                "event_index": int(event.event_index),
                "start_ms": float(event.start_ms),
                "end_ms": float(event.end_ms),
                "duration_ms": float(event.duration_ms),
                "n_samples": int(event.n_samples),
                "x_px": float(x[valid].mean()),
                "y_px": float(y[valid].mean()),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "participant_id",
            "trial_id",
            "event_index",
            "start_ms",
            "end_ms",
            "duration_ms",
            "n_samples",
            "x_px",
            "y_px",
        ],
    )


def _demo_aois() -> list[AOI]:
    return [
        AOI("header", "header", 0, 0, 1920, 260, source="researcher_defined"),
        AOI("left", "left panel", 0, 260, 820, 1080, source="researcher_defined"),
        AOI("main", "main content", 820, 260, 1920, 1080, source="researcher_defined"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("gazeforge-tour-demo"),
        help="Directory for the small reviewable tour bundle.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source = simulate_gaze(
        n_participants=2,
        n_trials=1,
        samples_per_trial=120,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        screen_size_px=SCREEN_SIZE_PX,
        random_state=7,
    )
    source_snapshot = source.copy(deep=True)
    source_fingerprint = fingerprint_frame(source_snapshot)
    trail = AuditTrail()

    gaze = canonicalize_gaze(
        source,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        screen_size_px=SCREEN_SIZE_PX,
        metadata={"example": EVIDENCE_CLASSIFICATION},
    )
    trail.add(
        operation="canonicalize_gaze",
        input_data=source_snapshot,
        output_data=gaze.data,
        parameters={
            "sampling_rate_hz": SAMPLING_RATE_HZ,
            "screen_size_px": SCREEN_SIZE_PX,
        },
    )

    qc_samples = ai_flag_anomalies(
        gaze.data,
        sampling_rate_hz=gaze.sampling_rate_hz,
        random_state=7,
        trail=trail,
    )
    trial_quality = score_trial_quality(qc_samples, screen_size_px=SCREEN_SIZE_PX)
    trail.add(
        operation="score_trial_quality",
        input_data=qc_samples,
        output_data=trial_quality,
        parameters={"screen_size_px": SCREEN_SIZE_PX},
    )

    event_samples = ivt_classify_events(
        qc_samples,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        velocity_threshold_px_s=1000.0,
    )
    trail.add(
        operation="ivt_classify_events",
        input_data=qc_samples,
        output_data=event_samples,
        parameters={
            "sampling_rate_hz": SAMPLING_RATE_HZ,
            "velocity_threshold_px_s": 1000.0,
        },
    )
    event_intervals = samples_to_event_intervals(
        event_samples,
        label_col="predicted_event",
        sampling_rate_hz=SAMPLING_RATE_HZ,
    )
    trail.add(
        operation="samples_to_event_intervals",
        input_data=event_samples,
        output_data=event_intervals,
        parameters={"label_col": "predicted_event"},
    )

    fixations = _fixation_centroids(event_samples, event_intervals)
    trail.add(
        operation="fixation_centroids",
        input_data=event_intervals,
        output_data=fixations,
        parameters={"source_event_label": "fixation"},
    )

    aois = _demo_aois()
    aoi_frame = aois_to_frame(aois)
    assignments = map_fixations_to_aois(
        fixations,
        aois,
        overlap_rule="first",
        trail=trail,
    )
    scanpaths = to_semantic_scanpaths(assignments)
    trail.add(
        operation="to_semantic_scanpaths",
        input_data=assignments,
        output_data=scanpaths,
        parameters={
            "label_col": "aoi_label",
            "collapse_repeats": True,
            "drop_unassigned": True,
        },
    )

    pd.testing.assert_frame_equal(source, source_snapshot, check_exact=True)
    source_unchanged = fingerprint_frame(source) == source_fingerprint
    if not source_unchanged:
        raise RuntimeError("The synthetic source table changed during the tour.")
    if not (len(source) == len(gaze.data) == len(qc_samples) == len(event_samples)):
        raise RuntimeError("Sample row counts changed across non-destructive stages.")

    outputs = {
        "01_source_gaze.csv": source_snapshot,
        "02_canonical_gaze.csv": gaze.data,
        "03_qc_samples.csv": qc_samples,
        "04_trial_quality.csv": trial_quality,
        "05_event_samples.csv": event_samples,
        "06_event_intervals.csv": event_intervals,
        "07_fixation_centroids.csv": fixations,
        "08_aoi_definitions.csv": aoi_frame,
        "09_fixation_aoi_assignments.csv": assignments,
        "10_semantic_scanpaths.csv": scanpaths,
    }
    for name, frame in outputs.items():
        frame.to_csv(args.output_dir / name, index=False)

    (args.output_dir / "provenance.json").write_text(
        trail.to_json(indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "example": "00_gazeforge_tour",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "gazeforge_version": __version__,
        "source_unchanged": source_unchanged,
        "sample_row_count_preserved": True,
        "source_rows": int(len(source_snapshot)),
        "source_fingerprint": source_fingerprint,
        "canonical_fingerprint": fingerprint_frame(gaze.data),
        "qc_fingerprint": fingerprint_frame(qc_samples),
        "stages": [
            "simulate/load source gaze",
            "canonicalise",
            "non-destructive QC",
            "transparent I-VT events",
            "researcher-defined AOIs",
            "semantic scanpaths",
            "provenance",
        ],
        "boundaries": {
            "synthetic_output_is_empirical_validation": False,
            "qc_flag_is_automatic_exclusion": False,
            "workflow_execution_is_device_validation": False,
            "workflow_execution_is_measurement_validation": False,
            "ivt_demo_establishes_general_event_model_superiority": False,
        },
        "next_steps": {
            "real_tracker_import": "docs/worked-tracker-import.md",
            "qc_review_and_exclusions": "docs/qc-review-exclusion-ledger.md",
            "learned_event_validation": "docs/event-model-validation-clinic.md",
            "publication_freeze": "docs/publication-readiness.md",
        },
    }
    (args.output_dir / "workflow_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print("GazeForge tour complete")
    print(f"  source samples: {len(source_snapshot)}")
    print(f"  QC-flagged samples: {int(qc_samples['qc_flag'].sum())}")
    print(f"  event intervals: {len(event_intervals)}")
    print(f"  fixation/AOI assignments: {len(assignments)}")
    print(f"  output bundle: {args.output_dir}")
    print("  evidence: synthetic/demo only; not empirical validation")


if __name__ == "__main__":
    main()
