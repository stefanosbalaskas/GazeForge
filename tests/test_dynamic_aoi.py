import pandas as pd

from gazeforge import (
    CallableDynamicAOIProvider,
    DynamicAOIKeyframe,
    detect_dynamic_aois,
    dynamic_aois_to_frame,
    interpolate_dynamic_aoi,
    map_fixations_to_dynamic_aois,
)


def _track():
    return [
        DynamicAOIKeyframe(
            "claim",
            "claim",
            0,
            0,
            0,
            100,
            100,
            confidence=0.8,
            source="ai",
            model_name="tracker",
            model_version="1",
        ),
        DynamicAOIKeyframe(
            "claim",
            "claim",
            100,
            100,
            0,
            200,
            100,
            confidence=1.0,
            source="ai",
            model_name="tracker",
            model_version="1",
        ),
    ]


def test_dynamic_interpolation_and_no_extrapolation():
    middle = interpolate_dynamic_aoi(_track(), 50, max_gap_ms=100)
    assert middle is not None
    assert middle.xmin == 50
    assert middle.xmax == 150
    assert middle.confidence == 0.9
    assert middle.source == "interpolated"
    assert interpolate_dynamic_aoi(_track(), -1, max_gap_ms=100) is None
    assert interpolate_dynamic_aoi(_track(), 101, max_gap_ms=100) is None


def test_dynamic_interpolation_refuses_large_temporal_gap():
    assert interpolate_dynamic_aoi(_track(), 50, max_gap_ms=75) is None


def test_dynamic_mapping_preserves_temporal_provenance():
    fixations = pd.DataFrame(
        {
            "timestamp_ms": [0, 50, 100, 150],
            "x_px": [50, 75, 150, 150],
            "y_px": [50, 50, 50, 50],
        }
    )
    mapped = map_fixations_to_dynamic_aois(
        fixations,
        _track(),
        max_interpolation_gap_ms=100,
    )
    assert mapped.loc[0, "aoi_id"] == "claim"
    assert mapped.loc[1, "aoi_source"] == "interpolated"
    assert mapped.loc[2, "aoi_model_name"] == "tracker"
    assert pd.isna(mapped.loc[3, "aoi_id"])


def test_dynamic_provider_threshold_and_reviewable_table():
    def tracker(stimulus, labels):
        return [
            DynamicAOIKeyframe("a", labels[0], 0, 0, 0, 10, 10, confidence=0.9),
            DynamicAOIKeyframe("b", labels[1], 0, 20, 20, 30, 30, confidence=0.1),
        ]

    provider = CallableDynamicAOIProvider(tracker, model_name="custom", model_version="1")
    detected = detect_dynamic_aois(
        object(),
        labels=["claim", "logo"],
        provider=provider,
        min_confidence=0.5,
    )
    assert len(detected) == 1
    frame = dynamic_aois_to_frame(detected)
    assert frame.loc[0, "label"] == "claim"
