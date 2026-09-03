import numpy as np
import pandas as pd
import pytest

from gazeforge.exceptions import SchemaError
from gazeforge.stratified import summarize_event_predictions_by_stratum


def _prediction_fixture():
    rows = []
    strata = ("image", "moving_dot", "video")
    for fold in (1, 2):
        for stratum_index, stratum in enumerate(strata):
            participant = f"P{fold}{stratum_index}"
            trial = f"{participant}_{stratum}"
            for model in ("I-VT", "RandomForest"):
                for sample in range(8):
                    truth = "fixation" if sample < 5 else "saccade"
                    predicted = truth
                    if sample == 6 and stratum == "video":
                        predicted = "fixation"
                    row = {
                        "participant_id": participant,
                        "trial_id": trial,
                        "timestamp_ms": sample * (1000.0 / 60.0),
                        "event_label": truth,
                        "predicted_event": predicted,
                        "comparison_model": model,
                        "validation_fold": fold,
                        "stimulus_type": stratum,
                    }
                    if model == "RandomForest":
                        if predicted == "fixation":
                            row["p_event_fixation"] = 0.85
                            row["p_event_saccade"] = 0.15
                        else:
                            row["p_event_fixation"] = 0.10
                            row["p_event_saccade"] = 0.90
                        row["event_confidence"] = max(
                            row["p_event_fixation"],
                            row["p_event_saccade"],
                        )
                    rows.append(row)
    return pd.DataFrame(rows)


def test_stratified_metrics_cover_three_families_without_refitting():
    result = summarize_event_predictions_by_stratum(
        _prediction_fixture(),
        stratify_col="stimulus_type",
        sampling_rate_hz=60.0,
        calibration_bins=4,
    )

    assert set(result.summary["stratum"]) == {"image", "moving_dot", "video"}
    assert set(result.summary["model"]) == {"I-VT", "RandomForest"}
    assert result.design["models_refit_by_stratum"] is False
    assert (result.summary["n_folds"] == 2).all()
    assert (result.summary["n_test_rows_total"] == 16).all()
    assert result.fold_metrics["event_f1"].between(0, 1).all()


def test_stratified_metrics_do_not_fabricate_ivt_calibration():
    result = summarize_event_predictions_by_stratum(
        _prediction_fixture(),
        stratify_col="stimulus_type",
        sampling_rate_hz=60.0,
        calibration_bins=4,
    )

    ivt = result.fold_metrics[result.fold_metrics["model"] == "I-VT"]
    learned = result.fold_metrics[result.fold_metrics["model"] == "RandomForest"]
    assert ivt["multiclass_brier_score"].isna().all()
    assert ivt["expected_calibration_error"].isna().all()
    assert learned["multiclass_brier_score"].notna().all()
    assert learned["expected_calibration_error"].notna().all()
    assert np.isfinite(learned["macro_f1"]).all()


def test_stratified_event_metrics_reject_trial_crossing_strata():
    predictions = _prediction_fixture()
    mask = (
        (predictions["comparison_model"] == "I-VT")
        & (predictions["validation_fold"] == 1)
        & (predictions["trial_id"] == "P10_image")
    )
    index = predictions.index[mask][-1]
    predictions.loc[index, "stimulus_type"] = "video"

    with pytest.raises(SchemaError, match="exactly one stratum"):
        summarize_event_predictions_by_stratum(
            predictions,
            stratify_col="stimulus_type",
            sampling_rate_hz=60.0,
        )


def test_stratified_metrics_can_skip_event_level_analysis():
    predictions = _prediction_fixture().drop(columns=["trial_id"])
    result = summarize_event_predictions_by_stratum(
        predictions,
        stratify_col="stimulus_type",
        sampling_rate_hz=60.0,
        include_event_level_metrics=False,
    )

    assert result.fold_metrics["event_f1"].isna().all()
    assert result.design["include_event_level_metrics"] is False
