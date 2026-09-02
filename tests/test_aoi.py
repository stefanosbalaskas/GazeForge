import pandas as pd

from gazeforge.aoi import (
    AOI,
    CallableAOIProvider,
    aois_to_frame,
    apply_aoi_review,
    detect_semantic_aois,
    map_fixations_to_aois,
)


def test_semantic_provider_threshold_and_mapping():
    def detector(image, labels):
        return [
            AOI("a1", labels[0], 0, 0, 100, 100, confidence=0.9, source="ai"),
            AOI("a2", labels[1], 50, 50, 150, 150, confidence=0.4, source="ai"),
        ]

    provider = CallableAOIProvider(detector, model_name="test", model_version="1")
    aois = detect_semantic_aois(
        object(), labels=["claim", "logo"], provider=provider, min_confidence=0.3
    )
    assert len(aois) == 2
    frame = aois_to_frame(aois)
    assert frame.loc[0, "label"] == "claim"

    fix = pd.DataFrame({"x_px": [75, 125, 200], "y_px": [75, 125, 200]})
    mapped = map_fixations_to_aois(fix, aois, overlap_rule="highest_confidence")
    assert mapped.loc[0, "aoi_id"] == "a1"
    assert mapped.loc[1, "aoi_id"] == "a2"
    assert pd.isna(mapped.loc[2, "aoi_id"])


def test_human_aoi_review():
    aois = [AOI("a1", "old", 0, 0, 20, 20, confidence=0.7, source="ai")]
    decisions = pd.DataFrame([{"aoi_id": "a1", "action": "relabel", "label": "claim"}])
    reviewed, log = apply_aoi_review(aois, decisions)
    assert reviewed[0].label == "claim"
    assert reviewed[0].source == "human_corrected"
    assert log.loc[0, "action"] == "relabel"
