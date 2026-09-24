from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gazeforge.gaze_in_wild_current_listing_evidence as giw_listing
import gazeforge.gaze_in_wild_distribution_evidence as giw_distribution
import gazeforge.gaze_in_wild_supplementary_evidence as giw_supplement
import gazeforge.hollywood2_annotation_provenance as h2_annotation
import gazeforge.hollywood2_author_license_evidence as h2_author
import gazeforge.hollywood2_coordinate_metadata as h2_coordinate
import gazeforge.hollywood2_gin_accessible_host_evidence as h2_access
import gazeforge.hollywood2_history_evidence as h2_history
import gazeforge.hollywood2_original_subject_metadata as h2_original_probe
import gazeforge.hollywood2_original_subject_metadata_evidence as h2_original
import gazeforge.hollywood2_participant_crosswalk_exhaustion as h2_crosswalk
import gazeforge.quality_gating as quality
import gazeforge.resampling as resampling
import gazeforge.visualization as visualization
import gazeforge.visus_scaffold as visus_scaffold
from gazeforge.exceptions import BenchmarkIntegrityError, SchemaError

GIW_CURRENT_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-current-first-party-listing-evidence-v1.json"
)

GIW_DISTRIBUTION_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-distribution-availability-evidence-v1.json"
)

GIW_SUPPLEMENT_EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/gaze-in-wild-supplementary-identity-evidence-v1.json"
)

H2_ANNOTATION_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-annotation-provenance-evidence-v1.json"
)

H2_ACCESS_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-gin-host-metadata-accessible-evidence-v1.json"
)

H2_HISTORY_EVIDENCE = Path("validation/evidence/hollywood2/hollywood2-gin-history-evidence-v1.json")

H2_AUTHOR_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-author-license-statement-evidence-v1.json"
)

H2_ORIGINAL_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-original-subject-metadata-evidence-v1.json"
)

H2_CROSSWALK_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-participant-crosswalk-exhaustion-evidence-v1.json"
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ======================================================================
# quality_gating.py
# ======================================================================


def test_motion_index_singleton_group_leaves_transition_unknown():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1"],
            "trial_id": ["T1"],
            "timestamp_ms": [0.0],
            "acc_x": [0.0],
            "acc_y": [0.0],
            "acc_z": [1.0],
        }
    )

    result = quality.derive_accelerometer_motion_index(frame)

    assert np.isnan(result.loc[0, "motion_jerk"])
    assert np.isnan(result.loc[0, "motion_index"])


def test_motion_index_no_valid_acceleration_transition():
    frame = pd.DataFrame(
        {
            "participant_id": ["P1", "P1"],
            "trial_id": ["T1", "T1"],
            "timestamp_ms": [0.0, 10.0],
            "acc_x": [0.0, np.nan],
            "acc_y": [0.0, 0.0],
            "acc_z": [1.0, 1.0],
        }
    )

    result = quality.derive_accelerometer_motion_index(frame)

    assert result["motion_jerk"].isna().all()
    assert result["motion_index"].isna().all()


def test_motion_summary_scalar_key_compatibility(monkeypatch):
    frame = pd.DataFrame(
        {
            "quality_modality": ["pupil", "pupil"],
            "quality_weight": [1.0, 0.5],
            "quality_state": ["clean", "downweighted"],
        }
    )

    class FakeGroupBy:
        def __iter__(self):
            yield "pupil", frame

    original_groupby = pd.DataFrame.groupby

    def fake_groupby(self, by=None, *args, **kwargs):
        if self is frame:
            return FakeGroupBy()
        return original_groupby(self, by, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "groupby", fake_groupby)

    result = quality.summarize_motion_quality(
        frame,
        group_cols=(),
    )

    assert result.loc[0, "quality_modality"] == "pupil"
    assert result.loc[0, "n_samples"] == 2


# ======================================================================
# resampling.py residual branches
# ======================================================================


def test_interpolation_exact_left_tolerance_branch():
    result = resampling._interpolate_with_gap_limit(
        np.array([0.0, 10.0, 20.0]),
        np.array([0.0, 1.0, 2.0]),
        np.array([10.0 + 5e-10]),
        max_gap_ms=20.0,
    )

    assert result[0] == pytest.approx(1.0)


def test_interpolation_gap_too_large_remains_missing():
    result = resampling._interpolate_with_gap_limit(
        np.array([0.0, 100.0]),
        np.array([0.0, 10.0]),
        np.array([50.0]),
        max_gap_ms=10.0,
    )

    assert np.isnan(result[0])


# ======================================================================
# GIW current-listing final residual
# ======================================================================


def _current_listing_probe(*, historical_status=404):
    record = {
        "record_type": giw_listing.PROBE_RECORD_TYPE,
        "current_first_party_page": {
            "url": giw_listing.RIT_LAB_URL,
            "observed_http_status": 200,
            "listing_text": giw_listing.LISTING_TEXT,
            "listing_present_exactly_once": True,
            "listing_target": giw_listing.PUBLICATION_TARGET,
            "listing_target_class": "publication_pubmed",
            "listing_target_is_expected_publication": True,
            "listing_target_is_direct_dataset_archive_verified": False,
            "dataset_file_rights_terms_found_on_listing": False,
        },
        "historical_endpoint_observation": {
            "url": giw_listing.HISTORICAL_HTTPS_URL,
            "secure_tls_certificate_verified": False,
            "secure_transport_failure_class": ("tls_certificate_verification_error"),
            "tls_unverified_fallback_used": True,
            "observed_http_status": historical_status,
            "retrieval_succeeded": False,
            "transport_status_is_source_identity_or_rights_evidence": False,
            "tls_unverified_fallback_is_source_authentication_evidence": False,
            "observation_is_global_unavailability_proof": False,
            "observation_is_exact_copy_identity_evidence": False,
        },
        "review_trigger": {
            "listing_target_changed_from_expected_publication": False,
            "listing_target_is_first_party_rit_candidate": False,
            "requires_human_evidence_review": False,
            "automatic_source_or_rights_promotion_permitted": False,
            "historical_transport_observation_is_review_gate": False,
        },
        "scientific_boundary": {
            "current_first_party_listing_verified": True,
            "current_exact_authoritative_copy_obtained": False,
            "dataset_file_rights_resolved": False,
            "analysis_use_permitted": False,
            "redistribution_authorized": False,
            "participant_mapping_verified": False,
            "complete_trial_to_task_mapping_verified": False,
            "distributed_file_sampling_cadence_verified": False,
            "independent_labeller_recoverability_verified": False,
            "human_human_agreement_created": False,
            "participant_disjoint_model_validation_created": False,
            "cross_dataset_performance_created": False,
            "gp3_validity_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
        "claim_limit": "transport diagnostics are non-gating",
    }

    record["listing_state_fingerprint_sha256"] = giw_listing.listing_state_fingerprint(record)
    record["observation_fingerprint_sha256"] = giw_listing.observation_fingerprint(record)

    return record


def test_current_listing_probe_rejects_boolean_http_status():
    probe = _current_listing_probe(
        historical_status=True,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an integer",
    ):
        giw_listing.validate_gaze_in_wild_current_listing_probe(
            probe,
            GIW_CURRENT_EVIDENCE,
        )


# ======================================================================
# GIW distribution evidence
# ======================================================================


def test_distribution_requires_exactly_two_secondary_leads():
    record = _json(GIW_DISTRIBUTION_EVIDENCE)
    record["secondary_recovery_leads"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="exactly two",
    ):
        giw_distribution.validate_gaze_in_wild_distribution_availability_evidence(record)


def test_distribution_secondary_leads_must_be_mappings():
    record = _json(GIW_DISTRIBUTION_EVIDENCE)
    record["secondary_recovery_leads"][0] = "not-a-mapping"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be mappings",
    ):
        giw_distribution.validate_gaze_in_wild_distribution_availability_evidence(record)


# ======================================================================
# GIW supplementary evidence
# ======================================================================


def test_supplementary_rejects_drifted_official_url():
    record = _json(GIW_SUPPLEMENT_EVIDENCE)
    record["publication"]["supplementary_information_url"] = (
        "https://example.invalid/not-the-supplement.pdf"
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="supplement URL drifted",
    ):
        giw_supplement.validate_gaze_in_wild_supplementary_identity_evidence(record)


def test_supplementary_requires_claim_limits():
    record = _json(GIW_SUPPLEMENT_EVIDENCE)
    record["claim_limits"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="preserve claim limits",
    ):
        giw_supplement.validate_gaze_in_wild_supplementary_identity_evidence(record)


def test_supplementary_requires_next_actions():
    record = _json(GIW_SUPPLEMENT_EVIDENCE)
    record["next_required_actions"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="next required actions",
    ):
        giw_supplement.validate_gaze_in_wild_supplementary_identity_evidence(record)


def test_supplementary_detects_immutable_fingerprint_drift():
    record = _json(GIW_SUPPLEMENT_EVIDENCE)
    record["coverage_only_extra"] = True
    record["evidence_fingerprint_sha256"] = giw_supplement.evidence_fingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable v1 fingerprint drifted",
    ):
        giw_supplement.validate_gaze_in_wild_supplementary_identity_evidence(record)


# ======================================================================
# Hollywood2 annotation provenance
# ======================================================================


def test_annotation_provenance_requires_claim_limits():
    record = _json(H2_ANNOTATION_EVIDENCE)
    record["claim_limits"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="claim limits",
    ):
        h2_annotation.validate_hollywood2_annotation_provenance_evidence(record)


def test_annotation_provenance_requires_next_actions():
    record = _json(H2_ANNOTATION_EVIDENCE)
    record["next_required_actions"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="next required actions",
    ):
        h2_annotation.validate_hollywood2_annotation_provenance_evidence(record)


def test_annotation_provenance_detects_bad_self_fingerprint():
    record = _json(H2_ANNOTATION_EVIDENCE)
    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        h2_annotation.validate_hollywood2_annotation_provenance_evidence(record)


def test_annotation_provenance_detects_immutable_fingerprint_drift():
    record = _json(H2_ANNOTATION_EVIDENCE)
    record["coverage_only_extra"] = True
    record["evidence_fingerprint_sha256"] = h2_annotation.evidence_fingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable v1 fingerprint drifted",
    ):
        h2_annotation.validate_hollywood2_annotation_provenance_evidence(record)


# ======================================================================
# Hollywood2 coordinate metadata
# ======================================================================


def test_coordinate_probe_required_schema_false_branch(
    tmp_path,
):
    path = tmp_path / "incomplete.arff"

    path.write_text(
        "\n".join(
            [
                "@relation gaze",
                "%@METADATA width_px 1920",
                "%@METADATA height_px 1080",
                "%@METADATA width_mm 530",
                "%@METADATA height_mm 300",
                "%@METADATA distance_mm 650",
                "@attribute time numeric",
                "@attribute x numeric",
                "@attribute y numeric",
                "@attribute confidence numeric",
                "@attribute handlabeller_1 string",
                "@data",
                "",
            ]
        ),
        encoding="utf-8",
    )

    record = h2_coordinate.build_hollywood2_coordinate_metadata_probe(tmp_path)

    assert record["record_type"] == h2_coordinate.RECORD_TYPE


# ======================================================================
# Hollywood2 accessible-host evidence
# ======================================================================


def test_accessible_host_requires_four_datacite_rows():
    record = _json(H2_ACCESS_EVIDENCE)
    record["live_observation"]["datacite_queries"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="DataCite ledger drifted",
    ):
        h2_access.validate_hollywood2_gin_accessible_host_evidence(record)


def test_accessible_host_datacite_rows_must_be_mappings():
    record = _json(H2_ACCESS_EVIDENCE)
    record["live_observation"]["datacite_queries"][0] = 123

    with pytest.raises(
        BenchmarkIntegrityError,
        match="DataCite row is invalid",
    ):
        h2_access.validate_hollywood2_gin_accessible_host_evidence(record)


def test_accessible_host_detects_bad_self_fingerprint():
    record = _json(H2_ACCESS_EVIDENCE)
    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        h2_access.validate_hollywood2_gin_accessible_host_evidence(record)


# ======================================================================
# Hollywood2 history evidence
# ======================================================================


def test_history_requires_all_commit_subjects():
    record = _json(H2_HISTORY_EVIDENCE)
    record["repository_history"]["commit_subjects"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="seven reachable commit summaries",
    ):
        h2_history.validate_hollywood2_gin_history_evidence(record)


def test_history_requires_three_readme_versions():
    record = _json(H2_HISTORY_EVIDENCE)
    record["readme_history"]["versions"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="three README versions",
    ):
        h2_history.validate_hollywood2_gin_history_evidence(record)


def test_history_readme_keyword_evidence_must_remain_empty():
    record = _json(H2_HISTORY_EVIDENCE)
    record["readme_history"]["versions"][0]["keyword_lines"] = ["license"]

    with pytest.raises(
        BenchmarkIntegrityError,
        match="keyword evidence must remain empty",
    ):
        h2_history.validate_hollywood2_gin_history_evidence(record)


def test_history_requires_claim_limits():
    record = _json(H2_HISTORY_EVIDENCE)
    record["claim_limits"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="claim limits",
    ):
        h2_history.validate_hollywood2_gin_history_evidence(record)


def test_history_requires_next_actions():
    record = _json(H2_HISTORY_EVIDENCE)
    record["next_required_actions"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="next required actions",
    ):
        h2_history.validate_hollywood2_gin_history_evidence(record)


def test_history_detects_bad_self_fingerprint():
    record = _json(H2_HISTORY_EVIDENCE)
    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        h2_history.validate_hollywood2_gin_history_evidence(record)


def test_history_detects_immutable_fingerprint_drift():
    record = _json(H2_HISTORY_EVIDENCE)
    record["coverage_only_extra"] = True
    record["evidence_fingerprint_sha256"] = h2_history.evidence_fingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable history evidence fingerprint drifted",
    ):
        h2_history.validate_hollywood2_gin_history_evidence(record)


# ======================================================================
# Hollywood2 participant crosswalk
# ======================================================================


def test_crosswalk_requires_resolution_routes():
    record = _json(H2_CROSSWALK_EVIDENCE)
    record["remaining_authoritative_resolution_routes"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="resolution routes drifted",
    ):
        h2_crosswalk.validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_crosswalk_requires_six_claim_limits():
    record = _json(H2_CROSSWALK_EVIDENCE)
    record["claim_limits"] = []

    with pytest.raises(
        BenchmarkIntegrityError,
        match="claim limits drifted",
    ):
        h2_crosswalk.validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_crosswalk_detects_bad_self_fingerprint():
    record = _json(H2_CROSSWALK_EVIDENCE)
    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        h2_crosswalk.validate_hollywood2_participant_crosswalk_exhaustion(record)


def test_crosswalk_detects_immutable_fingerprint_drift():
    record = _json(H2_CROSSWALK_EVIDENCE)
    record["coverage_only_extra"] = True
    record["evidence_fingerprint_sha256"] = h2_crosswalk.evidence_fingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable fingerprint drifted",
    ):
        h2_crosswalk.validate_hollywood2_participant_crosswalk_exhaustion(record)


# ======================================================================
# Hollywood2 author-license evidence
# ======================================================================


def test_author_license_loader_missing_file(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        h2_author._load_json_object(tmp_path / "missing.json")


def test_author_license_loader_rejects_nonobject(tmp_path):
    path = tmp_path / "array.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be one JSON object",
    ):
        h2_author._load_json_object(path)


def test_author_license_mapping_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="field",
    ):
        h2_author._mapping({}, "missing")


def test_author_license_equal_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        h2_author._equal(
            "actual",
            "expected",
            "demo",
        )


def test_author_license_true_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        h2_author._true(
            False,
            "demo",
        )


def test_author_license_false_guard():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        h2_author._false(
            True,
            "demo",
        )


def test_author_license_detects_bad_self_fingerprint():
    record = _json(H2_AUTHOR_EVIDENCE)
    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        h2_author.validate_hollywood2_author_license_evidence(record)


def test_author_license_detects_immutable_fingerprint_drift():
    record = _json(H2_AUTHOR_EVIDENCE)
    record["coverage_only_extra"] = True
    record["evidence_fingerprint_sha256"] = h2_author.evidence_fingerprint(record)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable v1 fingerprint drifted",
    ):
        h2_author.validate_hollywood2_author_license_evidence(record)


def test_author_license_live_probe_detects_new_bytes():
    extracted_text = " ".join(
        [
            "Towards a better understanding of eye movements in natural contexts",
            "Ioannis Agtzidis",
            "Chapter 4 Hand-Labeled Data Sets",
            h2_author.OPEN_LICENSE_PHRASE,
            h2_author.HOLLYWOOD2_GIN_URL,
            h2_author.GAZECOM_GIN_URL,
            h2_author.HMD_GIN_URL,
        ]
    )

    probe = h2_author.build_probe_record(
        pdf_bytes=b"coverage-only-different-pdf",
        extracted_text=extracted_text,
        final_url=h2_author.SOURCE_URL,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="bytes/text or markers drifted",
    ):
        h2_author.validate_hollywood2_author_license_live_probe(
            probe,
            H2_AUTHOR_EVIDENCE,
        )


# ======================================================================
# Hollywood2 original-subject live-probe branches
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
and non-transferable license. You may not sub-license or
transfer the dataset. It is your responsibility to seek prior
written permission.
</body></html>
"""


def _fetch(body: bytes, *, url: str):
    return {
        "requested_url": url,
        "final_url": url,
        "http_status": 200,
        "content_type": "text/html; charset=utf-8",
        "content_length": str(len(body)),
        "content_disposition": None,
        "body": body,
    }


def _original_probe():
    return h2_original_probe.build_probe_record(
        _fetch(
            _DESCRIPTION,
            url=h2_original.DESCRIPTION_URL,
        ),
        _fetch(
            _LICENSE,
            url=h2_original.LICENSE_URL,
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


def _refingerprint_original(probe):
    probe["probe_fingerprint_sha256"] = h2_original_probe.probe_fingerprint(probe)
    return probe


def test_original_subject_rejects_changed_data_link_count():
    probe = _original_probe()
    probe["description"]["hollywood2_data_links"] = []
    _refingerprint_original(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="data-link surface changed",
    ):
        h2_original.validate_hollywood2_original_subject_live_probe(
            probe,
            H2_ORIGINAL_EVIDENCE,
        )


def test_original_subject_rejects_nonmapping_data_link():
    probe = _original_probe()
    probe["description"]["hollywood2_data_links"][0] = "invalid"
    _refingerprint_original(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="data link is invalid",
    ):
        h2_original.validate_hollywood2_original_subject_live_probe(
            probe,
            H2_ORIGINAL_EVIDENCE,
        )


def test_original_subject_rejects_non_html_archive_route():
    probe = _original_probe()
    probe["advertised_data_link_head"]["content_type"] = "application/octet-stream"
    _refingerprint_original(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="no longer resolves to HTML",
    ):
        h2_original.validate_hollywood2_original_subject_live_probe(
            probe,
            H2_ORIGINAL_EVIDENCE,
        )


# ======================================================================
# visualization.py
# ======================================================================


def test_event_probability_plot_requires_probability_columns():
    frame = pd.DataFrame(
        {
            "timestamp_ms": [0.0, 10.0],
        }
    )

    with pytest.raises(
        SchemaError,
        match="has no columns with prefix",
    ):
        visualization.plot_event_probabilities(frame)


def test_aoi_overlay_image_branch():
    axis = visualization.plot_aoi_overlay(
        [],
        image=np.zeros((2, 2)),
        title=None,
    )

    assert axis is not None


# ======================================================================
# VISUS scaffold
# ======================================================================


def test_visus_scaffold_rejects_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        visus_scaffold.build_visus_source_audit_scaffold(tmp_path / "missing")


def test_visus_scaffold_rejects_wrong_write_object(tmp_path):
    with pytest.raises(TypeError):
        visus_scaffold.write_visus_source_audit_scaffold(
            object(),
            tmp_path / "out.json",
        )


def test_visus_scaffold_root_symlink_guard_via_contract(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "source"
    root.mkdir()

    original = Path.is_symlink

    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: True if self == root else original(self),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="symbolic-link root",
    ):
        visus_scaffold.build_visus_source_audit_scaffold(root)


def test_visus_inventory_symlink_guard_via_contract(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "source"
    root.mkdir()

    candidate = root / "candidate.txt"
    candidate.write_text("data", encoding="utf-8")

    original = Path.is_symlink

    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: True if self == candidate else original(self),
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="refuses symbolic links",
    ):
        visus_scaffold._inventory(root)
