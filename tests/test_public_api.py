import gazeforge


def test_lund_sensitivity_is_exposed_from_top_level_api():
    assert gazeforge.Lund2013SensitivityRun.__name__ == "Lund2013SensitivityRun"
    assert callable(gazeforge.run_lund2013_sampling_sensitivity)
    assert "Lund2013SensitivityRun" in gazeforge.__all__
    assert "run_lund2013_sampling_sensitivity" in gazeforge.__all__


def test_lund_fetch_is_exposed_from_top_level_api():
    assert gazeforge.Lund2013FetchResult.__name__ == "Lund2013FetchResult"
    assert callable(gazeforge.fetch_lund2013_dataset)
    assert len(gazeforge.LUND2013_COMMIT) == 40
    assert gazeforge.LUND2013_REPOSITORY == "richardandersson/EyeMovementDetectorEvaluation"
    assert "Lund2013FetchResult" in gazeforge.__all__
    assert "fetch_lund2013_dataset" in gazeforge.__all__
