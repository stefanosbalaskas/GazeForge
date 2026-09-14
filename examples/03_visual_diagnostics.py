"""Generate synthetic/demo visual diagnostics without creating empirical evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from gazeforge import ai_flag_anomalies, canonicalize_gaze, simulate_gaze
from gazeforge.aoi import AOI
from gazeforge.dynamic_aoi import DynamicAOIKeyframe
from gazeforge.visualization import (
    plot_aoi_overlay,
    plot_dynamic_aoi_snapshot,
    plot_event_calibration,
    plot_event_probabilities,
    plot_qc_timeline,
    plot_scanpath,
)


def _save(axis, path: Path) -> None:
    axis.figure.tight_layout()
    axis.figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(axis.figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("visual-diagnostics-demo"),
        help="Directory for generated PNG files.",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw = simulate_gaze(
        n_participants=1,
        n_trials=1,
        samples_per_trial=180,
        sampling_rate_hz=60,
        random_state=42,
    )
    gaze = canonicalize_gaze(raw, sampling_rate_hz=60, screen_size_px=(1920, 1080))
    flagged = ai_flag_anomalies(
        gaze.data,
        sampling_rate_hz=gaze.sampling_rate_hz,
        random_state=42,
    )
    _save(
        plot_qc_timeline(flagged, title="Synthetic/demo QC anomaly timeline"),
        args.output_dir / "01_qc_timeline.png",
    )

    timestamp = np.arange(0.0, 1000.0, 50.0)
    phase = np.linspace(0.0, 2.0 * np.pi, len(timestamp))
    fixation = 0.55 + 0.25 * np.cos(phase)
    saccade = 0.25 + 0.18 * np.sin(phase)
    noise = np.maximum(0.02, 1.0 - fixation - saccade)
    total = fixation + saccade + noise
    probabilities = pd.DataFrame(
        {
            "timestamp_ms": timestamp,
            "p_event_fixation": fixation / total,
            "p_event_saccade": saccade / total,
            "p_event_noise": noise / total,
        }
    )
    _save(
        plot_event_probabilities(
            probabilities,
            confidence_threshold=0.60,
            title="Synthetic/demo event probabilities",
        ),
        args.output_dir / "02_event_probabilities.png",
    )

    calibrated = probabilities.copy()
    labels = np.array(["fixation", "saccade", "noise"], dtype=object)
    matrix = calibrated[["p_event_fixation", "p_event_saccade", "p_event_noise"]].to_numpy()
    calibrated["event_label"] = labels[np.argmax(matrix, axis=1)]
    _save(
        plot_event_calibration(
            calibrated,
            n_bins=6,
            title="Synthetic/demo top-label calibration",
        ),
        args.output_dir / "03_calibration.png",
    )

    aois = [
        AOI("logo", "logo", 120, 90, 430, 270),
        AOI("claim", "nutrition claim", 1080, 110, 1710, 330),
        AOI("product", "product", 620, 360, 1320, 920),
    ]
    fixations = pd.DataFrame(
        {
            "x_px": [240, 1180, 980, 760, 1450],
            "y_px": [170, 210, 580, 690, 250],
            "aoi_label": ["logo", "nutrition claim", "product", "product", "nutrition claim"],
        }
    )
    _save(
        plot_aoi_overlay(aois, fixations=fixations, title="Synthetic/demo semantic AOIs"),
        args.output_dir / "04_aoi_overlay.png",
    )
    _save(
        plot_scanpath(fixations, title="Synthetic/demo semantic scanpath"),
        args.output_dir / "05_scanpath.png",
    )

    keyframes = [
        DynamicAOIKeyframe("product", "product", 0.0, 500, 320, 980, 800),
        DynamicAOIKeyframe("product", "product", 100.0, 620, 320, 1100, 800),
    ]
    _save(
        plot_dynamic_aoi_snapshot(
            keyframes,
            50.0,
            fixations=pd.DataFrame({"x_px": [810.0], "y_px": [520.0]}),
            max_interpolation_gap_ms=100.0,
            title="Synthetic/demo dynamic AOI at 50 ms",
        ),
        args.output_dir / "06_dynamic_aoi.png",
    )

    print(f"Wrote six synthetic/demo figures to {args.output_dir.resolve()}")
    print("These figures are software examples, not empirical validation evidence.")


if __name__ == "__main__":
    main()
