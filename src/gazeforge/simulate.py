"""Synthetic data for examples, smoke tests, and pipeline validation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def simulate_gaze(
    *,
    n_participants: int = 4,
    n_trials: int = 3,
    samples_per_trial: int = 240,
    sampling_rate_hz: float = 60.0,
    screen_size_px: tuple[int, int] = (1920, 1080),
    random_state: int = 42,
) -> pd.DataFrame:
    """Simulate smooth gaze with occasional saccade-like jumps and missing samples."""
    rng = np.random.default_rng(random_state)
    width, height = screen_size_px
    dt = 1000.0 / sampling_rate_hz
    rows: list[dict[str, object]] = []

    for participant in range(n_participants):
        for trial in range(n_trials):
            x = width * (0.35 + 0.3 * rng.random())
            y = height * (0.35 + 0.3 * rng.random())
            for sample in range(samples_per_trial):
                if sample and sample % max(20, samples_per_trial // 5) == 0:
                    x += rng.normal(0, width * 0.16)
                    y += rng.normal(0, height * 0.12)
                else:
                    x += rng.normal(0, 6)
                    y += rng.normal(0, 5)
                x = float(np.clip(x, 0, width))
                y = float(np.clip(y, 0, height))
                pupil = 3.3 + rng.normal(0, 0.12)
                if rng.random() < 0.015:
                    x_out, y_out = np.nan, np.nan
                else:
                    x_out, y_out = x, y
                rows.append(
                    {
                        "participant_id": f"P{participant + 1:03d}",
                        "trial_id": f"T{trial + 1:02d}",
                        "timestamp_ms": sample * dt,
                        "x_px": x_out,
                        "y_px": y_out,
                        "pupil": pupil,
                    }
                )
    return pd.DataFrame(rows)
