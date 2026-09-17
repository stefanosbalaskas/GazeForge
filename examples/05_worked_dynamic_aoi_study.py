"""Run a deterministic moving-stimulus dynamic-AOI study with GazeForge.

The bundled fixation table and AOI tracks are synthetic/demo inputs. The script
demonstrates bounded interpolation, no extrapolation, dynamic fixation assignment,
semantic scanpaths, provenance, and optional figures. It is not empirical
validation and does not establish detector, tracker, native 60 Hz, Gazepoint, or
GP3 validity.
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from gazeforge import (
    AuditTrail,
    DynamicAOIKeyframe,
    dynamic_aois_to_frame,
    fingerprint_frame,
    interpolate_dynamic_aoi,
    map_fixations_to_dynamic_aois,
    to_semantic_scanpaths,
)

EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"
SCREEN_SIZE_PX = (1920, 1080)
MAX_INTERPOLATION_GAP_MS = 1000.0
AOI_LABELS = ("product", "claim", "cta")
TRACK_TIMES_MS = (0.0, 1000.0, 2000.0)


def _keyframes() -> list[DynamicAOIKeyframe]:
    """Return three deterministic reviewed AOI tracks."""
    specs = {
        "product": [
            (200, 260, 600, 700),
            (350, 280, 750, 720),
            (500, 300, 900, 740),
        ],
        "claim": [
            (980, 120, 1640, 350),
            (850, 140, 1510, 370),
            (720, 160, 1380, 390),
        ],
        "cta": [
            (1120, 730, 1640, 930),
            (1170, 690, 1690, 890),
            (1220, 650, 1740, 850),
        ],
    }
    frames: list[DynamicAOIKeyframe] = []
    for label, boxes in specs.items():
        for timestamp_ms, bounds in zip(TRACK_TIMES_MS, boxes, strict=True):
            frames.append(
                DynamicAOIKeyframe(
                    aoi_id=label,
                    label=label,
                    timestamp_ms=timestamp_ms,
                    xmin=float(bounds[0]),
                    ymin=float(bounds[1]),
                    xmax=float(bounds[2]),
                    ymax=float(bounds[3]),
                    confidence=1.0,
                    source="researcher_reviewed_demo",
                )
            )
    return frames


def _track(keyframes: list[DynamicAOIKeyframe], label: str) -> list[DynamicAOIKeyframe]:
    return [frame for frame in keyframes if frame.aoi_id == label]


def _center(
    keyframes: list[DynamicAOIKeyframe],
    label: str,
    timestamp_ms: float,
) -> tuple[float, float]:
    geometry = interpolate_dynamic_aoi(
        _track(keyframes, label),
        timestamp_ms,
        max_gap_ms=MAX_INTERPOLATION_GAP_MS,
    )
    if geometry is None:
        raise RuntimeError(f"Expected bounded geometry for {label!r} at {timestamp_ms} ms.")
    return (
        (geometry.xmin + geometry.xmax) / 2.0,
        (geometry.ymin + geometry.ymax) / 2.0,
    )


def _source_fixations(keyframes: list[DynamicAOIKeyframe]) -> pd.DataFrame:
    """Build deterministic fixation rows that visit moving AOIs plus range probes."""
    sequences = {
        "video_a": (
            (250.0, "product"),
            (750.0, "claim"),
            (1000.0, "cta"),
            (1250.0, "product"),
            (1750.0, "cta"),
        ),
        "video_b": (
            (250.0, "claim"),
            (750.0, "product"),
            (1000.0, "cta"),
            (1250.0, "claim"),
            (1750.0, "product"),
        ),
    }
    rows: list[dict[str, object]] = []
    for participant_index in range(4):
        participant_id = f"p{participant_index + 1:02d}"
        x_offset = float(participant_index * 3)
        y_offset = float(participant_index - 1)

        for trial_id, sequence in sequences.items():
            rows.append(
                {
                    "participant_id": participant_id,
                    "trial_id": trial_id,
                    "timestamp_ms": -100.0,
                    "duration_ms": 160.0,
                    "x_px": 400.0 + x_offset,
                    "y_px": 480.0 + y_offset,
                    "probe": "before_track_range",
                }
            )
            for timestamp_ms, label in sequence:
                x_px, y_px = _center(keyframes, label, timestamp_ms)
                rows.append(
                    {
                        "participant_id": participant_id,
                        "trial_id": trial_id,
                        "timestamp_ms": timestamp_ms,
                        "duration_ms": 220.0,
                        "x_px": x_px + x_offset,
                        "y_px": y_px + y_offset,
                        "probe": "within_track_range",
                    }
                )
            rows.append(
                {
                    "participant_id": participant_id,
                    "trial_id": trial_id,
                    "timestamp_ms": 2100.0,
                    "duration_ms": 160.0,
                    "x_px": 700.0 + x_offset,
                    "y_px": 520.0 + y_offset,
                    "probe": "after_track_range",
                }
            )

    return pd.DataFrame(rows)


def _interpolation_audit(keyframes: list[DynamicAOIKeyframe]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    audit_times = (-100.0, 0.0, 500.0, 1000.0, 1500.0, 2000.0, 2100.0)
    for label in AOI_LABELS:
        track = _track(keyframes, label)
        for timestamp_ms in audit_times:
            geometry = interpolate_dynamic_aoi(
                track,
                timestamp_ms,
                max_gap_ms=MAX_INTERPOLATION_GAP_MS,
            )
            rows.append(
                {
                    "aoi_id": label,
                    "timestamp_ms": timestamp_ms,
                    "resolved": geometry is not None,
                    "temporal_source": None if geometry is None else geometry.source,
                    "xmin": None if geometry is None else geometry.xmin,
                    "ymin": None if geometry is None else geometry.ymin,
                    "xmax": None if geometry is None else geometry.xmax,
                    "ymax": None if geometry is None else geometry.ymax,
                }
            )
    return pd.DataFrame(rows)


def _assignment_summary(assignments: pd.DataFrame) -> pd.DataFrame:
    data = assignments.copy()
    data["assignment"] = data["aoi_label"].fillna("UNASSIGNED").astype(str)
    return (
        data.groupby(["participant_id", "trial_id", "assignment"], sort=False)
        .size()
        .rename("n_fixations")
        .reset_index()
    )


def _write_figures(
    output_dir: Path,
    keyframes: list[DynamicAOIKeyframe],
    assignments: pd.DataFrame,
) -> list[str]:
    from matplotlib import pyplot as plt

    from gazeforge.visualization import plot_dynamic_aoi_snapshot, plot_scanpath

    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    snapshot_fixation = assignments.loc[
        (assignments["participant_id"] == "p01")
        & (assignments["trial_id"] == "video_a")
        & (assignments["timestamp_ms"] == 1250.0)
    ]
    axis = plot_dynamic_aoi_snapshot(
        keyframes,
        1250.0,
        fixations=snapshot_fixation,
        max_interpolation_gap_ms=MAX_INTERPOLATION_GAP_MS,
        title="Bounded dynamic AOIs at 1250 ms",
    )
    snapshot_name = "figures/01_dynamic_aoi_snapshot.png"
    axis.figure.savefig(output_dir / snapshot_name, dpi=160, bbox_inches="tight")
    plt.close(axis.figure)

    scanpath_rows = assignments.loc[
        (assignments["participant_id"] == "p01")
        & (assignments["trial_id"] == "video_a")
        & assignments["aoi_label"].notna()
    ].sort_values("timestamp_ms")
    axis = plot_scanpath(
        scanpath_rows,
        title="Synthetic dynamic-AOI scanpath · p01 · video_a",
    )
    scanpath_name = "figures/02_dynamic_scanpath.png"
    axis.figure.savefig(output_dir / scanpath_name, dpi=160, bbox_inches="tight")
    plt.close(axis.figure)

    return [snapshot_name, scanpath_name]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-dynamic-aoi-demo"),
        help="Directory for the reviewable dynamic-AOI study bundle.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip optional Matplotlib figures and write tables/JSON only.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    keyframes = _keyframes()
    source = _source_fixations(keyframes)
    source_snapshot = source.copy(deep=True)
    source_fingerprint = fingerprint_frame(source_snapshot)
    keyframe_table = dynamic_aois_to_frame(keyframes)
    keyframe_fingerprint = fingerprint_frame(keyframe_table)
    trail = AuditTrail()

    assignments = map_fixations_to_dynamic_aois(
        source,
        keyframes,
        max_interpolation_gap_ms=MAX_INTERPOLATION_GAP_MS,
        overlap_rule="highest_confidence",
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
    interpolation_audit = _interpolation_audit(keyframes)
    assignment_summary = _assignment_summary(assignments)

    outside = assignments["probe"].isin({"before_track_range", "after_track_range"})
    if not assignments.loc[outside, "aoi_id"].isna().all():
        raise RuntimeError("Dynamic AOI mapping extrapolated outside the observed track range.")

    internal = assignments["probe"].eq("within_track_range")
    if not assignments.loc[internal, "aoi_id"].notna().all():
        raise RuntimeError("Expected all within-range synthetic fixations to map to a dynamic AOI.")
    if "interpolated" not in set(assignments.loc[internal, "aoi_source"].dropna()):
        raise RuntimeError("Worked example did not exercise bounded AOI interpolation.")

    for label in AOI_LABELS:
        track = _track(keyframes, label)
        if interpolate_dynamic_aoi(
            track,
            -100.0,
            max_gap_ms=MAX_INTERPOLATION_GAP_MS,
        ) is not None:
            raise RuntimeError("Pre-track extrapolation must return no dynamic AOI geometry.")
        if interpolate_dynamic_aoi(
            track,
            2100.0,
            max_gap_ms=MAX_INTERPOLATION_GAP_MS,
        ) is not None:
            raise RuntimeError("Post-track extrapolation must return no dynamic AOI geometry.")

    pd.testing.assert_frame_equal(source, source_snapshot, check_exact=True)
    source_unchanged = fingerprint_frame(source) == source_fingerprint
    if not source_unchanged:
        raise RuntimeError("Source fixation table changed during the worked example.")

    tables = {
        "01_source_fixations.csv": source_snapshot,
        "02_dynamic_aoi_keyframes.csv": keyframe_table,
        "03_fixation_dynamic_aoi_assignments.csv": assignments,
        "04_semantic_scanpaths.csv": scanpaths,
        "05_interpolation_audit.csv": interpolation_audit,
        "06_assignment_summary.csv": assignment_summary,
    }
    for filename, table in tables.items():
        table.to_csv(args.output_dir / filename, index=False)

    figure_outputs: list[str] = []
    if not args.no_figures:
        figure_outputs = _write_figures(args.output_dir, keyframes, assignments)

    analysis_plan = {
        "example": "worked_dynamic_aoi_study",
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "research_question": (
            "Which moving visible regions receive fixations, and in what semantic order?"
        ),
        "aoi_labels": list(AOI_LABELS),
        "dynamic_aoi_source": "researcher_reviewed_demo",
        "max_interpolation_gap_ms": MAX_INTERPOLATION_GAP_MS,
        "overlap_rule": "highest_confidence",
        "no_extrapolation": True,
        "observable_outputs": [
            "dynamic_aoi_keyframes",
            "fixation_dynamic_aoi_assignments",
            "semantic_scanpaths",
            "interpolation_audit",
        ],
        "substantive_boundary": (
            "Dynamic AOI membership and sequence structure describe observable gaze-region "
            "correspondence. They do not by themselves establish attention quality, "
            "comprehension, persuasion, preference, intent, or another latent state."
        ),
        "validation_boundary": (
            "This deterministic software demonstration does not validate a learned detector "
            "or tracker and does not establish native-device, native 60 Hz, Gazepoint, or "
            "GP3 validity."
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
        "workflow": "worked_dynamic_aoi_study",
        "gazeforge_version": version("gazeforge"),
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "input_mode": "deterministic_synthetic_fixation_and_dynamic_aoi_demo",
        "screen_size_px": list(SCREEN_SIZE_PX),
        "source_unchanged": source_unchanged,
        "source_fingerprint_sha256": source_fingerprint,
        "keyframe_fingerprint_sha256": keyframe_fingerprint,
        "aoi_labels": list(AOI_LABELS),
        "max_interpolation_gap_ms": MAX_INTERPOLATION_GAP_MS,
        "no_extrapolation_verified": True,
        "table_outputs": list(tables),
        "supporting_outputs": ["analysis_plan.json", "provenance.json"],
        "figure_outputs": figure_outputs,
        "scientific_boundary": (
            "Synthetic/demo outputs teach bounded dynamic-AOI mapping and reporting. They are "
            "not empirical validation evidence and do not establish detector accuracy, "
            "tracker validity, native 60 Hz validity, Gazepoint validity, GP3 validity, or "
            "substantive psychological effects."
        ),
    }
    (args.output_dir / "workflow_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote worked dynamic-AOI demo to {args.output_dir.resolve()}")
    print(f"AOIs: {', '.join(AOI_LABELS)}")
    print(f"Evidence boundary: {EVIDENCE_CLASSIFICATION}")
    print("Bounded interpolation exercised: yes")
    print("No extrapolation verified: yes")
    print("Source table unchanged: yes")


if __name__ == "__main__":
    main()
