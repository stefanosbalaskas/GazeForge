import builtins
import sys
import types

import numpy as np
import pandas as pd
import pytest

from gazeforge.aoi import (
    AOI,
    CallableAOIProvider,
    HuggingFaceZeroShotAOIProvider,
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



@pytest.mark.parametrize(
    "kwargs",
    [
        {"xmin": 1, "ymin": 0, "xmax": 1, "ymax": 2},
        {"xmin": 0, "ymin": 2, "xmax": 1, "ymax": 2},
    ],
)
def test_aoi_rejects_nonpositive_geometry(kwargs):
    with pytest.raises(ValueError, match="AOI bounds"):
        AOI("bad", "bad", confidence=0.5, **kwargs)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_aoi_rejects_confidence_outside_probability_range(confidence):
    with pytest.raises(ValueError, match="confidence"):
        AOI("bad", "bad", 0, 0, 1, 1, confidence=confidence)


def test_callable_aoi_provider_materializes_detector_iterable():
    provider = CallableAOIProvider(
        lambda image, labels: (
            AOI(str(index), label, index, 0, index + 1, 1)
            for index, label in enumerate(labels)
        )
    )

    detected = provider.detect(object(), ["claim", "logo"])

    assert [aoi.label for aoi in detected] == ["claim", "logo"]


def test_huggingface_provider_reports_missing_optional_dependency(monkeypatch):
    provider = HuggingFaceZeroShotAOIProvider()
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "transformers":
            raise ImportError("synthetic missing dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with pytest.raises(Exception, match="vision"):
        provider._get_pipeline()


def test_huggingface_provider_builds_caches_and_maps_detector_output(monkeypatch):
    calls = []

    def fake_pipeline(*, task, model, device):
        calls.append((task, model, device))

        def detector(image, *, candidate_labels):
            assert image == "image"
            assert candidate_labels == ["claim"]
            return [
                {
                    "label": "claim",
                    "score": 0.875,
                    "box": {"xmin": 1, "ymin": 2, "xmax": 11, "ymax": 22},
                }
            ]

        return detector

    module = types.ModuleType("transformers")
    module.pipeline = fake_pipeline
    monkeypatch.setitem(sys.modules, "transformers", module)

    provider = HuggingFaceZeroShotAOIProvider(
        model_name="synthetic/owl",
        model_version="test-version",
        device="cpu",
    )
    pipeline = provider._get_pipeline()
    assert provider._get_pipeline() is pipeline

    aois = provider.detect("image", ["claim"])

    assert calls == [("zero-shot-object-detection", "synthetic/owl", "cpu")]
    assert aois == [
        AOI(
            "ai_0000",
            "claim",
            1.0,
            2.0,
            11.0,
            22.0,
            confidence=0.875,
            source="ai",
            model_name="synthetic/owl",
            model_version="test-version",
        )
    ]


def test_huggingface_provider_requires_at_least_one_label():
    provider = HuggingFaceZeroShotAOIProvider(_pipeline=lambda *args, **kwargs: [])

    with pytest.raises(ValueError, match="At least one semantic label"):
        provider.detect(object(), [])


@pytest.mark.parametrize("threshold", [-0.01, 1.01])
def test_semantic_aoi_detection_rejects_invalid_threshold(threshold):
    provider = CallableAOIProvider(lambda image, labels: [])

    with pytest.raises(ValueError, match="min_confidence"):
        detect_semantic_aois(
            object(),
            labels=["claim"],
            provider=provider,
            min_confidence=threshold,
        )


def test_aois_to_frame_preserves_complete_review_metadata():
    aois = [
        AOI(
            "a1",
            "claim",
            1,
            2,
            3,
            4,
            confidence=0.8,
            source="ai",
            model_name="model",
            model_version="1",
        )
    ]

    frame = aois_to_frame(aois)

    assert frame.to_dict("records") == [
        {
            "aoi_id": "a1",
            "label": "claim",
            "xmin": 1,
            "ymin": 2,
            "xmax": 3,
            "ymax": 4,
            "confidence": 0.8,
            "source": "ai",
            "model_name": "model",
            "model_version": "1",
        }
    ]


def test_aoi_review_requires_action_columns_and_known_identifiers():
    aois = [AOI("a1", "claim", 0, 0, 10, 10)]

    with pytest.raises(Exception, match="require columns"):
        apply_aoi_review(aois, pd.DataFrame({"aoi_id": ["a1"]}))

    decisions = pd.DataFrame([{"aoi_id": "missing", "action": "accept"}])
    with pytest.raises(Exception, match="unknown AOI"):
        apply_aoi_review(aois, decisions)


def test_aoi_review_accept_and_reject_are_explicit_and_logged():
    aois = [
        AOI("a1", "claim", 0, 0, 10, 10, source="ai"),
        AOI("a2", "logo", 20, 20, 30, 30, source="ai"),
    ]
    decisions = pd.DataFrame(
        [
            {"aoi_id": "a1", "action": " ACCEPT "},
            {"aoi_id": "a2", "action": "reject"},
        ]
    )

    reviewed, log = apply_aoi_review(aois, decisions)

    assert [aoi.aoi_id for aoi in reviewed] == ["a1"]
    assert reviewed[0].source == "human_reviewed"
    assert log.to_dict("records") == [
        {
            "aoi_id": "a1",
            "action": "accept",
            "before_label": "claim",
            "after_label": "claim",
            "reviewed": True,
        },
        {
            "aoi_id": "a2",
            "action": "reject",
            "before_label": "logo",
            "after_label": None,
            "reviewed": True,
        },
    ]


def test_aoi_review_relabel_requires_label():
    aois = [AOI("a1", "claim", 0, 0, 10, 10)]
    decisions = pd.DataFrame([{"aoi_id": "a1", "action": "relabel"}])

    with pytest.raises(Exception, match="requires a label"):
        apply_aoi_review(aois, decisions)


def test_aoi_review_replace_bounds_requires_all_coordinates_and_valid_geometry():
    aois = [AOI("a1", "claim", 0, 0, 10, 10)]

    incomplete = pd.DataFrame(
        [{"aoi_id": "a1", "action": "replace_bounds", "xmin": 1}]
    )
    with pytest.raises(Exception, match="requires all bounds"):
        apply_aoi_review(aois, incomplete)

    invalid = pd.DataFrame(
        [
            {
                "aoi_id": "a1",
                "action": "replace_bounds",
                "xmin": 5,
                "ymin": 1,
                "xmax": 4,
                "ymax": 8,
            }
        ]
    )
    with pytest.raises(ValueError, match="AOI bounds"):
        apply_aoi_review(aois, invalid)


def test_aoi_review_replace_bounds_updates_geometry_and_source():
    aois = [AOI("a1", "claim", 0, 0, 10, 10, source="ai")]
    decisions = pd.DataFrame(
        [
            {
                "aoi_id": "a1",
                "action": "replace_bounds",
                "xmin": 1,
                "ymin": 2,
                "xmax": 11,
                "ymax": 12,
            }
        ]
    )

    reviewed, log = apply_aoi_review(aois, decisions)

    assert reviewed[0] == AOI(
        "a1",
        "claim",
        1,
        2,
        11,
        12,
        source="human_corrected",
    )
    assert log.loc[0, "after_label"] == "claim"


def test_aoi_review_rejects_unsupported_action():
    aois = [AOI("a1", "claim", 0, 0, 10, 10)]
    decisions = pd.DataFrame([{"aoi_id": "a1", "action": "merge"}])

    with pytest.raises(Exception, match="Unsupported AOI review action"):
        apply_aoi_review(aois, decisions)


def test_fixation_mapping_validates_coordinate_and_overlap_contracts():
    fixations = pd.DataFrame({"x_px": [1.0]})

    with pytest.raises(Exception, match="coordinate columns"):
        map_fixations_to_aois(fixations, [])

    complete = pd.DataFrame({"x_px": [1.0], "y_px": [1.0]})
    with pytest.raises(ValueError, match="overlap_rule"):
        map_fixations_to_aois(complete, [], overlap_rule="unknown")


def test_fixation_mapping_handles_nonfinite_points_and_all_overlap_rules():
    large = AOI("large", "large", 0, 0, 10, 10, confidence=0.9)
    small = AOI("small", "small", 2, 2, 6, 6, confidence=0.8)
    equal_conf_small = AOI("tie-small", "tie-small", 3, 3, 5, 5, confidence=0.9)
    fixations = pd.DataFrame(
        {
            "x_px": [4.0, np.nan, 20.0],
            "y_px": [4.0, 4.0, 20.0],
        }
    )

    highest = map_fixations_to_aois(
        fixations,
        [large, small, equal_conf_small],
        overlap_rule="highest_confidence",
    )
    smallest = map_fixations_to_aois(
        fixations,
        [large, small, equal_conf_small],
        overlap_rule="smallest_area",
    )
    first = map_fixations_to_aois(
        fixations,
        [small, large],
        overlap_rule="first",
    )

    assert highest.loc[0, "aoi_id"] == "tie-small"
    assert smallest.loc[0, "aoi_id"] == "tie-small"
    assert first.loc[0, "aoi_id"] == "small"
    assert highest["aoi_id"].isna().tolist() == [False, True, True]
    assert np.isnan(highest.loc[1, "aoi_confidence"])
    assert pd.isna(highest.loc[2, "aoi_source"])


def test_fixation_mapping_records_audit_trail_parameters():
    class Trail:
        def __init__(self):
            self.calls = []

        def add(self, **kwargs):
            self.calls.append(kwargs)

    trail = Trail()
    fixations = pd.DataFrame({"gx": [5.0], "gy": [5.0]})
    aois = [AOI("a1", "claim", 0, 0, 10, 10)]

    mapped = map_fixations_to_aois(
        fixations,
        aois,
        x_col="gx",
        y_col="gy",
        trail=trail,
    )

    assert mapped.loc[0, "aoi_id"] == "a1"
    assert len(trail.calls) == 1
    call = trail.calls[0]
    assert call["operation"] == "map_fixations_to_aois"
    assert call["input_data"] is fixations
    assert call["parameters"] == {
        "x_col": "gx",
        "y_col": "gy",
        "overlap_rule": "highest_confidence",
        "n_aois": 1,
    }
