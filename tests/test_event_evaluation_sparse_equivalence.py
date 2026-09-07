import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

import gazeforge.event_evaluation as event_evaluation
from gazeforge.event_evaluation import match_event_intervals, temporal_event_iou


def _event_frame(starts, ends, labels):
    starts = np.asarray(starts, dtype=float)
    ends = np.asarray(ends, dtype=float)
    n_events = len(starts)
    return pd.DataFrame(
        {
            "participant_id": ["P1"] * n_events,
            "trial_id": ["T1"] * n_events,
            "event_index": np.arange(1, n_events + 1, dtype=int),
            "event_label": list(labels),
            "start_ms": starts,
            "end_ms": ends,
            "duration_ms": ends - starts,
            "n_samples": np.ones(n_events, dtype=int),
        }
    )


def _random_stream(rng, n_events, *, shift=0.0):
    starts = []
    ends = []
    cursor = float(rng.uniform(-5.0, 5.0) + shift)
    for gap, duration in zip(
        rng.uniform(0.1, 8.0, n_events),
        rng.uniform(1.0, 15.0, n_events),
        strict=True,
    ):
        cursor += float(gap)
        starts.append(cursor)
        cursor += float(duration)
        ends.append(cursor)
    vocabulary = np.asarray(["fixation", "saccade", "pursuit"], dtype=object)
    labels = vocabulary[rng.integers(0, len(vocabulary), n_events)].tolist()
    return _event_frame(starts, ends, labels)


def _dense_reference_matches(predicted, reference, *, min_iou, require_label_match):
    if predicted.empty or reference.empty:
        return []
    ious = np.zeros((len(predicted), len(reference)), dtype=float)
    for pred_pos, (_, pred_row) in enumerate(predicted.iterrows()):
        for ref_pos, (_, ref_row) in enumerate(reference.iterrows()):
            if require_label_match and str(pred_row["event_label"]) != str(
                ref_row["event_label"]
            ):
                continue
            ious[pred_pos, ref_pos] = temporal_event_iou(
                pred_row["start_ms"],
                pred_row["end_ms"],
                ref_row["start_ms"],
                ref_row["end_ms"],
            )
    pred_idx, ref_idx = linear_sum_assignment(1.0 - ious)
    matched = []
    for pred_pos, ref_pos in zip(pred_idx, ref_idx, strict=True):
        iou = float(ious[pred_pos, ref_pos])
        if iou <= 0.0 or iou < float(min_iou):
            continue
        matched.append(
            (
                int(predicted.iloc[int(pred_pos)]["event_index"]),
                int(reference.iloc[int(ref_pos)]["event_index"]),
                iou,
            )
        )
    return matched


def _signature(matches):
    matched = matches.loc[matches["status"] == "matched"]
    false_positive = matches.loc[matches["status"] == "false_positive"]
    false_negative = matches.loc[matches["status"] == "false_negative"]
    return {
        "matched": sorted(
            (
                int(row["predicted_event_index"]),
                int(row["reference_event_index"]),
                round(float(row["iou"]), 14),
            )
            for _, row in matched.iterrows()
        ),
        "false_positive": sorted(
            int(value) for value in false_positive["predicted_event_index"].tolist()
        ),
        "false_negative": sorted(
            int(value) for value in false_negative["reference_event_index"].tolist()
        ),
    }


def _dense_signature(predicted, reference, *, min_iou, require_label_match):
    matched = _dense_reference_matches(
        predicted,
        reference,
        min_iou=min_iou,
        require_label_match=require_label_match,
    )
    matched_pred = {item[0] for item in matched}
    matched_ref = {item[1] for item in matched}
    return {
        "matched": sorted((left, right, round(iou, 14)) for left, right, iou in matched),
        "false_positive": sorted(
            int(value)
            for value in predicted.loc[
                ~predicted["event_index"].isin(matched_pred), "event_index"
            ].tolist()
        ),
        "false_negative": sorted(
            int(value)
            for value in reference.loc[
                ~reference["event_index"].isin(matched_ref), "event_index"
            ].tolist()
        ),
    }


def test_sparse_matching_matches_prior_dense_objective_randomized():
    for seed in range(64):
        rng = np.random.default_rng(seed)
        predicted = _random_stream(rng, int(rng.integers(0, 9)))
        reference = _random_stream(
            rng,
            int(rng.integers(0, 9)),
            shift=float(rng.uniform(-10.0, 10.0)),
        )
        if seed % 2 and len(predicted):
            predicted = predicted.sample(frac=1.0, random_state=seed).reset_index(drop=True)
        if seed % 3 and len(reference):
            reference = reference.sample(frac=1.0, random_state=seed + 1000).reset_index(
                drop=True
            )
        for require_label_match in (True, False):
            for min_iou in (0.0, 0.2, 0.5, 0.75):
                actual = match_event_intervals(
                    predicted,
                    reference,
                    min_iou=min_iou,
                    require_label_match=require_label_match,
                )
                assert _signature(actual) == _dense_signature(
                    predicted,
                    reference,
                    min_iou=min_iou,
                    require_label_match=require_label_match,
                )


def test_sparse_matching_preserves_split_tie_behavior():
    predicted = _event_frame([0.0], [20.0], ["fixation"])
    reference = _event_frame([0.0, 10.0], [10.0, 20.0], ["fixation", "fixation"])
    actual = match_event_intervals(predicted, reference, min_iou=0.5)
    assert _signature(actual) == _dense_signature(
        predicted,
        reference,
        min_iou=0.5,
        require_label_match=True,
    )


def test_sparse_matching_keeps_disconnected_components_independent():
    predicted = _event_frame(
        [0.0, 1000.0, 2000.0],
        [100.0, 1100.0, 2100.0],
        ["fixation", "saccade", "pursuit"],
    )
    reference = _event_frame(
        [10.0, 1010.0, 2010.0],
        [90.0, 1090.0, 2090.0],
        ["fixation", "saccade", "pursuit"],
    )
    actual = match_event_intervals(predicted, reference, min_iou=0.5)
    assert _signature(actual) == _dense_signature(
        predicted,
        reference,
        min_iou=0.5,
        require_label_match=True,
    )


def test_long_one_to_one_stream_avoids_dense_hungarian_matrix(monkeypatch):
    n_events = 5000
    starts = np.arange(n_events, dtype=float) * 20.0
    predicted = _event_frame(starts, starts + 10.0, ["fixation"] * n_events)
    reference = predicted.copy()
    calls = []
    real_assignment = event_evaluation.linear_sum_assignment

    def recording_assignment(cost_matrix):
        calls.append(tuple(cost_matrix.shape))
        return real_assignment(cost_matrix)

    monkeypatch.setattr(event_evaluation, "linear_sum_assignment", recording_assignment)
    matches = match_event_intervals(predicted, reference, min_iou=0.5)
    assert int((matches["status"] == "matched").sum()) == n_events
    assert calls == []
