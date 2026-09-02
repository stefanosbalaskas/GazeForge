import pandas as pd
import pytest

from gazeforge import sample_label_agreement
from gazeforge.exceptions import SchemaError


def _labels(values):
    return pd.DataFrame(
        {
            "participant_id": "P1",
            "trial_id": "T1",
            "timestamp_ms": [0.0, 2.0, 4.0, 6.0],
            "event_label": values,
        }
    )


def test_sample_label_agreement_reports_kappa_and_confusion():
    result = sample_label_agreement(
        _labels(["fixation", "fixation", "saccade", "saccade"]),
        _labels(["fixation", "saccade", "saccade", "saccade"]),
    )
    assert result["n_aligned_samples"] == 4
    assert result["exact_agreement"] == pytest.approx(0.75)
    assert -1 <= result["cohen_kappa"] <= 1
    assert set(result["labels"]) == {"fixation", "saccade"}


def test_sample_label_agreement_rejects_duplicate_keys():
    left = _labels(["fixation"] * 4)
    left.loc[1, "timestamp_ms"] = 0.0
    with pytest.raises(SchemaError):
        sample_label_agreement(left, _labels(["fixation"] * 4))
