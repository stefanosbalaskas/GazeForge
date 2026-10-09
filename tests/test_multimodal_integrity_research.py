import pandas as pd
import pytest

from gazeforge.multimodal_integrity_research import (
    audit_multimodal_pairing,
    audit_temporal_session_separation,
    reliability_weighted_fusion,
)


def test_split_axes_do_not_collapse_into_a_single_flag():
    train = pd.DataFrame({
        "participant_id": ["a"], "session_id": ["s1"], "temporal_block_id": ["b1"]
    })
    test = pd.DataFrame({
        "participant_id": ["a"], "session_id": ["s2"], "temporal_block_id": ["b2"]
    })
    result = audit_temporal_session_separation(train, test)
    assert result["temporal_block_disjoint"]
    assert result["session_disjoint"]
    assert not result["participant_disjoint"]
    assert result["trial_separation_certified"] is False
    assert result["trial_disjoint"] is None


def test_cross_source_is_not_labeled_fused():
    left = pd.DataFrame({"participant_id": ["a"], "trial_id": ["1"]})
    right = pd.DataFrame({"participant_id": ["b"], "trial_id": ["1"]})
    out = audit_multimodal_pairing({"eye": left, "eda": right})
    assert out["classification"] == "unpaired_cross_source"
    assert out["clock_alignment_certified"] is False
    right.loc[0, "participant_id"] = "a"
    paired = audit_multimodal_pairing({"eye": left, "eda": right})
    assert paired["classification"] == "paired_within_trial_not_time_certified"


def test_fusion_requires_explicit_scales_and_valid_qc():
    frame = pd.DataFrame({
        "gaze": [2., 3., 4.], "eda": [6., 8., 9.],
        "q_gaze": [1., 0., None], "q_eda": [1., 1., 0.],
    })
    with pytest.raises(ValueError, match="commensurate"):
        reliability_weighted_fusion(
            frame, value_cols=["gaze", "eda"], weight_cols=["q_gaze", "q_eda"]
        )
    out = reliability_weighted_fusion(
        frame, value_cols=["gaze", "eda"], weight_cols=["q_gaze", "q_eda"],
        values_are_commensurate=True,
    )
    assert out["fused_value"].iloc[0] == pytest.approx(4)
    assert out["fused_value"].iloc[1] == pytest.approx(8)
    assert pd.isna(out["fused_value"].iloc[2])
    assert out["n_contributing_modalities"].tolist() == [2, 1, 0]


def test_trial_disjointness_does_not_alias_session_or_block():
    train = pd.DataFrame({
        "participant_id": ["a"], "session_id": ["s1"],
        "trial_id": ["t1"], "temporal_block_id": ["b1"],
    })
    test = pd.DataFrame({
        "participant_id": ["a"], "session_id": ["s1"],
        "trial_id": ["t2"], "temporal_block_id": ["b1"],
    })
    result = audit_temporal_session_separation(train, test)
    assert result["trial_separation_certified"] is True
    assert result["trial_disjoint"] is True
    assert result["trial_overlap"] == 0
    assert result["temporal_block_disjoint"] is False
    assert result["session_disjoint"] is False
    assert result["participant_disjoint"] is False
    test["trial_id"] = "t1"
    shared = audit_temporal_session_separation(train, test)
    assert shared["trial_overlap"] == 1
    assert shared["trial_disjoint"] is False
