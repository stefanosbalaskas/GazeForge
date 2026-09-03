from gazeforge import (
    GAZE_IN_WILD_LABELS,
    gaze_in_wild_manual_event_card,
    load_gaze_in_wild_directory,
    load_gaze_in_wild_mat,
)


def test_gaze_in_wild_card_is_native_low_rate_human_reference():
    card = gaze_in_wild_manual_event_card()
    assert card.sampling_rates_hz == [120.0]
    assert card.sampling_origin == "native"
    assert card.annotation_origin == "human-manual"
    assert card.reference_strength == "human-reference"
    assert card.human_annotator_count == 5
    assert card.is_native_human_reference
    assert "head-free" in card.task


def test_gaze_in_wild_public_api_is_exposed():
    assert GAZE_IN_WILD_LABELS[1] == "fixation"
    assert callable(load_gaze_in_wild_mat)
    assert callable(load_gaze_in_wild_directory)
