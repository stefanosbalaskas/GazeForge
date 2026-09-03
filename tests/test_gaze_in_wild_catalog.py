from gazeforge.benchmark_catalog import gaze_in_wild_manual_event_card


def test_gaze_in_wild_card_is_native_low_rate_human_reference():
    card = gaze_in_wild_manual_event_card()
    assert card.sampling_rates_hz == [120.0]
    assert card.sampling_origin == "native"
    assert card.annotation_origin == "human-manual"
    assert card.reference_strength == "human-reference"
    assert card.human_annotator_count == 5
    assert card.is_native_human_reference
    assert "head-free" in card.task
