"""Tests for optional, non-mutating visual diagnostics."""

from __future__ import annotations

import matplotlib
import pandas as pd
import pandas.testing as pdt
import pytest

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from gazeforge.aoi import AOI
from gazeforge.dynamic_aoi import DynamicAOIKeyframe
from gazeforge.exceptions import SchemaError
from gazeforge.visualization import (
    plot_aoi_overlay,
    plot_dynamic_aoi_snapshot,
    plot_event_calibration,
    plot_event_probabilities,
    plot_qc_timeline,
    plot_scanpath,
)


def test_plot_qc_timeline_marks_flags_without_mutation() -> None:
    data = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 16.7, 33.4, 50.1],
            "qc_anomaly_score": [0.1, 0.2, 0.9, 0.15],
            "qc_flag": [False, False, True, False],
        }
    )
    before = data.copy(deep=True)
    axis = plot_qc_timeline(data)
    assert axis.get_xlabel() == "Time (ms)"
    assert len(axis.lines) == 1
    assert len(axis.collections) == 1
    pdt.assert_frame_equal(data, before)
    plt.close(axis.figure)


def test_plot_event_probabilities_uses_styles_and_threshold() -> None:
    predictions = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 16.7, 33.4],
            "p_event_fixation": [0.8, 0.6, 0.2],
            "p_event_saccade": [0.1, 0.3, 0.7],
            "p_event_noise": [0.1, 0.1, 0.1],
        }
    )
    axis = plot_event_probabilities(predictions, confidence_threshold=0.6)
    assert len(axis.lines) == 4
    assert {line.get_linestyle() for line in axis.lines[:3]} == {"-", "--", "-."}
    assert axis.get_ylim() == pytest.approx((0.0, 1.0))
    plt.close(axis.figure)


def test_plot_event_calibration_draws_ideal_and_observed() -> None:
    predictions = pd.DataFrame(
        {
            "event_label": ["fixation", "fixation", "saccade", "saccade"],
            "p_event_fixation": [0.9, 0.7, 0.3, 0.2],
            "p_event_saccade": [0.1, 0.3, 0.7, 0.8],
        }
    )
    axis = plot_event_calibration(predictions, n_bins=4)
    assert [line.get_label() for line in axis.lines] == ["ideal", "observed"]
    assert axis.get_xlim() == pytest.approx((0.0, 1.0))
    plt.close(axis.figure)


def test_plot_aoi_overlay_supports_caller_axis_and_fixations() -> None:
    aois = [
        AOI("logo", "logo", 10, 20, 110, 90),
        AOI("claim", "claim", 150, 40, 330, 130),
    ]
    fixations = pd.DataFrame({"x_px": [30.0, 210.0], "y_px": [50.0, 80.0]})
    figure, supplied = plt.subplots()
    returned = plot_aoi_overlay(aois, fixations=fixations, ax=supplied)
    assert returned is supplied
    assert len(returned.patches) == 2
    assert len(returned.texts) == 2
    assert len(returned.collections) == 1
    plt.close(figure)


def test_plot_scanpath_adds_order_annotations() -> None:
    fixations = pd.DataFrame(
        {
            "x_px": [100.0, 220.0, 160.0],
            "y_px": [120.0, 180.0, 260.0],
            "aoi_label": ["logo", "claim", "product"],
        }
    )
    axis = plot_scanpath(fixations)
    assert len(axis.lines) == 1
    assert [text.get_text() for text in axis.texts] == [
        "1 · logo",
        "2 · claim",
        "3 · product",
    ]
    plt.close(axis.figure)


def test_plot_dynamic_aoi_snapshot_respects_interpolation_gap() -> None:
    keyframes = [
        DynamicAOIKeyframe("product", "product", 0.0, 0, 0, 100, 100),
        DynamicAOIKeyframe("product", "product", 100.0, 20, 0, 120, 100),
    ]
    interpolated = plot_dynamic_aoi_snapshot(keyframes, 50.0, max_interpolation_gap_ms=100.0)
    assert len(interpolated.patches) == 1
    assert interpolated.patches[0].get_x() == pytest.approx(10.0)
    plt.close(interpolated.figure)

    blocked = plot_dynamic_aoi_snapshot(keyframes, 50.0, max_interpolation_gap_ms=40.0)
    assert len(blocked.patches) == 0
    plt.close(blocked.figure)


def test_visualization_input_validation_is_explicit() -> None:
    with pytest.raises(SchemaError, match="QC timeline input"):
        plot_qc_timeline(pd.DataFrame({"timestamp_ms": [0.0]}))
    with pytest.raises(ValueError, match="confidence_threshold"):
        plot_event_probabilities(
            pd.DataFrame({"timestamp_ms": [0.0], "p_event_fixation": [1.0]}),
            confidence_threshold=1.1,
        )
    with pytest.raises(SchemaError, match="label column"):
        plot_scanpath(pd.DataFrame({"x_px": [1.0], "y_px": [2.0]}))
