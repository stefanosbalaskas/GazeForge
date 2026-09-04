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


def test_paired_model_differences_are_exposed_from_top_level_api():
    assert gazeforge.PairedModelDifferences.__name__ == "PairedModelDifferences"
    assert callable(gazeforge.paired_model_metric_differences)
    assert "PairedModelDifferences" in gazeforge.__all__
    assert "paired_model_metric_differences" in gazeforge.__all__


def test_source_resolution_governance_is_exposed_from_top_level_api():
    assert gazeforge.SourceResolutionRecord.__name__ == "SourceResolutionRecord"
    assert gazeforge.SourceResolutionDashboard.__name__ == "SourceResolutionDashboard"
    assert gazeforge.SourceResolutionBundleLock.__name__ == "SourceResolutionBundleLock"
    for name in (
        "load_source_resolution_record",
        "validate_source_resolution_record",
        "validate_source_resolution_records",
        "validate_hollywood2_source_resolution_record",
        "validate_gaze_in_wild_source_resolution_record",
        "discover_source_resolution_paths",
        "validate_source_resolution_directory",
        "build_source_resolution_dashboard",
        "render_source_resolution_dashboard_markdown",
        "build_source_resolution_bundle_lock",
        "load_source_resolution_bundle_lock",
        "validate_source_resolution_bundle_lock",
    ):
        assert callable(getattr(gazeforge, name))
        assert name in gazeforge.__all__
    assert "SourceResolutionRecord" in gazeforge.__all__
    assert "SourceResolutionDashboard" in gazeforge.__all__
    assert "SourceResolutionBundleLock" in gazeforge.__all__


def test_hollywood2_source_audit_is_exposed_from_top_level_api():
    assert gazeforge.Hollywood2SourceAuditSpec.__name__ == "Hollywood2SourceAuditSpec"
    assert gazeforge.Hollywood2SourceFileRecord.__name__ == "Hollywood2SourceFileRecord"
    assert callable(gazeforge.audit_hollywood2_source)
    assert callable(gazeforge.load_audited_hollywood2_directory)
    assert callable(gazeforge.load_hollywood2_source_audit_spec)
    assert "Hollywood2SourceAuditRun" in gazeforge.__all__
    assert "audit_hollywood2_source" in gazeforge.__all__


def test_gaze_in_wild_source_audit_is_exposed_from_top_level_api():
    assert gazeforge.GazeInWildSourceAuditSpec.__name__ == "GazeInWildSourceAuditSpec"
    assert gazeforge.GazeInWildLabelFileRecord.__name__ == "GazeInWildLabelFileRecord"
    assert gazeforge.GazeInWildProcessFileRecord.__name__ == "GazeInWildProcessFileRecord"
    assert callable(gazeforge.audit_gaze_in_wild_source)
    assert callable(gazeforge.audited_gaze_in_wild_files_by_labeller)
    assert callable(gazeforge.load_gaze_in_wild_source_audit_spec)
    assert "GazeInWildSourceAuditRun" in gazeforge.__all__
    assert "audit_gaze_in_wild_source" in gazeforge.__all__


def test_gaze_in_wild_labeller_agreement_is_exposed_from_top_level_api():
    assert gazeforge.GazeInWildLabellerAgreementRun.__name__ == (
        "GazeInWildLabellerAgreementRun"
    )
    assert callable(gazeforge.run_gaze_in_wild_labeller_agreement)
    assert "GazeInWildLabellerAgreementRun" in gazeforge.__all__
    assert "run_gaze_in_wild_labeller_agreement" in gazeforge.__all__


def test_gaze_in_wild_model_validation_is_exposed_from_top_level_api():
    assert gazeforge.GazeInWildPreparedBenchmark.__name__ == "GazeInWildPreparedBenchmark"
    assert gazeforge.GazeInWildModelValidationRun.__name__ == "GazeInWildModelValidationRun"
    assert callable(gazeforge.prepare_gaze_in_wild_benchmark)
    assert callable(gazeforge.run_gaze_in_wild_model_validation)
    assert "GazeInWildPreparedBenchmark" in gazeforge.__all__
    assert "GazeInWildModelValidationRun" in gazeforge.__all__
    assert "prepare_gaze_in_wild_benchmark" in gazeforge.__all__
    assert "run_gaze_in_wild_model_validation" in gazeforge.__all__


def test_visus_source_audit_is_exposed_from_top_level_api():
    assert gazeforge.VisusSourceAuditSpec.__name__ == "VisusSourceAuditSpec"
    assert gazeforge.VisusSourceFileRecord.__name__ == "VisusSourceFileRecord"
    assert gazeforge.VisusAuditedFile.__name__ == "VisusAuditedFile"
    assert callable(gazeforge.audit_visus_source)
    assert callable(gazeforge.load_visus_source_audit_spec)
    assert "VisusSourceAuditRun" in gazeforge.__all__
    assert "audit_visus_source" in gazeforge.__all__


def test_visus_canonical_intake_is_exposed_from_top_level_api():
    assert gazeforge.VisusCanonicalAOIIntakeRun.__name__ == "VisusCanonicalAOIIntakeRun"
    assert callable(gazeforge.prepare_visus_canonical_aoi_intake)
    assert "VisusCanonicalAOIIntakeRun" in gazeforge.__all__
    assert "prepare_visus_canonical_aoi_intake" in gazeforge.__all__


def test_visus_prediction_intake_is_exposed_from_top_level_api():
    assert gazeforge.VisusDynamicAOIPredictionIntakeRun.__name__ == (
        "VisusDynamicAOIPredictionIntakeRun"
    )
    assert callable(gazeforge.prepare_visus_dynamic_aoi_predictions)
    assert "VisusDynamicAOIPredictionIntakeRun" in gazeforge.__all__
    assert "prepare_visus_dynamic_aoi_predictions" in gazeforge.__all__


def test_visus_model_validation_is_exposed_from_top_level_api():
    assert gazeforge.VisusDynamicAOIModelValidationRun.__name__ == (
        "VisusDynamicAOIModelValidationRun"
    )
    assert callable(gazeforge.run_visus_dynamic_aoi_model_validation)
    assert "VisusDynamicAOIModelValidationRun" in gazeforge.__all__
    assert "run_visus_dynamic_aoi_model_validation" in gazeforge.__all__


def test_visus_human_agreement_is_exposed_from_top_level_api():
    assert gazeforge.VisusDynamicAOIHumanAgreementRun.__name__ == (
        "VisusDynamicAOIHumanAgreementRun"
    )
    assert callable(gazeforge.run_visus_dynamic_aoi_human_agreement)
    assert "VisusDynamicAOIHumanAgreementRun" in gazeforge.__all__
    assert "run_visus_dynamic_aoi_human_agreement" in gazeforge.__all__


def test_visus_validation_suite_is_exposed_from_top_level_api():
    assert gazeforge.VisusDynamicAOIValidationSuiteRun.__name__ == (
        "VisusDynamicAOIValidationSuiteRun"
    )
    assert callable(gazeforge.run_visus_dynamic_aoi_validation_suite)
    assert callable(gazeforge.validate_visus_dynamic_aoi_suite_manifest)
    assert callable(gazeforge.discover_visus_dynamic_aoi_suite_manifests)
    assert "VisusDynamicAOIValidationSuiteRun" in gazeforge.__all__
    assert "run_visus_dynamic_aoi_validation_suite" in gazeforge.__all__
    assert "validate_visus_dynamic_aoi_suite_manifest" in gazeforge.__all__
    assert "discover_visus_dynamic_aoi_suite_manifests" in gazeforge.__all__
