"""Run a deterministic worked advertising/interface study with GazeForge.

The bundled gaze is synthetic and intentionally shaped like a small static-ad study.
Outputs demonstrate an auditable study workflow; they are not empirical validation
and do not establish tracker, native 60 Hz, Gazepoint, or GP3 validity.
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from gazeforge import (
    AOI,
    AuditTrail,
    ai_flag_anomalies,
    aois_to_frame,
    canonicalize_gaze,
    fingerprint_frame,
    ivt_classify_events,
    map_fixations_to_aois,
    samples_to_event_intervals,
    score_trial_quality,
    to_semantic_scanpaths,
)

SAMPLING_RATE_HZ = 60.0
SCREEN_SIZE_PX = (1920, 1080)
EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
AOI_LABELS = ("brand", "claim", "disclosure", "product")


def _aois() -> list[AOI]:
    return [
        AOI("brand", "brand", 80, 80, 520, 280, source="researcher_defined"),
        AOI("claim", "claim", 80, 340, 940, 650, source="researcher_defined"),
        AOI(
            "disclosure",
            "disclosure",
            80,
            760,
            940,
            920,
            source="researcher_defined",
        ),
        AOI("product", "product", 1080, 150, 1840, 930, source="researcher_defined"),
    ]


def _build_source() -> pd.DataFrame:
    centers = {
        "brand": (300.0, 180.0),
        "claim": (500.0, 495.0),
        "disclosure": (500.0, 840.0),
        "product": (1460.0, 540.0),
    }
    sequences = {
        "ad_a": ("brand", "claim", "product", "disclosure"),
        "ad_b": ("product", "claim", "disclosure", "brand"),
    }
    jitter = ((0.0, 0.0), (3.0, -2.0), (-2.0, 2.0), (2.0, 1.0), (-3.0, -1.0))
    dt_ms = 1000.0 / SAMPLING_RATE_HZ
    rows: list[dict[str, object]] = []

    for participant_index in range(4):
        participant = f"p{participant_index + 1:02d}"
        offset_x = float(participant_index * 2)
        offset_y = float(participant_index - 1)
        for trial, sequence in sequences.items():
            timestamp_ms = 0.0
            previous: tuple[float, float] | None = None
            for label in sequence:
                center = centers[label]
                if previous is not None:
                    for step in range(1, 5):
                        fraction = step / 5.0
                        rows.append(
                            {
                                "participant_id": participant,
                                "trial_id": trial,
                                "timestamp_ms": timestamp_ms,
                                "x_px": previous[0] + fraction * (center[0] - previous[0]),
                                "y_px": previous[1] + fraction * (center[1] - previous[1]),
                            }
                        )
                        timestamp_ms += dt_ms
                for sample_index in range(24):
                    dx, dy = jitter[sample_index % len(jitter)]
                    rows.append(
                        {
                            "participant_id": participant,
                            "trial_id": trial,
                            "timestamp_ms": timestamp_ms,
                            "x_px": center[0] + dx + offset_x,
                            "y_px": center[1] + dy + offset_y,
                        }
                    )
                    timestamp_ms += dt_ms
                previous = center

    return pd.DataFrame(rows)


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

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-advertising-study-demo"),
        help="Directory for the reviewable worked-study bundle.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source = _build_source()
    source_snapshot = source.copy(deep=True)
    source_fingerprint = fingerprint_frame(source_snapshot)
    trail = AuditTrail()

    gaze = canonicalize_gaze(
        source,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        screen_size_px=SCREEN_SIZE_PX,
        metadata={
            "example": "worked_advertising_interface_study",
            "evidence_classification": EVIDENCE_CLASSIFICATION,
        },
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

    flagged = ai_flag_anomalies(
        gaze.data,
        sampling_rate_hz=gaze.sampling_rate_hz,
        random_state=42,
        trail=trail,
    )
    quality = score_trial_quality(flagged, screen_size_px=SCREEN_SIZE_PX)
    trail.add(
        operation="score_trial_quality",
        input_data=flagged,
        output_data=quality,
        parameters={"screen_size_px": SCREEN_SIZE_PX},
    )

    event_samples = ivt_classify_events(
        flagged,
        sampling_rate_hz=gaze.sampling_rate_hz,
        velocity_threshold_px_s=1000.0,
    )
    trail.add(
        operation="ivt_classify_events",
        input_data=flagged,
        output_data=event_samples,
        parameters={"velocity_threshold_px_s": 1000.0},
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

    fixation_centroids = _fixation_centroids(event_samples, event_intervals)
    trail.add(
        operation="fixation_centroids",
        input_data=event_intervals,
        output_data=fixation_centroids,
        parameters={"source_event_label": "fixation"},
    )

    aois = _aois()
    aoi_definitions = aois_to_frame(aois)
    assignments = map_fixations_to_aois(
        fixation_centroids,
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

    assigned_labels = set(assignments["aoi_label"].dropna().astype(str))
    missing_labels = set(AOI_LABELS) - assigned_labels
    if missing_labels:
        raise RuntimeError(f"Worked example failed to visit AOIs: {sorted(missing_labels)}")

    pd.testing.assert_frame_equal(source, source_snapshot, check_exact=True)
    source_unchanged = fingerprint_frame(source) == source_fingerprint
    if not source_unchanged:
        raise RuntimeError("Source table changed during the worked example.")

    tables = {
        "01_source_gaze.csv": source_snapshot,
        "02_canonical_gaze.csv": gaze.data,
        "03_qc_samples.csv": flagged,
        "04_trial_quality.csv": quality,
        "05_event_samples.csv": event_samples,
        "06_event_intervals.csv": event_intervals,
        "07_fixation_centroids.csv": fixation_centroids,
        "08_aoi_definitions.csv": aoi_definitions,
        "09_fixation_aoi_assignments.csv": assignments,
        "10_semantic_scanpaths.csv": scanpaths,
    }
    for filename, table in tables.items():
        table.to_csv(args.output_dir / filename, index=False)

    analysis_plan = {
        "example": "worked_advertising_interface_study",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "research_question": (
            "Which predefined visible regions are inspected, and in what semantic order?"
        ),
        "observable_outputs": [
            "trial_quality",
            "transparent_ivt_events",
            "fixation_aoi_assignments",
            "semantic_scanpaths",
        ],
        "aoi_labels": list(AOI_LABELS),
        "qc_rule": "Review flags; do not automatically delete samples.",
        "event_baseline": {
            "method": "I-VT",
            "velocity_threshold_px_s": 1000.0,
            "purpose": "inspectable software demonstration baseline",
        },
        "empirical_validation_plan": (
            "For a real learned-model study, validate against suitable reference labels "
            "with an explicit leakage-safe held-out unit such as participants."
        ),
        "substantive_boundary": (
            "AOI assignments and scanpaths describe observable visual-attention structure; "
            "they do not by themselves establish persuasion, liking, comprehension, or intent."
        ),
    }
    (args.output_dir / "analysis_plan.json").write_text(
        json.dumps(analysis_plan, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "provenance.json").write_text(
        trail.to_json(indent=2),
        encoding="utf-8",
    )

    manifest = {
        "workflow": "worked_advertising_interface_study",
        "gazeforge_version": version("gazeforge"),
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "input_mode": "deterministic_synthetic_real_data_shaped_demo",
        "sampling_rate_hz": SAMPLING_RATE_HZ,
        "screen_size_px": list(SCREEN_SIZE_PX),
        "source_unchanged": source_unchanged,
        "source_fingerprint_sha256": source_fingerprint,
        "aoi_labels": list(AOI_LABELS),
        "table_outputs": list(tables),
        "supporting_outputs": ["analysis_plan.json", "provenance.json"],
        "scientific_boundary": (
            "Synthetic/demo outputs teach study structure and software composition; they are "
            "not empirical validation evidence and do not establish native-device, native "
            "60 Hz, Gazepoint, or GP3 validity."
        ),
    }
    (args.output_dir / "workflow_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote worked advertising/interface demo to {args.output_dir.resolve()}")
    print(f"AOIs: {', '.join(AOI_LABELS)}")
    print(f"Evidence boundary: {EVIDENCE_CLASSIFICATION}")
    print("Source table unchanged: yes")


if __name__ == "__main__":
    main()
