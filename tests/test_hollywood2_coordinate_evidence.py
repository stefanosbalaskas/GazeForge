from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_coordinate_evidence import (
    EVIDENCE_FINGERPRINT,
    evidence_fingerprint,
    validate_author_input_convention,
    validate_hollywood2_coordinate_evidence,
    validate_live_probe_against_coordinate_evidence,
)
from gazeforge.hollywood2_coordinate_metadata import probe_fingerprint

EVIDENCE_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-coordinate-semantics-evidence-v1.json"
)


def _reviewed_live_probe() -> dict:
    metadata_signatures = [
        {
            "metadata": {
                "width_px": float(index + 1),
                "height_px": 1.0,
                "width_mm": 475.0,
                "height_mm": 250.0,
                "distance_mm": 600.0,
            },
            "file_count": 1 if index < 23 else 674,
            "metadata_signature_sha256": f"{index + 1:064x}",
        }
        for index in range(24)
    ]
    record = {
        "record_type": "hollywood2-coordinate-metadata-live-probe-v1",
        "status": "observed-pinned-arff-header-metadata",
        "source_binding": {
            "repository": "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em.git",
            "commit_sha1": "870fa6d6209c9085260918d61433a0a2c70fd497",
        },
        "header_inventory": {
            "arff_file_count": 697,
            "unique_header_sha256_count": 24,
            "max_header_bytes": 380,
            "required_gaze_schema_file_count": 697,
            "author_convention_metadata_complete_file_count": 697,
            "attribute_signatures": [
                {
                    "attributes": [
                        "time",
                        "x",
                        "y",
                        "confidence",
                        "handlabeller_1",
                        "handlabeller_final",
                    ],
                    "file_count": 697,
                }
            ],
            "metadata_key_file_counts": {
                "distance_mm": 697,
                "height_mm": 697,
                "height_px": 697,
                "width_mm": 697,
                "width_px": 697,
            },
            "metadata_signatures": metadata_signatures,
            "marker_file_counts": {
                "pixel_or_px": 697,
                "screen": 0,
                "resolution": 0,
                "width": 697,
                "height": 697,
                "monitor_or_display": 0,
                "stimulus_or_video": 0,
                "degree_or_visual_angle": 0,
            },
        },
        "coordinate_boundary": {
            "header_vocabulary_observed": True,
            "all_headers_match_author_input_metadata_convention": True,
            "coordinate_unit_candidate": "pixels",
            "coordinate_unit_verified": False,
            "coordinate_verification_basis_created": False,
            "pixel_to_visual_angle_conversion_verified": False,
            "unit_sensitive_cross_dataset_modelling_ready": False,
        },
        "mapping_boundary": {
            "participant_identity_mapping_verified": False,
            "source_token_to_participant_mapping_verified": False,
        },
        "rights_boundary": {
            "new_rights_permission_created": False,
            "raw_source_redistribution_authorized": False,
        },
        "scientific_boundary": {
            "raw_source_rows_read": False,
            "raw_source_rows_embedded": False,
            "source_filenames_embedded": False,
            "participant_disjoint_validation_created": False,
            "cross_dataset_validation_created": False,
            "new_empirical_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def test_immutable_coordinate_evidence_validates() -> None:
    record = validate_hollywood2_coordinate_evidence(EVIDENCE_PATH)
    assert record["evidence_fingerprint_sha256"] == EVIDENCE_FINGERPRINT
    assert evidence_fingerprint(record) == EVIDENCE_FINGERPRINT
    assert record["verification"]["coordinate_unit"] == "pixels"
    assert record["verification"]["coordinate_unit_verified"] is True
    assert record["scientific_boundary"]["cross_dataset_validation_created"] is False


def test_immutable_coordinate_evidence_rejects_rights_promotion() -> None:
    record = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    record["rights_boundary"]["new_analysis_permission_created"] = True
    record["evidence_fingerprint_sha256"] = evidence_fingerprint(record)

    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_coordinate_evidence(record)


def test_author_input_convention_requires_units_and_metadata_keys() -> None:
    text = """
    %@METADATA width_px 1280
    %@METADATA height_px 720
    %@METADATA width_mm 400
    %@METADATA height_mm 225
    %@METADATA distance_mm 450
    time (in microseconds)
    x and y - the on-screen coordinates (in pixels; conversion follows)
    """
    validate_author_input_convention(text)

    with pytest.raises(BenchmarkIntegrityError, match="markers are missing"):
        validate_author_input_convention(text.replace("coordinates (in pixels", "coordinates"))


def test_live_probe_cannot_promote_participant_mapping() -> None:
    live = _reviewed_live_probe()
    live["mapping_boundary"]["participant_identity_mapping_verified"] = True
    live["probe_fingerprint_sha256"] = probe_fingerprint(live)

    with pytest.raises(BenchmarkIntegrityError):
        validate_live_probe_against_coordinate_evidence(live, EVIDENCE_PATH)


def test_live_probe_must_match_reviewed_fingerprint() -> None:
    live = _reviewed_live_probe()
    assert live["probe_fingerprint_sha256"] != (
        "d3ed5f9bc005ec435c34df1aa8fb0cb30599d49dff4835085f00114d43e185bd"
    )

    with pytest.raises(BenchmarkIntegrityError, match="drifted from review"):
        validate_live_probe_against_coordinate_evidence(live, EVIDENCE_PATH)
