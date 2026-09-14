"""Transparent I-VT eye-event baseline on deterministic synthetic gaze."""

from gazeforge import canonicalize_gaze, ivt_classify_events, simulate_gaze


def main() -> None:
    raw = simulate_gaze(
        n_participants=3,
        n_trials=2,
        samples_per_trial=300,
        sampling_rate_hz=60,
        random_state=42,
    )
    gaze = canonicalize_gaze(
        raw,
        sampling_rate_hz=60,
        screen_size_px=(1920, 1080),
    )
    classified = ivt_classify_events(
        gaze.data,
        sampling_rate_hz=gaze.sampling_rate_hz,
        velocity_threshold_px_s=1000.0,
    )

    print(classified["predicted_event"].value_counts().to_string())

    participant = classified["participant_id"].iloc[0]
    trial = classified["trial_id"].iloc[0]
    first_trial = classified.loc[
        (classified["participant_id"] == participant)
        & (classified["trial_id"] == trial),
        ["participant_id", "trial_id", "timestamp_ms", "predicted_event"],
    ]
    changes = first_trial["predicted_event"].ne(first_trial["predicted_event"].shift())
    print("\nFirst-trial event transitions:")
    print(first_trial.loc[changes].to_string(index=False))


if __name__ == "__main__":
    main()
