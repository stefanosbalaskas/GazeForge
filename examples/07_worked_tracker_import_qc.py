"""Worked tracker-import and non-destructive QC example.

This deterministic demo uses Gazepoint-style source columns to demonstrate an
explicit import contract, preflight diagnostics, review-first QC, provenance,
and a reviewable output bundle. It is not empirical tracker/device validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gazeforge import (
    AuditTrail,
    __version__,
    adapt_gazepoint_samples,
    ai_flag_anomalies,
    fingerprint_frame,
    infer_sampling_rate_hz,
    score_trial_quality,
)

SCREEN_SIZE_PX = (1920, 1080)
NOMINAL_RATE_HZ = 60.0
EVIDENCE_CLASSIFICATION = "synthetic_demo_not_empirical_evidence"


def _build_demo_export() -> pd.DataFrame:
    """Return a deterministic Gazepoint-shaped tracker export."""
    rows: list[dict[str, Any]] = []
    dt_s = 1.0 / NOMINAL_RATE_HZ

    for participant_index, participant in enumerate(("P001", "P002"), start=1):
        for trial_index, trial in enumerate(("ad_A", "ad_B"), start=1):
            for sample_index in range(18):
                time_s = sample_index * dt_s
                phase = 0.34 * sample_index + 0.4 * trial_index
                x_norm = 0.42 + 0.12 * np.sin(phase) + 0.015 * participant_index
                y_norm = 0.48 + 0.10 * np.cos(phase * 0.8) + 0.01 * trial_index
                rows.append(
                    {
                        "USER_FILE": participant,
                        "MEDIA_ID": trial,
                        "TIME": round(time_s, 9),
                        "BPOGX": float(x_norm),
                        "BPOGY": float(y_norm),
                        "PUPIL": float(3.0 + 0.08 * np.sin(phase * 0.6)),
                        "VALIDITY": 1,
                    }
                )

    source = pd.DataFrame(rows)

    # Deliberate review cases. They remain in the source and all derivatives.
    duplicate = source.iloc[[7]].copy()
    duplicate.loc[:, "BPOGX"] = duplicate["BPOGX"] + 0.004
    source = pd.concat([source, duplicate], ignore_index=True)

    source.loc[22, "BPOGX"] = 1.08  # converts beyond the right screen edge
    source.loc[55, "BPOGY"] = -0.04  # converts above the top screen edge
    source.loc[31, "BPOGX"] = np.nan  # retained missing gaze sample

    return source


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _build_preflight(
    source: pd.DataFrame,
    canonical: pd.DataFrame,
    *,
    observed_rate_hz: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    sample_key = ["participant_id", "trial_id", "timestamp_ms"]
    duplicate_mask = canonical.duplicated(sample_key, keep=False)
    missing_identity_mask = canonical[["participant_id", "trial_id"]].isna().any(axis=1)

    width_px, height_px = SCREEN_SIZE_PX
    valid_xy = canonical["x_px"].notna() & canonical["y_px"].notna()
    offscreen_mask = valid_xy & (
        (canonical["x_px"] < 0)
        | (canonical["x_px"] > width_px)
        | (canonical["y_px"] < 0)
        | (canonical["y_px"] > height_px)
    )
    missing_gaze_mask = canonical[["x_px", "y_px"]].isna().any(axis=1)

    relative_rate_difference = abs(observed_rate_hz - NOMINAL_RATE_HZ) / NOMINAL_RATE_HZ
    row_count_preserved = len(source) == len(canonical)

    summary = {
        "source_rows": int(len(source)),
        "canonical_rows": int(len(canonical)),
        "row_count_preserved": bool(row_count_preserved),
        "duplicate_sample_key_rows": int(duplicate_mask.sum()),
        "missing_identity_rows": int(missing_identity_mask.sum()),
        "missing_gaze_rows": int(missing_gaze_mask.sum()),
        "offscreen_rows": int(offscreen_mask.sum()),
        "nominal_rate_hz": NOMINAL_RATE_HZ,
        "observed_cadence_hz": float(observed_rate_hz),
        "nominal_vs_observed_relative_difference": float(relative_rate_difference),
    }

    preflight = pd.DataFrame(
        [
            {
                "diagnostic": "source_row_count",
                "value": summary["source_rows"],
                "review": "source observations retained",
            },
            {
                "diagnostic": "canonical_row_count",
                "value": summary["canonical_rows"],
                "review": "must equal source row count; no silent deletion",
            },
            {
                "diagnostic": "duplicate_sample_key_rows",
                "value": summary["duplicate_sample_key_rows"],
                "review": "retained for acquisition/export review; not deduplicated",
            },
            {
                "diagnostic": "missing_identity_rows",
                "value": summary["missing_identity_rows"],
                "review": "investigate source identity; do not guess participant/trial labels",
            },
            {
                "diagnostic": "missing_gaze_rows",
                "value": summary["missing_gaze_rows"],
                "review": "retained for QC; not filled by guesswork",
            },
            {
                "diagnostic": "offscreen_rows",
                "value": summary["offscreen_rows"],
                "review": "retained for review; not clipped to screen bounds",
            },
            {
                "diagnostic": "nominal_rate_hz",
                "value": summary["nominal_rate_hz"],
                "review": "acquisition/demo contract value; not inferred from timestamps",
            },
            {
                "diagnostic": "observed_cadence_hz",
                "value": summary["observed_cadence_hz"],
                "review": "median positive within-trial timestamp cadence; not hardware-rate proof",
            },
            {
                "diagnostic": "nominal_vs_observed_relative_difference",
                "value": summary["nominal_vs_observed_relative_difference"],
                "review": "diagnostic comparison only",
            },
        ]
    )
    return preflight, summary


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    source = _build_demo_export()
    source_snapshot = source.copy(deep=True)
    source_fingerprint = fingerprint_frame(source)

    source_path = output_dir / "01_source_tracker_export.csv"
    source.to_csv(source_path, index=False)

    gaze = adapt_gazepoint_samples(
        source,
        screen_size_px=SCREEN_SIZE_PX,
        participant_col="USER_FILE",
        trial_col="MEDIA_ID",
        timestamp_col="TIME",
        x_col="BPOGX",
        y_col="BPOGY",
        pupil_col="PUPIL",
        validity_col="VALIDITY",
        time_unit="seconds",
        coordinates="normalized",
        sampling_rate_hz=None,
    )
    canonical = gaze.data
    observed_rate_hz = infer_sampling_rate_hz(canonical)

    canonical_path = output_dir / "02_canonical_gaze.csv"
    canonical.to_csv(canonical_path, index=False)

    preflight, preflight_summary = _build_preflight(
        source,
        canonical,
        observed_rate_hz=observed_rate_hz,
    )
    preflight_path = output_dir / "03_import_preflight.csv"
    preflight.to_csv(preflight_path, index=False)

    trail = AuditTrail()
    trail.add(
        operation="adapt_gazepoint_samples",
        input_data=source,
        output_data=canonical,
        parameters={
            "participant_col": "USER_FILE",
            "trial_col": "MEDIA_ID",
            "timestamp_col": "TIME",
            "x_col": "BPOGX",
            "y_col": "BPOGY",
            "pupil_col": "PUPIL",
            "validity_col": "VALIDITY",
            "time_unit": "seconds",
            "timestamp_scale_to_ms": 1000.0,
            "coordinates": "normalized",
            "coordinate_scale": list(SCREEN_SIZE_PX),
            "screen_size_px": list(SCREEN_SIZE_PX),
            "sampling_rate_hz": None,
        },
        warnings=[
            "Import compatibility is not Gazepoint/GP3 or native-60-Hz validation.",
            "Observed timestamp cadence is not proof of native hardware sampling rate.",
        ],
    )

    qc_samples = ai_flag_anomalies(
        canonical,
        sampling_rate_hz=gaze.sampling_rate_hz,
        random_state=42,
        trail=trail,
    )
    qc_path = output_dir / "04_qc_samples.csv"
    qc_samples.to_csv(qc_path, index=False)

    trial_quality = score_trial_quality(
        qc_samples,
        screen_size_px=SCREEN_SIZE_PX,
    )
    quality_path = output_dir / "05_trial_quality.csv"
    trial_quality.to_csv(quality_path, index=False)

    source_unchanged = source.equals(source_snapshot)
    row_count_preserved = len(source) == len(canonical) == len(qc_samples)

    assert source_unchanged
    assert row_count_preserved
    assert preflight_summary["duplicate_sample_key_rows"] >= 2
    assert preflight_summary["offscreen_rows"] >= 2
    assert preflight_summary["missing_identity_rows"] == 0
    assert not canonical.duplicated(
        ["participant_id", "trial_id", "timestamp_ms"],
        keep=False,
    ).empty

    import_contract = {
        "source_format": "deterministic Gazepoint-style demo export",
        "source_columns": {
            "participant_id": "USER_FILE",
            "trial_id": "MEDIA_ID",
            "timestamp": "TIME",
            "x": "BPOGX",
            "y": "BPOGY",
            "pupil": "PUPIL",
            "validity": "VALIDITY",
        },
        "time_unit": "seconds",
        "timestamp_scale_to_ms": 1000.0,
        "coordinate_basis": "normalized_screen_fraction",
        "coordinate_scale_to_pixels": {
            "x": SCREEN_SIZE_PX[0],
            "y": SCREEN_SIZE_PX[1],
        },
        "screen_size_px": list(SCREEN_SIZE_PX),
        "nominal_rate_hz": NOMINAL_RATE_HZ,
        "observed_cadence_hz": observed_rate_hz,
        "observed_cadence_method": "median positive within-trial timestamp interval",
        "repair_policy": (
            "review-first: no clipping, deletion, deduplication, identity reconstruction, "
            "or silent source repair"
        ),
        "preflight": preflight_summary,
    }
    _write_json(output_dir / "import_contract.json", import_contract)

    analysis_plan = {
        "purpose": "worked tracker import and non-destructive QC demonstration",
        "event_model_fitted": False,
        "learned_event_model_fitted": False,
        "exclusions_applied": False,
        "source_mutation_allowed": False,
        "primary_steps": [
            "fingerprint immutable source table",
            "adapt explicitly declared Gazepoint-style fields",
            "inspect identity, duplicate keys, cadence, and coordinate bounds",
            "add non-destructive anomaly flags",
            "summarize trial quality",
            "freeze provenance and evidence boundary",
        ],
        "evidence_classification": EVIDENCE_CLASSIFICATION,
    }
    _write_json(output_dir / "analysis_plan.json", analysis_plan)
    (output_dir / "provenance.json").write_text(
        trail.to_json(indent=2) + "\n",
        encoding="utf-8",
    )

    csv_outputs = [
        source_path.name,
        canonical_path.name,
        preflight_path.name,
        qc_path.name,
        quality_path.name,
    ]
    json_outputs = [
        "import_contract.json",
        "analysis_plan.json",
        "provenance.json",
        "workflow_manifest.json",
    ]

    manifest = {
        "example": "07_worked_tracker_import_qc",
        "gazeforge_version": __version__,
        "evidence_classification": EVIDENCE_CLASSIFICATION,
        "source_unchanged": source_unchanged,
        "row_count_preserved": row_count_preserved,
        "source_fingerprint": source_fingerprint,
        "source_csv_sha256": _sha256_file(source_path),
        "canonical_fingerprint": fingerprint_frame(canonical),
        "qc_fingerprint": fingerprint_frame(qc_samples),
        "screen_size_px": list(SCREEN_SIZE_PX),
        "nominal_rate_hz": NOMINAL_RATE_HZ,
        "observed_cadence_hz": observed_rate_hz,
        "duplicate_sample_key_rows_retained": preflight_summary["duplicate_sample_key_rows"],
        "missing_identity_rows": preflight_summary["missing_identity_rows"],
        "offscreen_rows_retained": preflight_summary["offscreen_rows"],
        "missing_gaze_rows_retained": preflight_summary["missing_gaze_rows"],
        "event_model_fitted": False,
        "exclusions_applied": False,
        "adapter_compatibility_is_device_validation": False,
        "native_60hz_validity_claim_created": False,
        "gazepoint_gp3_validity_claim_created": False,
        "csv_outputs": csv_outputs,
        "json_outputs": json_outputs,
        "scientific_boundary": (
            "This deterministic Gazepoint-shaped demo demonstrates an explicit software "
            "import/QC contract only. It is not empirical validation evidence and does not "
            "establish Gazepoint, GP3, native 60 Hz, event-model, or measurement validity."
        ),
    }
    _write_json(output_dir / "workflow_manifest.json", manifest)

    print("Worked tracker import + QC complete")
    print(f"Output directory: {output_dir}")
    print(f"Source table unchanged: {'yes' if source_unchanged else 'no'}")
    print(f"Row count preserved: {'yes' if row_count_preserved else 'no'}")
    print(f"Duplicate-key rows retained: {preflight_summary['duplicate_sample_key_rows']}")
    print(f"Off-screen rows retained: {preflight_summary['offscreen_rows']}")
    print(f"Observed timestamp cadence: {observed_rate_hz:.3f} Hz")
    print(
        "Evidence boundary: synthetic demo only; import compatibility is not "
        "Gazepoint/GP3 or native-60-Hz validation."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic worked tracker-import and QC demonstration."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("worked-tracker-import-qc-demo"),
        help="Directory for reviewable CSV/JSON outputs.",
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
