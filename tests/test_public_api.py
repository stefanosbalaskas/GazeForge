import gazeforge


def test_lund_sensitivity_is_exposed_from_top_level_api():
    assert gazeforge.Lund2013SensitivityRun.__name__ == "Lund2013SensitivityRun"
    assert callable(gazeforge.run_lund2013_sampling_sensitivity)
    assert "Lund2013SensitivityRun" in gazeforge.__all__
    assert "run_lund2013_sampling_sensitivity" in gazeforge.__all__
