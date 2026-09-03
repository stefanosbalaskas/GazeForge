from gazeforge.evidence_details import render_validated_report_detail_markdown


def _base_report(metrics):
    return {
        "benchmark": {
            "name": "Lund2013",
            "sampling_origin": "resampled",
            "reference_strength": "derived-human-reference",
        },
        "metrics": metrics,
        "report_fingerprint_sha256": "a" * 64,
    }


def test_model_report_details_render_overall_paired_and_stimulus_tables():
    report = _base_report(
        {
            "summary": [
                {
                    "model": "RandomForest",
                    "n_folds": 5,
                    "accuracy_mean": 0.8,
                    "balanced_accuracy_mean": 0.76,
                    "macro_f1_mean": 0.74,
                    "event_f1_mean": 0.65,
                    "event_mean_matched_iou_mean": 0.7,
                    "multiclass_brier_score_mean": 0.25,
                    "expected_calibration_error_mean": 0.08,
                }
            ],
            "paired_model_difference_summary": [
                {
                    "model_a": "RandomForest",
                    "model_b": "ContextMLP",
                    "metric": "macro_f1",
                    "n_paired_folds": 5,
                    "mean_delta_a_minus_b": 0.02,
                    "mean_improvement_for_a": 0.02,
                    "wins_model_a": 3,
                    "ties": 1,
                    "wins_model_b": 1,
                }
            ],
            "stimulus_type_summary": [
                {
                    "stratum": "video",
                    "model": "RandomForest",
                    "n_folds": 5,
                    "n_test_rows_total": 120,
                    "n_test_groups_unique": 8,
                    "accuracy_mean": 0.78,
                    "macro_f1_mean": 0.71,
                    "event_f1_mean": 0.62,
                    "event_mean_matched_iou_mean": 0.68,
                }
            ],
        }
    )

    markdown = render_validated_report_detail_markdown(report)

    assert "Overall held-out model performance" in markdown
    assert "Matched-fold model differences" in markdown
    assert "Performance by stimulus family" in markdown
    assert "RandomForest" in markdown
    assert "video" in markdown
    assert "not cross-validation significance tests" in markdown
    assert "`aaaaaaaaaaaa`" in markdown


def test_human_agreement_details_render_overall_and_stimulus_rows():
    report = _base_report(
        {
            "overall": {
                "n_aligned_samples": 1000,
                "exact_agreement": 0.82,
                "cohen_kappa": 0.74,
            },
            "by_stimulus_type": {
                "image": {
                    "n_aligned_samples": 400,
                    "exact_agreement": 0.85,
                    "cohen_kappa": 0.78,
                }
            },
        }
    )

    markdown = render_validated_report_detail_markdown(report)

    assert "Human–human annotation agreement" in markdown
    assert "Aligned samples" in markdown
    assert "image" in markdown
    assert "0.820" in markdown


def test_sensitivity_details_render_settings_and_model_surface():
    report = _base_report(
        {
            "settings": [
                {
                    "target_sampling_rate_hz": 60.0,
                    "min_label_purity": 0.75,
                    "comparison_status": "ok",
                    "ambiguous_fraction": 0.05,
                    "retained_fraction_of_target": 0.94,
                    "retained_group_count": 12,
                }
            ],
            "model_metrics": [
                {
                    "target_sampling_rate_hz": 60.0,
                    "min_label_purity": 0.75,
                    "model": "ContextMLP",
                    "macro_f1_mean": 0.73,
                    "event_f1_mean": 0.64,
                    "event_mean_matched_iou_mean": 0.69,
                    "ambiguous_fraction": 0.05,
                    "retained_fraction_of_target": 0.94,
                }
            ],
        }
    )

    markdown = render_validated_report_detail_markdown(report)

    assert "Sampling × label-purity settings" in markdown
    assert "Model sensitivity surface" in markdown
    assert "ContextMLP" in markdown
    assert "60.000" in markdown


def test_unknown_validated_schema_falls_back_without_guessing_metrics():
    report = _base_report({"future_metric_bundle": {"opaque": 0.91}})

    markdown = render_validated_report_detail_markdown(report)

    assert "no specialised public detail renderer yet" in markdown
    assert "0.91" not in markdown
