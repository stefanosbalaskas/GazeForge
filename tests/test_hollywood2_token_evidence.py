import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_token_evidence import (
    HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES,
    HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V1,
    HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2,
    HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V3,
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION,
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1,
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2,
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3,
    _canonicalize_metric_value,
    _validate_numeric_canonicalization_contract,
)


def test_hollywood2_v2_absorbs_original_last_bit_summary_drift() -> None:
    reviewed = {"brier": 0.26322308543548284}
    fresh_worker = {"brier": 0.263223085435484}

    v1_reviewed = _canonicalize_metric_value(
        reviewed,
        decimal_places=HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V1,
    )
    v1_fresh = _canonicalize_metric_value(
        fresh_worker,
        decimal_places=HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V1,
    )
    v2_reviewed = _canonicalize_metric_value(
        reviewed,
        decimal_places=HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2,
    )
    v2_fresh = _canonicalize_metric_value(
        fresh_worker,
        decimal_places=HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2,
    )
    assert v1_reviewed != v1_fresh
    assert v2_reviewed == v2_fresh


def test_hollywood2_v3_absorbs_observed_fold_level_rounding_boundary() -> None:
    reviewed = {"brier": 0.23971548231589268}
    diagnostic_worker = {"brier": 0.2397154823158968}

    v2_reviewed = _canonicalize_metric_value(
        reviewed,
        decimal_places=HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2,
    )
    v2_live = _canonicalize_metric_value(
        diagnostic_worker,
        decimal_places=HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2,
    )
    v3_reviewed = _canonicalize_metric_value(
        reviewed,
        decimal_places=HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V3,
    )
    v3_live = _canonicalize_metric_value(
        diagnostic_worker,
        decimal_places=HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V3,
    )

    assert v2_reviewed == {"brier": 0.23971548231589}
    assert v2_live == {"brier": 0.2397154823159}
    assert v2_reviewed != v2_live
    assert v3_reviewed == v3_live == {"brier": 0.2397154823159}
    assert _canonicalize_metric_value(reviewed) == v3_reviewed
    assert HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES == 13


def test_hollywood2_v1_v2_and_v3_contracts_remain_explicit() -> None:
    assert HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V1 == 15
    assert HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V2 == 14
    assert HOLLYWOOD2_SOURCE_TOKEN_METRIC_DECIMAL_PLACES_V3 == 13
    assert HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V1 == {
        "method": "recursive_round_finite_metric_floats",
        "metric_float_decimal_places": 15,
        "nonfinite_metric_floats_permitted": False,
        "benchmark_model_protocol_numeric_values_rounded": False,
    }
    assert HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V2 == {
        "method": "recursive_round_finite_metric_floats",
        "metric_float_decimal_places": 14,
        "nonfinite_metric_floats_permitted": False,
        "benchmark_model_protocol_numeric_values_rounded": False,
    }
    assert HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3 == {
        "method": "recursive_round_finite_metric_floats",
        "metric_float_decimal_places": 13,
        "nonfinite_metric_floats_permitted": False,
        "benchmark_model_protocol_numeric_values_rounded": False,
    }
    assert (
        HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION
        == HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION_V3
    )


def test_hollywood2_metric_canonicalization_is_metrics_only_contract() -> None:
    value = {
        "integer": 4,
        "token": "001",
        "flag": False,
        "values": (0.12345678901234567,),
    }
    canonical = _canonicalize_metric_value(value)
    assert canonical["integer"] == 4
    assert canonical["token"] == "001"
    assert canonical["flag"] is False
    assert canonical["values"] == [0.1234567890123]


def test_hollywood2_explicit_empty_contract_is_rejected() -> None:
    with pytest.raises(BenchmarkIntegrityError, match="reviewed v1, v2, or v3"):
        _validate_numeric_canonicalization_contract({})


@pytest.mark.parametrize("places", [0, 12, 16, 20])
def test_hollywood2_metric_canonicalization_rejects_unreviewed_precision(
    places: int,
) -> None:
    with pytest.raises(BenchmarkIntegrityError, match="reviewed 13-, 14-, or 15-place"):
        _canonicalize_metric_value({"metric": 0.5}, decimal_places=places)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_hollywood2_metric_canonicalization_rejects_nonfinite_values(value: float) -> None:
    with pytest.raises(BenchmarkIntegrityError, match="non-finite"):
        _canonicalize_metric_value({"metric": value})
