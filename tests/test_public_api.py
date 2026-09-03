import gazeforge


def test_lund_sensitivity_is_exposed_from_top_level_api():
    assert gazeforge.Lund2013SensitivityRun.__name__ == "Lund2013SensitivityRun"
    assert callable(gazeforge.run_lund2013_sampling_sensitivity)
    assert "Lund2013SensitivityRun" in gazeforge.__all__
    assert "run_lund2013_sampling_sensitivity" in gazeforge.__all__


def test_lund_fetch_is_exposed_from_top_level_api():
    assert gazeforge.Lund2013FetchResult.__name__ == "Lund2013FetchResult"
    assert callable(gazeforge.fetch_lund2013_dataset)
    assert callable(gazeforge.validate_lund2013_source_manifest)
    assert len(gazeforge.LUND2013_COMMIT) == 40
    assert gazeforge.LUND2013_REPOSITORY == "richardandersson/EyeMovementDetectorEvaluation"
    assert "Lund2013FetchResult" in gazeforge.__all__
    assert "fetch_lund2013_dataset" in gazeforge.__all__
    assert "validate_lund2013_source_manifest" in gazeforge.__all__


def test_lund_suite_is_exposed_from_top_level_api():
    assert gazeforge.Lund2013BenchmarkSuiteRun.__name__ == "Lund2013BenchmarkSuiteRun"
    assert callable(gazeforge.run_lund2013_benchmark_suite)
    assert callable(gazeforge.validate_lund2013_suite_manifest)
    assert callable(gazeforge.discover_lund2013_suite_manifests)
    assert "Lund2013BenchmarkSuiteRun" in gazeforge.__all__
    assert "run_lund2013_benchmark_suite" in gazeforge.__all__
    assert "validate_lund2013_suite_manifest" in gazeforge.__all__
    assert "discover_lund2013_suite_manifests" in gazeforge.__all__


def test_stratified_event_metrics_are_exposed_from_top_level_api():
    assert gazeforge.StratifiedEventPerformance.__name__ == "StratifiedEventPerformance"
    assert callable(gazeforge.summarize_event_predictions_by_stratum)
    assert "StratifiedEventPerformance" in gazeforge.__all__
    assert "summarize_event_predictions_by_stratum" in gazeforge.__all__
