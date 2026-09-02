import numpy as np
import pandas as pd
import pytest

from gazeforge.cross_dataset import (
    prepare_cross_dataset_event_benchmark,
    run_cross_dataset_event_validation,
)
from gazeforge.exceptions import SchemaError
from gazeforge.schema import GazeFrame


def _dataset(name: str, *, verified: bool = True, resolved: bool = True) -> GazeFrame:
    rows = []
    rate = 120.0
    dt = 1000.0 / rate
    participants = ["P1", "P2", "P3"] if resolved else ["__unresolved__"]
    for participant in participants:
        for sample in range(90):
            if sample < 30:
                label = "fixation"
                x = 100.0 + 0.05 * sample
            elif sample < 60:
                label = "saccade"
                x = 110.0 + 6.0 * (sample - 30)
            else:
                label = "pursuit"
                x = 290.0 + 0.7 * (sample - 60)
            rows.append(
                {
                    "participant_id": participant,
                    "trial_id": f"{participant}_trial",
                    "timestamp_ms": sample * dt,
                    "x_px": x,
                    "y_px": 200.0 + 0.2 * np.sin(sample / 5.0),
                    "event_label": label,
                    "dataset_id": name,
                    "source_file": f"{participant}.synthetic",
                }
            )
    return GazeFrame(
        data=pd.DataFrame(rows),
        sampling_rate_hz=rate,
        metadata={
            "source_dataset": name,
            "participant_identity_resolved": resolved,
            "coordinate_source_unit": "pixels" if verified else "unverified",
            "coordinate_unit_verified": verified,
        },
    )


def test_prepare_cross_dataset_requires_verified_coordinates():
    with pytest.raises(SchemaError, match="verified coordinate unit"):
        prepare_cross_dataset_event_benchmark(
            {"A": _dataset("A"), "B": _dataset("B", verified=False)},
            target_sampling_rate_hz=60.0,
        )


def test_prepare_cross_dataset_requires_resolved_participants():
    with pytest.raises(SchemaError, match="resolved participant"):
        prepare_cross_dataset_event_benchmark(
            {"A": _dataset("A"), "B": _dataset("B", resolved=False)},
            target_sampling_rate_hz=60.0,
        )


def test_prepare_cross_dataset_namespaces_identities_and_harmonises_labels():
    prepared = prepare_cross_dataset_event_benchmark(
        {"A": _dataset("A"), "B": _dataset("B")},
        target_sampling_rate_hz=60.0,
        min_label_purity=0.75,
    )
    assert prepared.data["dataset_id"].nunique() == 2
    assert set(prepared.data["event_label"]) == {"fixation", "saccade", "pursuit"}
    assert prepared.data["participant_id"].str.startswith(("A::", "B::")).all()
    assert prepared.data["source_participant_id"].isin({"P1", "P2", "P3"}).all()
    assert prepared.design["participant_namespace_policy"].startswith("dataset_id::")
    assert all(
        report["sampling_origin_at_analysis"] == "resampled"
        for report in prepared.dataset_reports.values()
    )


def test_prepare_cross_dataset_refuses_upsampling():
    with pytest.raises(ValueError, match="will not upsample"):
        prepare_cross_dataset_event_benchmark(
            {"A": _dataset("A"), "B": _dataset("B")},
            target_sampling_rate_hz=250.0,
        )


def test_cross_dataset_validation_runs_fresh_models_per_held_out_dataset():
    prepared = prepare_cross_dataset_event_benchmark(
        {"A": _dataset("A"), "B": _dataset("B")},
        target_sampling_rate_hz=60.0,
    )
    result = run_cross_dataset_event_validation(
        prepared,
        n_estimators=20,
        hidden_layer_sizes=(8,),
        temporal_solver="lbfgs",
        temporal_max_iter=120,
        context_radius_ms=20.0,
        rolling_window_ms=40.0,
        calibration_bins=4,
    )
    assert set(result.summary["model"]) == {"RandomForest", "ContextMLP"}
    assert set(result.summary["held_out_dataset"]) == {"A", "B"}
    assert len(result.summary) == 4
    assert len(result.report_fingerprint_sha256) == 64
    for validation in (result.random_forest, result.context_mlp):
        assert set(validation.predictions["held_out_dataset"]) == {"A", "B"}
        assert validation.folds["held_out_dataset"].nunique() == 2
