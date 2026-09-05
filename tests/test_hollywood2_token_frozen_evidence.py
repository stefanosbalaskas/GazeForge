import json
from pathlib import Path

from gazeforge.dashboard import load_frozen_benchmark_report

FROZEN = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-60hz-frozen-summary-v1.json"
)
EXPECTED_FROZEN_FINGERPRINT = (
    "c6aa390995b480f368b24601498ba1c0b666a3fa938f8dc095e36ead6129414e"
)
EXPECTED_SOURCE_REPORT_FINGERPRINT = (
    "6d6b7a0c677e278d3503ca5f6c4745430a037ea6b42a3000b93052fa7f2f0cab"
)
EXPECTED_SOURCE_REPORT_FILE_SHA256 = (
    "0d3e0ad01d47e6f953fc233c2a1c1a491d3a418dd685b96919ccdda0b96aaa63"
)
EXPECTED_TOKENS = (
    "001",
    "002",
    "003",
    "004",
    "005",
    "006",
    "008",
    "010",
    "011",
    "012",
    "013",
    "014",
    "015",
    "017",
    "018",
    "019",
)


def _report() -> dict:
    return load_frozen_benchmark_report(FROZEN)


def test_committed_hollywood2_source_token_summary_is_immutable() -> None:
    report = _report()
    assert report["report_fingerprint_sha256"] == EXPECTED_FROZEN_FINGERPRINT
    protocol = report["protocol"]
    assert (
        protocol["source_validation_report_fingerprint_sha256"]
        == EXPECTED_SOURCE_REPORT_FINGERPRINT
    )
    assert protocol["source_validation_report_file_sha256"] == EXPECTED_SOURCE_REPORT_FILE_SHA256


def test_frozen_hollywood2_source_token_summary_preserves_claim_boundary() -> None:
    report = _report()
    benchmark = report["benchmark"]
    protocol = report["protocol"]
    boundary = protocol["scientific_boundary"]
    preparation = protocol["preparation"]

    assert benchmark["name"] == "Hollywood2EM"
    assert benchmark["split_unit"] == "canonical_file_subject_token"
    assert benchmark["participant_count"] is None
    assert benchmark["sampling_origin"] == "resampled"
    assert benchmark["sampling_rates_hz"] == [500.0, 60.0]
    assert protocol["scope"] == "hollywood2-source-token-held-out-frozen-summary-v1"
    assert boundary["frozen_source_token_summary_created"] is True
    assert boundary["source_validation_report_fingerprint_bound"] is True
    assert boundary["aggregate_metrics_only"] is True
    assert boundary["operator_authorized_nonredistributive_analysis"] is True

    for key in (
        "participant_disjoint_validation_created",
        "participant_generalization_claim",
        "participant_identity_mapping_verified",
        "source_token_to_participant_mapping_verified",
        "cross_dataset_validation_created",
        "exact_license_identifier_verified",
        "exact_license_text_verified",
        "dataset_specific_analysis_terms_verified",
        "raw_predictions_embedded",
        "raw_source_redistributed_by_gazeforge",
        "full_validation_report_committed",
    ):
        assert boundary[key] is False

    assert preparation["participant_identity_resolved"] is False
    assert preparation["raw_source_rows_embedded"] is False
    assert preparation["source_filenames_embedded"] is False
    assert tuple(preparation["source_tokens"]) == EXPECTED_TOKENS
    assert preparation["source_token_count"] == 16
    assert preparation["ground_truth_file_count"] == 697
    assert preparation["ground_truth_sample_count"] == 3_871_580
    assert preparation["analysis_sampling_rate_hz"] == 60.0
    assert preparation["min_label_purity"] == 0.75
    assert preparation["prepared_rows_before_exclusions"] == 465_013
    assert preparation["analysis_rows"] == 450_649
    assert preparation["excluded_rows"] == 14_364


def test_frozen_hollywood2_source_token_fold_assignment_is_disjoint() -> None:
    report = _report()
    assignment = report["metrics"]["source_token_fold_assignment"]
    observed_tokens = [str(row["source_token"]) for row in assignment]
    observed_folds = [int(row["validation_fold"]) for row in assignment]
    assert len(observed_tokens) == 16
    assert len(set(observed_tokens)) == 16
    assert set(observed_tokens) == set(EXPECTED_TOKENS)
    assert set(observed_folds) == {1, 2, 3, 4}
    assert all(observed_folds.count(fold) == 4 for fold in (1, 2, 3, 4))


def test_frozen_hollywood2_source_token_headline_metrics_are_exact() -> None:
    report = _report()
    summary = {row["model"]: row for row in report["metrics"]["summary"]}
    assert set(summary) == {"I-VT", "RandomForest", "ContextMLP"}

    assert summary["I-VT"]["accuracy_mean"] == 0.7014897496394245
    assert summary["I-VT"]["macro_f1_mean"] == 0.560463661068529
    assert summary["I-VT"]["event_f1_mean"] == 0.6285631022529388
    assert summary["I-VT"]["event_mean_matched_iou_mean"] == 0.8547085039290625

    assert summary["RandomForest"]["accuracy_mean"] == 0.7533865032759848
    assert summary["RandomForest"]["macro_f1_mean"] == 0.7403795657907287
    assert summary["RandomForest"]["event_f1_mean"] == 0.43974268718423026
    assert summary["RandomForest"]["multiclass_brier_score_mean"] == 0.3422591412980906

    assert summary["ContextMLP"]["accuracy_mean"] == 0.8173265968151094
    assert summary["ContextMLP"]["macro_f1_mean"] == 0.8119366027264643
    assert summary["ContextMLP"]["event_f1_mean"] == 0.6022728172372932
    assert summary["ContextMLP"]["event_mean_matched_iou_mean"] == 0.883084755642208
    assert summary["ContextMLP"]["multiclass_brier_score_mean"] == 0.26322308543548284
    assert summary["ContextMLP"]["expected_calibration_error_mean"] == 0.014264058544022032


def test_frozen_hollywood2_summary_contains_no_source_paths_or_participant_promotion() -> None:
    payload = json.loads(FROZEN.read_text(encoding="utf-8"))
    text = json.dumps(payload, sort_keys=True)
    assert ".arff" not in text
    assert "_hollywood2_em" not in text
    assert "participant-held-out estimates" in payload["protocol"]["claim_limit"]
