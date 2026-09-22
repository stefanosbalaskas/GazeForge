from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gazeforge.gaze_in_wild_explicit_task_mapping_certificate as giw_cert
import gazeforge.hollywood2_gin_accessible_host_evidence as h2_access
import gazeforge.hollywood2_original_subject_metadata as h2_probe
import gazeforge.hollywood2_original_subject_metadata_evidence as h2_original
import gazeforge.location_scale_bootstrap_monte_carlo as boot_mc
import gazeforge.location_scale_hierarchical_bootstrap as hier
import gazeforge.source_candidate_cli as source_cli
import gazeforge.stratified as stratified
import gazeforge.synthetic_benchmark as synthetic
import gazeforge.visualization as visualization
import gazeforge.visus_osnabrueck_derivative_recovery as visus_derivative
from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

H2_ACCESS_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-gin-host-metadata-accessible-evidence-v1.json"
)

H2_ORIGINAL_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-original-subject-metadata-evidence-v1.json"
)

VISUS_DERIVATIVE_EVIDENCE = Path(
    "validation/evidence/visus-source-recheck/visus-osnabrueck-derivative-recovery-evidence-v1.json"
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ======================================================================
# Hollywood2 accessible-host: close final 98% residual
# ======================================================================


def _accessible_live_probe() -> dict:
    probe = {
        "record_type": h2_access.LIVE_RECORD_TYPE,
        "status": h2_access.LIVE_STATUS,
        "repository": h2_access.REPOSITORY_SLUG,
        "api": {
            "http_status": 200,
            "json_object": True,
            "full_name": h2_access.REPOSITORY_SLUG,
            "license_key_paths": [],
        },
        "page": {
            "http_status": 200,
            "contains_license_word": False,
            "contains_licence_word": False,
        },
        "datacite_queries": [
            {
                "http_status": 200,
                "json_object": True,
                "exact_repository_match_count": 0,
            }
            for _ in range(4)
        ],
        "rights_interpretation": {
            "host_api_metadata_accessible": True,
            "host_api_exposes_license_key": False,
            "host_api_exposes_nonempty_license_value": False,
            "exact_license_identifier_verified": False,
            "analysis_use_authorized": False,
            "raw_data_redistribution_authorized": False,
            "license_inference_from_page_keyword_permitted": False,
            "registry_zero_match_is_global_absence_claim": False,
            "datacite_exact_repository_match_count": 0,
        },
        "scientific_boundary": {
            "participant_identity_mapping_verified": False,
            "source_audit_ready": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_validation_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
    }
    probe["probe_fingerprint_sha256"] = h2_access.probe_fingerprint(probe)
    return probe


def test_accessible_live_probe_requires_four_datacite_rows():
    probe = _accessible_live_probe()
    probe["datacite_queries"] = []
    probe["probe_fingerprint_sha256"] = h2_access.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fresh DataCite ledger drifted",
    ):
        h2_access.validate_hollywood2_gin_accessible_host_live_probe(
            probe,
            H2_ACCESS_EVIDENCE,
        )


def test_accessible_live_probe_requires_mapping_datacite_rows():
    probe = _accessible_live_probe()
    probe["datacite_queries"][0] = "invalid-row"
    probe["probe_fingerprint_sha256"] = h2_access.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fresh DataCite row is invalid",
    ):
        h2_access.validate_hollywood2_gin_accessible_host_live_probe(
            probe,
            H2_ACCESS_EVIDENCE,
        )


# ======================================================================
# Hollywood2 original-subject: close final 99% residual
# ======================================================================


_DESCRIPTION = b"""
<html><body>
<p>We have collected data from 16 human volunteers.</p>
<p>We split them into an active group and a free-viewing group.</p>
<p>There were 12 active subjects and 4 free viewing subjects.</p>
<p>The active group had to solve an action recognition task.</p>
<p>The free-viewing group was not required to solve any specific task.</p>
<p>Sampling frequency 500Hz.</p>
<a href="http://vision.imar.ro/eyetracking/getdata.php?filepath=data&amp;filename=gaze_hollywood2.zip">
Hollywood-2 gaze data</a>
</body></html>
"""

_LICENSE = b"""
<html><body>
GRANT OF LICENCE FREE OF CHARGE FOR ACADEMIC USE ONLY.
Provided you send the request from an academic address,
you are granted a limited, non-exclusive, non-assignable
and non-transferable license. You may not sub-license
or transfer the dataset. It is your responsibility to seek
prior written permission.
</body></html>
"""


def _fetch(body: bytes, url: str) -> dict:
    return {
        "requested_url": url,
        "final_url": url,
        "http_status": 200,
        "content_type": "text/html; charset=utf-8",
        "content_length": str(len(body)),
        "content_disposition": None,
        "body": body,
    }


def _original_live_probe() -> dict:
    return h2_probe.build_probe_record(
        _fetch(
            _DESCRIPTION,
            h2_original.DESCRIPTION_URL,
        ),
        _fetch(
            _LICENSE,
            h2_original.LICENSE_URL,
        ),
        data_link_head={
            "requested_url": h2_original.ADVERTISED_ARCHIVE_URL,
            "final_url": h2_original.LOGIN_URL,
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "content_length": "2889",
            "content_disposition": None,
        },
    )


def test_original_subject_detects_new_public_readme_ledger_surface():
    probe = _original_live_probe()

    # Deliberately simulate a new ledger link while preserving the previously
    # reviewed marker state, exercising the independent list-level guard.
    probe["description"]["public_readme_links"] = [
        {
            "href": "README.txt",
            "resolved_url": ("https://vision.imar.ro/eyetracking/README.txt"),
            "text": "README",
        }
    ]
    probe["probe_fingerprint_sha256"] = h2_probe.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="public README/ledger surface appeared",
    ):
        h2_original.validate_hollywood2_original_subject_live_probe(
            probe,
            H2_ORIGINAL_EVIDENCE,
        )


# ======================================================================
# GIW explicit task-mapping certificate remaining branches
# ======================================================================


def _valid_task_certificate() -> dict:
    value = {
        "record_type": giw_cert.CERTIFICATE_RECORD_TYPE,
        "status": giw_cert.CERTIFICATE_STATUS,
        "authoritative_task_mapping_exhaustion_fingerprint_sha256": (
            giw_cert.TASK_MAPPING_EXHAUSTION_FINGERPRINT
        ),
        "candidate_fingerprint_sha256": "a" * 64,
        "review_fingerprint_sha256": "b" * 64,
        "mapping_fingerprint_sha256": "c" * 64,
        "trial_index_count": len(giw_cert.TRIAL_INDICES),
        "trial_indices": list(giw_cert.TRIAL_INDICES),
        "publication_task_count": len(giw_cert.EXPECTED_TASKS),
        "publication_tasks": list(giw_cert.EXPECTED_TASKS),
        "mapping_boundary": dict(giw_cert._EXPECTED_MAPPING_BOUNDARY),
        "scientific_boundary": dict(giw_cert._EXPECTED_SCIENTIFIC_BOUNDARY),
        "certificate_fingerprint_sha256": "d" * 64,
    }
    value["certificate_fingerprint_sha256"] = giw_cert.certificate_fingerprint(value)
    return value


@pytest.mark.parametrize(
    ("field", "replacement", "match"),
    [
        (
            "record_type",
            "wrong",
            "certificate type drifted",
        ),
        (
            "status",
            "wrong",
            "certificate status drifted",
        ),
        (
            "trial_indices",
            [999],
            "canonical TrIdx ledger drifted",
        ),
        (
            "publication_task_count",
            -1,
            "publication-task count drifted",
        ),
        (
            "publication_tasks",
            ["wrong"],
            "publication task ledger drifted",
        ),
    ],
)
def test_task_mapping_certificate_rejects_semantic_drift(
    field,
    replacement,
    match,
):
    value = _valid_task_certificate()
    value[field] = replacement

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        giw_cert.validate_certificate_record(value)


def test_task_mapping_certificate_rejects_self_fingerprint_drift():
    value = _valid_task_certificate()
    value["certificate_fingerprint_sha256"] = "f" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="certificate fingerprint drifted",
    ):
        giw_cert.validate_certificate_record(value)


# ======================================================================
# source_candidate_cli residual helpers
# ======================================================================


def test_source_candidate_json_loader_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        source_cli._load_json_object(
            tmp_path / "missing.json",
            label="demo",
        )


def test_source_candidate_json_loader_rejects_invalid_utf8(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_bytes(b"\xff")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        source_cli._load_json_object(
            path,
            label="demo",
        )


def test_source_candidate_json_loader_rejects_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="valid UTF-8 JSON",
    ):
        source_cli._load_json_object(
            path,
            label="demo",
        )


def test_source_candidate_json_loader_rejects_nonobject(tmp_path):
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        source_cli._load_json_object(
            path,
            label="demo",
        )


def test_source_candidate_giw_template_type_guard(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        source_cli,
        "load_gaze_in_wild_source_audit_spec",
        lambda path: object(),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires a GazeInWildSourceAuditSpec",
    ):
        source_cli._require_giw_template(tmp_path / "template.json")


def test_source_candidate_cli_module_entrypoint(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["gazeforge-source-candidate"],
    )

    with pytest.raises(SystemExit):
        runpy.run_module(
            "gazeforge.source_candidate_cli",
            run_name="__main__",
        )


# ======================================================================
# stratified.py cheap residual closure
# ======================================================================


def _stratified_row() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "event_label": ["fixation"],
            "predicted_event": ["fixation"],
            "comparison_model": ["demo"],
            "validation_fold": [1],
            "stimulus_type": ["image"],
        }
    )


def test_stratified_calibration_rejects_partial_probabilities():
    frame = pd.DataFrame(
        {
            "p_event_fixation": [0.8, np.nan],
            "p_event_saccade": [0.2, 0.8],
        }
    )

    with pytest.raises(
        SchemaError,
        match="partially missing probability",
    ):
        stratified._calibration_input(frame)


def test_stratified_requires_columns():
    frame = _stratified_row().drop(columns=["predicted_event"])

    with pytest.raises(
        SchemaError,
        match="require columns",
    ):
        stratified.summarize_event_predictions_by_stratum(
            frame,
            stratify_col="stimulus_type",
            sampling_rate_hz=60.0,
            include_event_level_metrics=False,
        )


def test_stratified_rejects_empty_predictions():
    frame = _stratified_row().iloc[0:0]

    with pytest.raises(
        ValueError,
        match="at least one row",
    ):
        stratified.summarize_event_predictions_by_stratum(
            frame,
            stratify_col="stimulus_type",
            sampling_rate_hz=60.0,
            include_event_level_metrics=False,
        )


def test_stratified_rejects_missing_identity():
    frame = _stratified_row()
    frame.loc[0, "comparison_model"] = None

    with pytest.raises(
        SchemaError,
        match="cannot contain missing",
    ):
        stratified.summarize_event_predictions_by_stratum(
            frame,
            stratify_col="stimulus_type",
            sampling_rate_hz=60.0,
            include_event_level_metrics=False,
        )


def test_stratified_rejects_bad_calibration_bins():
    with pytest.raises(
        ValueError,
        match="calibration_bins",
    ):
        stratified.summarize_event_predictions_by_stratum(
            _stratified_row(),
            stratify_col="stimulus_type",
            sampling_rate_hz=60.0,
            calibration_bins=1,
            include_event_level_metrics=False,
        )


def test_stratified_rejects_bad_event_iou():
    with pytest.raises(
        ValueError,
        match="event_min_iou",
    ):
        stratified.summarize_event_predictions_by_stratum(
            _stratified_row(),
            stratify_col="stimulus_type",
            sampling_rate_hz=60.0,
            event_min_iou=2.0,
            include_event_level_metrics=False,
        )


def test_stratified_rejects_bad_sampling_rate():
    with pytest.raises(
        ValueError,
        match="sampling_rate_hz",
    ):
        stratified.summarize_event_predictions_by_stratum(
            _stratified_row(),
            stratify_col="stimulus_type",
            sampling_rate_hz=0.0,
            include_event_level_metrics=False,
        )


# ======================================================================
# synthetic_benchmark.py
# ======================================================================


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"n_trials": 0}, "n_trials"),
        ({"samples_per_trial": 1}, "samples_per_trial"),
        (
            {"fixation_duration_samples": 0},
            "fixation_duration_samples",
        ),
        (
            {"saccade_duration_samples": 0},
            "saccade_duration_samples",
        ),
        (
            {"calibration_bias_px": (1.0,)},
            "calibration_bias_px",
        ),
        (
            {"calibration_bias_px": (np.nan, 0.0)},
            "calibration_bias_px",
        ),
    ],
)
def test_synthetic_spec_remaining_invalid_contracts(
    kwargs,
    match,
):
    with pytest.raises(ValueError, match=match):
        synthetic.SyntheticGazeSpec(**kwargs)


def _small_synthetic_run():
    spec = synthetic.SyntheticGazeSpec(
        n_participants=2,
        n_trials=1,
        samples_per_trial=30,
        fixation_duration_samples=8,
        saccade_duration_samples=2,
        dropout_probability=0.0,
        random_state=20260923,
    )
    return synthetic.simulate_known_truth_gaze(spec)


def _perfect_estimates(run):
    return run.truth.rename(
        columns={
            "x_true_px": "x_px",
            "y_true_px": "y_px",
            "event_label": "predicted_event",
        }
    )[
        [
            "participant_id",
            "trial_id",
            "sample_index",
            "x_px",
            "y_px",
            "predicted_event",
        ]
    ]


def _synthetic_certificate():
    run = _small_synthetic_run()
    estimates = _perfect_estimates(run)
    certificate = synthetic.build_synthetic_recovery_certificate(
        run,
        estimates,
        estimator_name="coverage-estimator",
        event_col="predicted_event",
        thresholds={"coordinate_rmse_px": 1.0},
    )
    return run, estimates, certificate


def _resign_synthetic(certificate):
    body = {
        key: value for key, value in certificate.items() if key != "certificate_fingerprint_sha256"
    }
    certificate["certificate_fingerprint_sha256"] = benchmark_fingerprint(body)
    return certificate


def test_synthetic_estimate_keys_require_all_identity_columns():
    run = _small_synthetic_run()
    estimates = _perfect_estimates(run).drop(columns=["sample_index"])

    with pytest.raises(
        ValueError,
        match="missing key columns",
    ):
        synthetic._validate_estimate_keys(
            run,
            estimates,
        )


def test_synthetic_score_requires_x_coordinate_column():
    run = _small_synthetic_run()
    estimates = _perfect_estimates(run).drop(columns=["x_px"])

    with pytest.raises(
        ValueError,
        match="missing coordinate column",
    ):
        synthetic.score_synthetic_gaze_recovery(
            run,
            estimates,
        )


def test_synthetic_score_requires_requested_event_column():
    run = _small_synthetic_run()
    estimates = _perfect_estimates(run)

    with pytest.raises(
        ValueError,
        match="missing event column",
    ):
        synthetic.score_synthetic_gaze_recovery(
            run,
            estimates,
            event_col="not_present",
        )


def test_synthetic_certificate_requires_estimator_name():
    run = _small_synthetic_run()

    with pytest.raises(
        ValueError,
        match="estimator_name",
    ):
        synthetic.build_synthetic_recovery_certificate(
            run,
            _perfect_estimates(run),
            estimator_name="",
        )


def test_synthetic_certificate_estimates_require_run():
    _, estimates, certificate = _synthetic_certificate()

    with pytest.raises(
        ValueError,
        match="estimates require",
    ):
        synthetic.validate_synthetic_recovery_certificate(
            certificate,
            estimates=estimates,
        )


def test_synthetic_certificate_rejects_schema():
    _, _, certificate = _synthetic_certificate()
    certificate["schema"] = "wrong"

    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        synthetic.validate_synthetic_recovery_certificate(certificate)


def test_synthetic_certificate_rejects_malformed_fingerprint():
    _, _, certificate = _synthetic_certificate()
    certificate["certificate_fingerprint_sha256"] = None

    with pytest.raises(
        ValueError,
        match="missing or malformed",
    ):
        synthetic.validate_synthetic_recovery_certificate(certificate)


def test_synthetic_certificate_rejects_fingerprint_mismatch():
    _, _, certificate = _synthetic_certificate()
    certificate["seed"] += 1

    with pytest.raises(
        ValueError,
        match="fingerprint mismatch",
    ):
        synthetic.validate_synthetic_recovery_certificate(certificate)


def test_synthetic_certificate_rejects_dataset_card_semantics():
    _, _, certificate = _synthetic_certificate()
    certificate["dataset_card"]["annotation_origin"] = "human-manual"
    _resign_synthetic(certificate)

    with pytest.raises(
        ValueError,
        match="dataset-card semantics",
    ):
        synthetic.validate_synthetic_recovery_certificate(certificate)


def test_synthetic_certificate_rejects_threshold_check_drift():
    _, _, certificate = _synthetic_certificate()
    certificate["threshold_checks"] = {"coordinate_rmse_px": False}
    _resign_synthetic(certificate)

    with pytest.raises(
        ValueError,
        match="threshold checks",
    ):
        synthetic.validate_synthetic_recovery_certificate(certificate)


def test_synthetic_certificate_rejects_threshold_status_drift():
    _, _, certificate = _synthetic_certificate()
    certificate["thresholds_passed"] = False
    _resign_synthetic(certificate)

    with pytest.raises(
        ValueError,
        match="threshold status",
    ):
        synthetic.validate_synthetic_recovery_certificate(certificate)


def test_synthetic_certificate_requires_estimator_metadata_for_replay():
    run, estimates, certificate = _synthetic_certificate()
    certificate["estimator"] = None
    _resign_synthetic(certificate)

    with pytest.raises(
        ValueError,
        match="missing estimator metadata",
    ):
        synthetic.validate_synthetic_recovery_certificate(
            certificate,
            run=run,
            estimates=estimates,
        )


def test_synthetic_certificate_replay_detects_extra_signed_content():
    run, estimates, certificate = _synthetic_certificate()
    certificate["coverage_only_extra"] = True
    _resign_synthetic(certificate)

    with pytest.raises(
        ValueError,
        match="does not replay",
    ):
        synthetic.validate_synthetic_recovery_certificate(
            certificate,
            run=run,
            estimates=estimates,
        )


# ======================================================================
# VISUS Osnabrueck derivative recovery
# ======================================================================


def test_visus_derivative_loader_missing_file(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        visus_derivative._load(tmp_path / "missing.json")


def test_visus_derivative_loader_rejects_nonobject(tmp_path):
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="one JSON object",
    ):
        visus_derivative._load(path)


def test_visus_derivative_mapping_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        visus_derivative._mapping(
            {},
            "missing",
        )


def test_visus_derivative_probe_bindings_require_list():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe bindings must be a list",
    ):
        visus_derivative._validate_probe_bindings({"probe_bindings": None})


def test_visus_derivative_probe_binding_rows_require_objects():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="probe binding must be an object",
    ):
        visus_derivative._validate_probe_bindings({"probe_bindings": ["invalid"]})


def test_visus_derivative_requires_eleven_scenarios():
    record = _json(VISUS_DERIVATIVE_EVIDENCE)
    record["structural_recovery"]["scenario_structures"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="eleven scenario structures",
    ):
        visus_derivative._validate_structural_recovery(record)


def test_visus_derivative_scenario_rows_require_objects():
    record = _json(VISUS_DERIVATIVE_EVIDENCE)
    record["structural_recovery"]["scenario_structures"][0] = "invalid"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="scenario structure must be an object",
    ):
        visus_derivative._validate_structural_recovery(record)


def test_visus_derivative_requires_five_resolution_requirements():
    record = _json(VISUS_DERIVATIVE_EVIDENCE)
    record["remaining_resolution_requirements"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="five remaining resolution requirements",
    ):
        visus_derivative.validate_visus_osnabrueck_derivative_recovery(record)


def test_visus_derivative_resolution_requirements_nonempty():
    record = _json(VISUS_DERIVATIVE_EVIDENCE)
    record["remaining_resolution_requirements"][0] = ""

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requirements must be non-empty",
    ):
        visus_derivative.validate_visus_osnabrueck_derivative_recovery(record)


def test_visus_derivative_requires_eight_claim_limits():
    record = _json(VISUS_DERIVATIVE_EVIDENCE)
    record["claim_limits"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="eight claim limits",
    ):
        visus_derivative.validate_visus_osnabrueck_derivative_recovery(record)


def test_visus_derivative_claim_limits_nonempty():
    record = _json(VISUS_DERIVATIVE_EVIDENCE)
    record["claim_limits"][0] = ""

    with pytest.raises(
        BenchmarkIntegrityError,
        match="claim limits must be non-empty",
    ):
        visus_derivative.validate_visus_osnabrueck_derivative_recovery(record)


# ======================================================================
# visualization.py branch closure
# ======================================================================


def test_qc_plot_without_optional_flags_or_title():
    frame = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 10.0],
            "qc_anomaly_score": [0.1, 0.2],
        }
    )

    axis = visualization.plot_qc_timeline(
        frame,
        title=None,
    )

    assert axis is not None


def test_qc_plot_with_flag_column_but_no_flagged_samples():
    frame = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 10.0],
            "qc_anomaly_score": [0.1, 0.2],
            "qc_flag": [False, False],
        }
    )

    axis = visualization.plot_qc_timeline(
        frame,
        title=None,
    )

    assert axis is not None


def test_probability_plot_without_threshold_or_title():
    frame = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 10.0],
            "p_event_": [0.5, 0.5],
        }
    )

    axis = visualization.plot_event_probabilities(
        frame,
        confidence_threshold=None,
        title=None,
    )

    assert axis is not None


def test_calibration_plot_without_title():
    frame = pd.DataFrame(
        {
            "event_label": [
                "fixation",
                "saccade",
            ],
            "p_event_fixation": [
                0.8,
                0.2,
            ],
            "p_event_saccade": [
                0.2,
                0.8,
            ],
        }
    )

    axis = visualization.plot_event_calibration(
        frame,
        n_bins=2,
        title=None,
    )

    assert axis is not None


def test_aoi_overlay_fixations_with_no_valid_coordinates():
    frame = pd.DataFrame(
        {
            "x_px": [np.nan],
            "y_px": [np.nan],
        }
    )

    axis = visualization.plot_aoi_overlay(
        [],
        fixations=frame,
        invert_y=False,
        title=None,
    )

    assert axis is not None


def test_scanpath_without_labels_annotation_or_axis_inversion():
    frame = pd.DataFrame(
        {
            "x_px": [1.0, 2.0],
            "y_px": [3.0, 4.0],
        }
    )

    axis = visualization.plot_scanpath(
        frame,
        label_col=None,
        annotate_order=False,
        invert_y=False,
        title=None,
    )

    assert axis is not None


def test_scanpath_annotation_without_semantic_labels():
    frame = pd.DataFrame(
        {
            "x_px": [1.0],
            "y_px": [2.0],
        }
    )

    axis = visualization.plot_scanpath(
        frame,
        label_col=None,
        annotate_order=True,
        title=None,
    )

    assert axis is not None


def test_dynamic_snapshot_with_no_visible_tracks():
    axis = visualization.plot_dynamic_aoi_snapshot(
        [],
        timestamp_ms=0.0,
        title=None,
    )

    assert axis is not None


# ======================================================================
# location_scale_bootstrap_monte_carlo.py adapter
# ======================================================================


def test_bootstrap_mcse_rejects_nonvector():
    with pytest.raises(
        SchemaError,
        match="replicate estimates are invalid",
    ):
        boot_mc._jackknife_sd_mcse(np.zeros((2, 2)))


def test_bootstrap_mcse_requires_three_replicates():
    with pytest.raises(
        SchemaError,
        match="at least three",
    ):
        boot_mc._jackknife_sd_mcse(np.array([1.0, 2.0]))


def test_bootstrap_mcse_rejects_centering_overflow():
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(
            SchemaError,
            match="finite centered estimates",
        ):
            boot_mc._jackknife_sd_mcse(
                np.array(
                    [
                        1e308,
                        -1e308,
                        0.0,
                    ]
                )
            )


def test_bootstrap_mcse_rejects_centered_sum_overflow():
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(
            SchemaError,
            match="centered sum of squares",
        ):
            boot_mc._jackknife_sd_mcse(
                np.array(
                    [
                        1e154,
                        -1e154,
                        0.0,
                    ]
                )
            )


def test_bootstrap_mcse_rejects_invalid_leave_one_out_variance(
    monkeypatch,
):
    monkeypatch.setattr(
        boot_mc.np,
        "dot",
        lambda a, b: 0.0,
    )

    with pytest.raises(
        SchemaError,
        match="leave-one-out variance",
    ):
        boot_mc._jackknife_sd_mcse(np.array([0.0, 1.0, 2.0]))


def test_bootstrap_mcse_rejects_nonfinite_final_mcse(
    monkeypatch,
):
    monkeypatch.setattr(
        boot_mc.np,
        "sum",
        lambda values: np.inf,
    )

    with pytest.raises(
        SchemaError,
        match="MCSE is non-finite",
    ):
        boot_mc._jackknife_sd_mcse(np.array([0.0, 1.0, 2.0, 3.0]))


# ======================================================================
# location_scale_hierarchical_bootstrap.py adapter branches
# ======================================================================


class _FakeHierSpec:
    group_col = "participant_id"
    outcome_col = "y"
    random_slope_predictor = "x"
    location_predictors = ()
    scale_predictors = ()


class _FakeHierResult:
    def __init__(self, covariance):
        self.spec = _FakeHierSpec()
        self.location_coef = np.array([0.0])
        self.scale_coef = np.array([0.0])
        self._covariance = covariance

    def random_effect_covariance_matrix(self):
        return self._covariance


class _FiniteRng:
    def standard_normal(self, shape):
        return np.ones(shape, dtype=float)


class _InfiniteRng:
    def standard_normal(self, shape):
        return np.full(shape, np.inf)


def _activate_fake_full_covariance(monkeypatch):
    monkeypatch.setattr(
        hier,
        "FullCovarianceLocationRandomSlopeScaleResult",
        _FakeHierResult,
    )


def test_hierarchical_population_draw_requires_two_groups(
    monkeypatch,
):
    _activate_fake_full_covariance(monkeypatch)
    result = _FakeHierResult(np.eye(3))

    with pytest.raises(
        SchemaError,
        match="at least two groups",
    ):
        hier._draw_population_effects(
            result,
            ("P1",),
            _FiniteRng(),
        )


def test_hierarchical_population_draw_rejects_invalid_covariance(
    monkeypatch,
):
    _activate_fake_full_covariance(monkeypatch)
    result = _FakeHierResult(np.eye(2))

    with pytest.raises(
        SchemaError,
        match="population matrix is invalid",
    ):
        hier._draw_population_effects(
            result,
            ("P1", "P2"),
            _FiniteRng(),
        )


def test_hierarchical_population_draw_rejects_non_pd_covariance(
    monkeypatch,
):
    _activate_fake_full_covariance(monkeypatch)
    covariance = np.array(
        [
            [1.0, 2.0, 0.0],
            [2.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    result = _FakeHierResult(covariance)

    with pytest.raises(
        SchemaError,
        match="not positive definite",
    ):
        hier._draw_population_effects(
            result,
            ("P1", "P2"),
            _FiniteRng(),
        )


def test_hierarchical_population_draw_rejects_nonfinite_cholesky(
    monkeypatch,
):
    _activate_fake_full_covariance(monkeypatch)
    result = _FakeHierResult(np.eye(3))

    monkeypatch.setattr(
        hier.np.linalg,
        "cholesky",
        lambda covariance: np.full((3, 3), np.nan),
    )

    with pytest.raises(
        SchemaError,
        match="Cholesky factor is non-finite",
    ):
        hier._draw_population_effects(
            result,
            ("P1", "P2"),
            _FiniteRng(),
        )


def test_hierarchical_population_draw_rejects_nonfinite_effects(
    monkeypatch,
):
    _activate_fake_full_covariance(monkeypatch)
    result = _FakeHierResult(np.eye(3))

    with pytest.raises(
        SchemaError,
        match="population effects are non-finite",
    ):
        hier._draw_population_effects(
            result,
            ("P1", "P2"),
            _InfiniteRng(),
        )


def test_hierarchical_simulation_rejects_missing_group_ids(
    monkeypatch,
):
    _activate_fake_full_covariance(monkeypatch)
    result = _FakeHierResult(np.eye(3))

    monkeypatch.setattr(
        hier._core,
        "_fixed_design",
        lambda *args, **kwargs: np.zeros(2),
    )

    frame = pd.DataFrame(
        {
            "participant_id": [
                None,
                "P2",
            ],
            "x": [
                0.0,
                1.0,
            ],
            "y": [
                0.0,
                0.0,
            ],
        }
    )

    with pytest.raises(
        SchemaError,
        match="group identities must be complete",
    ):
        hier._simulate_hierarchical_outcome(
            result,
            frame,
            rng=np.random.default_rng(1),
        )


def test_hierarchical_simulation_rejects_nonfinite_slope(
    monkeypatch,
):
    _activate_fake_full_covariance(monkeypatch)
    result = _FakeHierResult(np.eye(3))

    monkeypatch.setattr(
        hier._core,
        "_fixed_design",
        lambda *args, **kwargs: np.zeros(2),
    )

    monkeypatch.setattr(
        hier,
        "_draw_population_effects",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "participant_id": [
                    "P1",
                    "P2",
                ],
                "location_intercept": [
                    0.0,
                    0.0,
                ],
                "location_slope": [
                    0.0,
                    0.0,
                ],
                "log_scale_intercept": [
                    0.0,
                    0.0,
                ],
            }
        ),
    )

    frame = pd.DataFrame(
        {
            "participant_id": [
                "P1",
                "P2",
            ],
            "x": [
                np.nan,
                1.0,
            ],
            "y": [
                0.0,
                0.0,
            ],
        }
    )

    with pytest.raises(
        SchemaError,
        match="random-slope predictor is non-finite",
    ):
        hier._simulate_hierarchical_outcome(
            result,
            frame,
            rng=np.random.default_rng(1),
        )


def test_hierarchical_simulation_rejects_invalid_surface(
    monkeypatch,
):
    _activate_fake_full_covariance(monkeypatch)
    result = _FakeHierResult(np.eye(3))

    def fixed_design(
        data,
        predictors,
        coef,
        *,
        equation,
    ):
        if equation == "Location":
            return np.zeros(len(data))
        return np.full(len(data), 1000.0)

    monkeypatch.setattr(
        hier._core,
        "_fixed_design",
        fixed_design,
    )

    monkeypatch.setattr(
        hier,
        "_draw_population_effects",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "participant_id": [
                    "P1",
                    "P2",
                ],
                "location_intercept": [
                    0.0,
                    0.0,
                ],
                "location_slope": [
                    0.0,
                    0.0,
                ],
                "log_scale_intercept": [
                    0.0,
                    0.0,
                ],
            }
        ),
    )

    frame = pd.DataFrame(
        {
            "participant_id": [
                "P1",
                "P2",
            ],
            "x": [
                0.0,
                1.0,
            ],
            "y": [
                0.0,
                0.0,
            ],
        }
    )

    with np.errstate(over="ignore"):
        with pytest.raises(
            SchemaError,
            match="generating surface is invalid",
        ):
            hier._simulate_hierarchical_outcome(
                result,
                frame,
                rng=np.random.default_rng(1),
            )


def test_hierarchical_freeze_adapter_delegates(
    monkeypatch,
    tmp_path,
):
    expected = tmp_path / "certificate.json"

    monkeypatch.setattr(
        hier._core,
        "freeze_location_scale_hierarchical_bootstrap_certificate",
        lambda result, path, overwrite=False: Path(path),
    )

    result = hier.freeze_location_scale_hierarchical_bootstrap_certificate(
        object(),
        expected,
    )

    assert result == expected
