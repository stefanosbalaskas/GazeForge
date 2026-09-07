import copy
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.gaze_in_wild_coordinate_evidence import (
    EVIDENCE_FINGERPRINT,
    LIVE_RECORD_TYPE,
    SOURCE_BLOB,
    SOURCE_COMMIT,
    SOURCE_PATH,
    SOURCE_REPOSITORY,
    build_first_party_por_live_probe,
    evidence_fingerprint,
    probe_fingerprint,
    validate_first_party_por_source,
    validate_gaze_in_wild_por_coordinate_evidence,
    validate_live_por_probe_against_evidence,
)

EVIDENCE = Path(
    "validation/evidence/gaze-in-wild/"
    "gaze-in-wild-por-coordinate-semantics-evidence-v1.json"
)

SOURCE_SNIPPET = """
ETG.SceneResolution = [1920, 1080];
ETG.POR = [Gaze_Data.norm_pos_x, Gaze_Data.norm_pos_y];
ETG.POR(:, 2) = 1 - ETG.POR(:, 2);
[ETG.POR, ~] = linearizeData(ETG_T, ETG.POR, 'pchip');
ProcessData.ETG.SceneResolution = ETG.SceneResolution;
ProcessData.ETG.POR = interp1(ETG.T, ETG.POR, ProcessData.T,  'pchip', 'extrap');
"""


def _live_probe() -> dict:
    record = {
        "record_type": LIVE_RECORD_TYPE,
        "source_binding": {
            "repository": SOURCE_REPOSITORY,
            "commit_sha1": SOURCE_COMMIT,
            "path": SOURCE_PATH,
            "git_blob_sha1": SOURCE_BLOB,
        },
        "source_semantics": {
            "pupil_source_fields": ["norm_pos_x", "norm_pos_y"],
            "matlab_y_flip_present": True,
            "scene_resolution_px": [1920, 1080],
            "scene_resolution_stored_separately": True,
            "processdata_por_direct_interpolation_present": True,
            "required_marker_count": 6,
            "processdata_etg_por_occurrence_count": 1,
        },
        "verification": {
            "processdata_por_coordinate_space": "normalized_scene_image",
            "first_party_pixel_por_claim": False,
            "canonical_pixel_conversion_supported": True,
        },
        "boundaries": {
            "distribution_equivalence_verified": False,
            "participant_mapping_verified": False,
            "task_mapping_verified": False,
            "reuse_terms_verified": False,
            "analysis_use_permitted": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def _refingerprint(record: dict) -> dict:
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def test_immutable_por_evidence_is_exactly_bound():
    record = validate_gaze_in_wild_por_coordinate_evidence(EVIDENCE)
    assert record["evidence_fingerprint_sha256"] == EVIDENCE_FINGERPRINT
    assert evidence_fingerprint(record) == EVIDENCE_FINGERPRINT
    assert record["verification"]["processdata_por_coordinate_space"] == (
        "normalized_scene_image"
    )
    assert record["verification"]["first_party_pixel_por_claim"] is False
    assert record["mapping_boundary"]["participant_identity_mapping_verified"] is False
    assert record["rights_boundary"]["analysis_use_permitted"] is False


def test_first_party_source_markers_require_normalized_por_lineage():
    counts = validate_first_party_por_source(SOURCE_SNIPPET)
    assert counts == {
        "required_marker_count": 6,
        "processdata_etg_por_occurrence_count": 1,
    }


def test_missing_y_flip_is_rejected():
    source = SOURCE_SNIPPET.replace("ETG.POR(:, 2) = 1 - ETG.POR(:, 2);", "")
    with pytest.raises(BenchmarkIntegrityError, match="source markers are missing"):
        validate_first_party_por_source(source)


def test_duplicate_processdata_por_assignment_is_rejected():
    source = SOURCE_SNIPPET + "\nProcessData.ETG.POR = ProcessData.ETG.POR;\n"
    with pytest.raises(BenchmarkIntegrityError, match="exactly one reviewed"):
        validate_first_party_por_source(source)


def test_noncanonical_source_bytes_cannot_build_live_probe():
    with pytest.raises(BenchmarkIntegrityError, match="pinned Git blob"):
        build_first_party_por_live_probe(SOURCE_SNIPPET)


def test_metadata_only_live_probe_binds_to_immutable_evidence():
    evidence = validate_live_por_probe_against_evidence(_live_probe(), EVIDENCE)
    assert evidence["evidence_fingerprint_sha256"] == EVIDENCE_FINGERPRINT


def test_live_probe_cannot_promote_rights_or_analysis_permission():
    record = copy.deepcopy(_live_probe())
    record["boundaries"]["analysis_use_permitted"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="analysis_use_permitted"):
        validate_live_por_probe_against_evidence(record, EVIDENCE)


def test_live_probe_cannot_promote_participant_mapping():
    record = copy.deepcopy(_live_probe())
    record["boundaries"]["participant_mapping_verified"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="participant_mapping_verified"):
        validate_live_por_probe_against_evidence(record, EVIDENCE)


def test_live_probe_cannot_relabel_first_party_por_as_pixels():
    record = copy.deepcopy(_live_probe())
    record["verification"]["first_party_pixel_por_claim"] = True
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="pixel POR claim"):
        validate_live_por_probe_against_evidence(record, EVIDENCE)


def test_live_source_binding_drift_is_rejected_even_with_valid_probe_digest():
    record = copy.deepcopy(_live_probe())
    record["source_binding"]["commit_sha1"] = "0" * 40
    _refingerprint(record)
    with pytest.raises(BenchmarkIntegrityError, match="source binding drifted"):
        validate_live_por_probe_against_evidence(record, EVIDENCE)


def test_immutable_evidence_tampering_is_rejected_before_promotion():
    import json

    record = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    record["mapping_boundary"]["participant_task_mapping_verified"] = True
    with pytest.raises(BenchmarkIntegrityError, match="content fingerprint drifted"):
        validate_gaze_in_wild_por_coordinate_evidence(record)
