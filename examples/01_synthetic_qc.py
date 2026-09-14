"""Minimal deterministic GazeForge quality-control walkthrough."""

from gazeforge import ai_flag_anomalies, canonicalize_gaze, score_trial_quality, simulate_gaze


def main() -> None:
    raw = simulate_gaze(
        n_participants=4,
        n_trials=3,
        samples_per_trial=240,
        sampling_rate_hz=60,
        random_state=42,
    )
    gaze = canonicalize_gaze(
        raw,
        sampling_rate_hz=60,
        screen_size_px=(1920, 1080),
    )
    flagged = ai_flag_anomalies(
        gaze.data,
        sampling_rate_hz=gaze.sampling_rate_hz,
        random_state=42,
    )
    quality = score_trial_quality(flagged, screen_size_px=(1920, 1080))

    columns = [
        "participant_id",
        "trial_id",
        "missing_rate",
        "offscreen_rate",
        "anomaly_rate",
        "large_gap_rate",
        "quality_score",
    ]
    print(quality[columns].to_string(index=False))


if __name__ == "__main__":
    main()
