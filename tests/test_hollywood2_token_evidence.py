import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_token_evidence import (
    HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES,
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION,
    _canonicalize_metric_value,
)


def test_hollywood2_metric_canonicalization_removes_last_bit_drift() -> None:
    first = {
        "ece": 0.02320059813772811,
        "nested": [{"ece": 0.02505730628886507}],
    }
    second = {
        "ece": 0.023200598137728116,
        "nested": [{"ece": 0.025057306288865093}],
    }
    assert _canonicalize_metric_value(first) == _canonicalize_metric_value(second)
    assert _canonicalize_metric_value(first)["ece"] == 0.023200598137728
    assert HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES == 15


def test_hollywood2_metric_canonicalization_is_metrics_only_contract() -> None:
    assert HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION == {
        "method": "recursive_round_finite_metric_floats",
        "metric_float_decimal_places": 15,
        "nonfinite_metric_floats_permitted": False,
        "benchmark_model_protocol_numeric_values_rounded": False,
    }
    value = {"integer": 4, "token": "001", "flag": False, "values": (0.12345678901234567,)}
    canonical = _canonicalize_metric_value(value)
    assert canonical["integer"] == 4
    assert canonical["token"] == "001"
    assert canonical["flag"] is False
    assert canonical["values"] == [0.123456789012346]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_hollywood2_metric_canonicalization_rejects_nonfinite_values(value: float) -> None:
    with pytest.raises(BenchmarkIntegrityError, match="non-finite"):
        _canonicalize_metric_value({"metric": value})
