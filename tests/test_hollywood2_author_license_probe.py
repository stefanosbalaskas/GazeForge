import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_author_license_evidence import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256,
    GAZECOM_GIN_URL,
    HMD_GIN_URL,
    HOLLYWOOD2_GIN_URL,
    OPEN_LICENSE_PHRASE,
    build_probe_record,
    evidence_fingerprint,
    validate_hollywood2_author_license_evidence,
    validate_hollywood2_author_license_live_probe,
)

EVIDENCE_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-author-license-statement-evidence-v1.json"
)


def _text():
    return " ".join(
        [
            "Towards a better understanding of eye movements in natural contexts",
            "Ioannis Agtzidis",
            "Chapter 4 Hand-labeled data sets",
            OPEN_LICENSE_PHRASE,
            GAZECOM_GIN_URL,
            HOLLYWOOD2_GIN_URL,
            HMD_GIN_URL,
        ]
    )


def _live_record():
    return {
        "observed_statement": {
            "author_describes_chapter_data_as_publicly_available_with_open_source_license": True,
            "author_present": True,
            "chapter_4_hand_labeled_data_sets_present": True,
            "dissertation_title_present": True,
            "gazecom_gin_footnote_present": True,
            "hmd_gin_footnote_present": True,
            "hollywood2_gin_footnote_present": True,
            "hollywood2_repository_footnote_url": HOLLYWOOD2_GIN_URL,
            "open_source_license_statement_present": True,
            "statement_scope": "all_data_presented_in_dissertation_chapter_4",
        },
        "probe_fingerprint_sha256": EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256,
        "record_type": "hollywood2-author-license-live-probe-v1",
        "rights_interpretation": {
            "exact_license_identifier_recovered": False,
            "exact_license_text_recovered": False,
            "general_open_license_indication_verified": True,
            "gin_analysis_use_terms_status": "unresolved_exact_terms",
            "gin_raw_data_redistribution_terms_status": "unresolved_exact_terms",
            "license_inference_from_article_cc_by_permitted": False,
            "license_inference_from_underlying_hollywood2_terms_permitted": False,
            "repository_license_file_recovered": False,
        },
        "scientific_boundary": {
            "cross_dataset_validation_created": False,
            "exact_gin_dataset_license_verified": False,
            "frozen_evidence_performance_claim_created": False,
            "gin_analysis_use_authorized": False,
            "gin_raw_data_redistribution_authorized": False,
            "model_validation_created": False,
            "participant_identity_mapping_verified": False,
            "source_audit_ready": False,
        },
        "source": {
            "author": "Ioannis Agtzidis",
            "bytes": 44587570,
            "document_type": "doctoral_dissertation",
            "final_url": "https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
            "institution": "Technical University of Munich",
            "normalised_extracted_text_sha256": (
                "2e283d1f9f9f886c07f6629908f1cddc08b7d91fb1de76f50203b07e88974430"
            ),
            "requested_url": "https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
            "sha256": "f91705cafac65facf42563d6b3827148ef4114276759466a26afbc21ff4006ee",
            "title": "Towards a better understanding of eye movements in natural contexts",
            "year": 2020,
        },
        "status": "observed_author_dissertation_open_source_license_statement",
    }


def test_probe_records_statement_without_promoting_exact_rights():
    record = build_probe_record(
        pdf_bytes=b"%PDF synthetic fixture",
        extracted_text=_text(),
        final_url="https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
    )

    statement = record["observed_statement"]
    rights = record["rights_interpretation"]
    boundary = record["scientific_boundary"]
    assert statement["open_source_license_statement_present"] is True
    assert statement["hollywood2_gin_footnote_present"] is True
    assert rights["general_open_license_indication_verified"] is True
    assert rights["exact_license_identifier_recovered"] is False
    assert rights["exact_license_text_recovered"] is False
    assert rights["gin_analysis_use_terms_status"] == "unresolved_exact_terms"
    assert rights["gin_raw_data_redistribution_terms_status"] == "unresolved_exact_terms"
    assert boundary["exact_gin_dataset_license_verified"] is False
    assert boundary["gin_analysis_use_authorized"] is False
    assert boundary["gin_raw_data_redistribution_authorized"] is False
    assert boundary["source_audit_ready"] is False


def test_probe_refuses_missing_hollywood2_footnote():
    text = _text().replace(HOLLYWOOD2_GIN_URL, "")
    with pytest.raises(RuntimeError, match="hollywood2_gin_footnote_present"):
        build_probe_record(
            pdf_bytes=b"%PDF synthetic fixture",
            extracted_text=text,
            final_url="https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
        )


def test_probe_refuses_missing_open_license_statement():
    text = _text().replace(OPEN_LICENSE_PHRASE, "")
    with pytest.raises(RuntimeError, match="open_source_license_statement_present"):
        build_probe_record(
            pdf_bytes=b"%PDF synthetic fixture",
            extracted_text=text,
            final_url="https://mediatum.ub.tum.de/doc/1538004/1538004.pdf",
        )


def test_frozen_evidence_validates_and_has_expected_fingerprint():
    record = validate_hollywood2_author_license_evidence(EVIDENCE_PATH)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256


def test_live_probe_is_bound_to_frozen_evidence():
    result = validate_hollywood2_author_license_live_probe(_live_record(), EVIDENCE_PATH)
    assert result["probe_fingerprint_sha256"] == EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256


def test_refingerprinted_license_promotion_is_rejected(tmp_path):
    record = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    promoted = copy.deepcopy(record)
    promoted["rights_interpretation"]["exact_license_identifier_recovered"] = True
    promoted["scientific_boundary"]["exact_gin_dataset_license_verified"] = True
    promoted["evidence_fingerprint_sha256"] = evidence_fingerprint(promoted)
    path = tmp_path / "promoted.json"
    path.write_text(json.dumps(promoted), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_author_license_evidence(path)


def test_refingerprinted_permission_promotion_is_rejected(tmp_path):
    record = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    promoted = copy.deepcopy(record)
    promoted["rights_interpretation"]["analysis_use_authorized"] = True
    promoted["rights_interpretation"]["raw_data_redistribution_authorized"] = True
    promoted["scientific_boundary"]["gin_analysis_use_authorized"] = True
    promoted["scientific_boundary"]["gin_raw_data_redistribution_authorized"] = True
    promoted["evidence_fingerprint_sha256"] = evidence_fingerprint(promoted)
    path = tmp_path / "promoted.json"
    path.write_text(json.dumps(promoted), encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_author_license_evidence(path)


def test_live_probe_source_drift_is_rejected():
    drifted = _live_record()
    drifted["source"]["sha256"] = "0" * 64
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_author_license_live_probe(drifted, EVIDENCE_PATH)
