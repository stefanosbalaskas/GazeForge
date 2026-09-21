"""Run a deterministic end-to-end GazeForge research workflow.

The bundled data are synthetic demonstration data. Outputs are examples of software
composition and provenance, not empirical validation evidence or native-device validity.
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


def _researcher_defined_aois() -> list[AOI]:
    return [
        AOI(
            "header",
            "header",
            0,
            0,
            1920,
            260,
            source="researcher_defined",
        ),
        AOI(
            "left_panel",
            "left panel",
            0,
            260,
            820,
            1080,
            source="researcher_defined",
        ),
        AOI(
            "main_content",
            "main content",
            820,
            260,
            1920,
            1080,
            source="researcher_defined",
        ),
    ]


def _save_axis(axis, path: Path) -> None:
    from matplotlib import pyplot as plt

    axis.figure.tight_layout()
    axis.figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(axis.figure)


def _write_figures(
    output_dir: Path,
    flagged: pd.DataFrame,
    aois: list[AOI],
    assignments: pd.DataFrame,
) -> list[str]:
    from gazeforge.visualization import plot_aoi_overlay, plot_qc_timeline, plot_scanpath

    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    if assignments.empty:
        return []

    first_key = assignments[["participant_id", "trial_id"]].drop_duplicates().iloc[0]
    participant = first_key["participant_id"]
    trial = first_key["trial_id"]
    flagged_first = flagged.loc[
        (flagged["participant_id"] == participant) & (flagged["trial_id"] == trial)
    ]
    assigned_first = assignments.loc[
        (assignments["participant_id"] == participant) & (assignments["trial_id"] == trial)
    ]

    paths = [
        figure_dir / "01_qc_timeline.png",
        figure_dir / "02_aoi_overlay.png",
        figure_dir / "03_scanpath.png",
    ]
    _save_axis(
        plot_qc_timeline(flagged_first, title="Synthetic/demo QC timeline"),
        paths[0],
    )
    _save_axis(
        plot_aoi_overlay(
            aois,
            fixations=assigned_first,
            title="Researcher-defined AOIs with demo fixations",
        ),
        paths[1],
    )
    _save_axis(
        plot_scanpath(
            assigned_first,
            title="Synthetic/demo semantic scanpath",
        ),
        paths[2],
    )
    return [str(path.relative_to(output_dir)) for path in paths]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("end-to-end-research-demo"),
        help="Directory for the reviewable workflow bundle.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip optional Matplotlib diagnostics.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source = simulate_gaze(
        n_participants=2,
        n_trials=2,
        samples_per_trial=180,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        screen_size_px=SCREEN_SIZE_PX,
        random_state=42,
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

    fixation_centroids = _fixation_centroids(event_samples, event_intervals)
    trail.add(
        operation="fixation_centroids",
        input_data=event_intervals,
        output_data=fixation_centroids,
        parameters={"source_event_label": "fixation"},
    )

    aois = _researcher_defined_aois()
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

    pd.testing.assert_frame_equal(source, source_snapshot, check_exact=True)
    source_unchanged = fingerprint_frame(source) == source_fingerprint
    if not source_unchanged:
        raise RuntimeError("Source table changed during the workflow.")

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

    (args.output_dir / "provenance.json").write_text(
        trail.to_json(indent=2),
        encoding="utf-8",
    )

    figure_paths: list[str] = []
    if not args.no_figures:
        figure_paths = _write_figures(args.output_dir, flagged, aois, assignments)

    fingerprints = {filename: fingerprint_frame(table) for filename, table in tables.items()}
    manifest = {
        "workflow": "end_to_end_research_workflow",
        "gazeforge_version": version("gazeforge"),
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "input_mode": "deterministic_synthetic_demo",
        "sampling_rate_hz": SAMPLING_RATE_HZ,
        "screen_size_px": list(SCREEN_SIZE_PX),
        "source_unchanged": source_unchanged,
        "source_fingerprint_sha256": source_fingerprint,
        "table_fingerprints_sha256": fingerprints,
        "table_outputs": list(tables),
        "figure_outputs": figure_paths,
        "scientific_boundary": (
            "Synthetic/demo outputs demonstrate software composition and provenance; "
            "they are not empirical validation evidence and do not establish "
            "native-device or GP3 validity."
        ),
    }
    (args.output_dir / "workflow_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote end-to-end research demo to {args.output_dir.resolve()}")
    print(f"Evidence boundary: {EVIDENCE_CLASSIFICATION}")
    print("Source table unchanged: yes")


if __name__ == "__main__":
    main()
