import json
from pathlib import Path

from gazeforge.dashboard import load_frozen_benchmark_report
from gazeforge.hollywood2_token_evidence import (
    HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION,
)

FROZEN = Path(
    "validation/evidence/hollywood2/"
    "hollywood2-source-token-60hz-frozen-summary-v1.json"
)
EXPECTED_FROZEN_FINGERPRINT = (
    "e1f1c030f843e118ebd65520dfab8e872efb4ea3e1d520299a993b0ca00ddabf"
)
EXPECTED_SOURCE_REPORT_FINGERPRINT = (
    "a7a6219d6ffcb1fc6622110887a95f2c9d0646fea6e22d0ada941fe07b90586a"
)
EXPECTED_SOURCE_REPORT_FILE_SHA256 = (
    "a5e22948105321dc97dcffc66926c32a6c93c797722b879e38fd3c6860dde34e"
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
    assert (
        protocol["source_validation_numeric_canonicalization"]
        == HOLLYWOOD2_SOURCE_TOKEN_NUMERIC_CANONICALIZATION
    )


def test_frozen_hollywood2_source_token_summary_binds_reviewed_execution_lineage() -> None:
    report = _report()
    execution = report["protocol"]["reviewed_execution_evidence"]
    assert execution["canonicalized_reports_byte_identical"] is True

    pre_merge = execution["pre_merge"]
    assert pre_merge["workflow_run_id"] == 33_955_703_630
    assert pre_merge["head_sha"] == "5180d4e38a2f5929161b7baee6af18c5e9b43c4d"
    assert pre_merge["artifact_id"] == 9_966_618_539
    assert (
        pre_merge["artifact_zip_sha256"]
        == "a03b31f0a10f449aaa4212346f768be11797255eea9f9bc897b3baf8f575a8ae"
    )
    assert (
        pre_merge["uncanonicalized_report_fingerprint_sha256"]
        == "6d6b7a0c677e278d3503ca5f6c4745430a037ea6b42a3000b93052fa7f2f0cab"
    )

    exact_merge = execution["exact_merge"]
    assert exact_merge["workflow_run_id"] == 33_956_874_927
    assert exact_merge["head_sha"] == "e0e47c47e0a2e42a4520bd14a126b23fc3b05644"
    assert exact_merge["artifact_id"] == 9_966_993_646
    assert (
        exact_merge["artifact_zip_sha256"]
        == "3780e8d7a761e45e917e0229a02eeca332e9200473ef9a7489b1c41c5019a985"
    )
    assert (
        exact_merge["uncanonicalized_report_fingerprint_sha256"]
        == "d0ac2b9fd6e7f888abcba59f558b2424237ba86b789b14be53aa3a9414731bed"
    )


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

    assert summary["I-VT"]["accuracy_mean"] == 0.701489749639424
    assert summary["I-VT"]["macro_f1_mean"] == 0.560463661068529
    assert summary["I-VT"]["event_f1_mean"] == 0.628563102252939
    assert summary["I-VT"]["event_mean_matched_iou_mean"] == 0.854708503929063

    assert summary["RandomForest"]["accuracy_mean"] == 0.753386503275985
    assert summary["RandomForest"]["macro_f1_mean"] == 0.740379565790729
    assert summary["RandomForest"]["event_f1_mean"] == 0.43974268718423
    assert summary["RandomForest"]["multiclass_brier_score_mean"] == 0.342259141298091
    assert summary["RandomForest"]["expected_calibration_error_mean"] == 0.023200598137728

    assert summary["ContextMLP"]["accuracy_mean"] == 0.817326596815109
    assert summary["ContextMLP"]["macro_f1_mean"] == 0.811936602726464
    assert summary["ContextMLP"]["event_f1_mean"] == 0.602272817237293
    assert summary["ContextMLP"]["event_mean_matched_iou_mean"] == 0.883084755642208
    assert summary["ContextMLP"]["multiclass_brier_score_mean"] == 0.263223085435483
    assert summary["ContextMLP"]["expected_calibration_error_mean"] == 0.014264058544022


def test_frozen_hollywood2_summary_contains_no_source_paths_or_participant_promotion() -> None:
    payload = json.loads(FROZEN.read_text(encoding="utf-8"))
    text = json.dumps(payload, sort_keys=True)
    assert ".arff" not in text
    assert "_hollywood2_em" not in text
    assert "participant-held-out estimates" in payload["protocol"]["claim_limit"]
