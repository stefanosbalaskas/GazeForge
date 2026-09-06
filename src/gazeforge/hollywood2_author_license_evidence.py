"""Conservative evidence helpers for the Hollywood2EM author license statement."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SOURCE_URL = "https://mediatum.ub.tum.de/doc/1538004/1538004.pdf"
LIVE_RECORD_TYPE = "hollywood2-author-license-live-probe-v1"
LIVE_STATUS = "observed_author_dissertation_open_source_license_statement"
OPEN_LICENSE_PHRASE = (
    "All the data presented in this chapter are made publicly available with an open-source "
    "license"
)
HOLLYWOOD2_GIN_URL = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"
GAZECOM_GIN_URL = "https://gin.g-node.org/ioannis.agtzidis/gazecom_annotations"
HMD_GIN_URL = "https://gin.g-node.org/ioannis.agtzidis/360_em_dataset"


def sha256_bytes(data: bytes) -> str:
    """Return a lowercase SHA-256 digest for bytes."""
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    """Serialize one JSON-compatible value canonically for fingerprinting."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def normalise_extracted_text(text: str) -> str:
    """Normalize PDF-extracted whitespace without altering lexical content."""
    return re.sub(r"\s+", " ", text).strip()


def build_probe_record(*, pdf_bytes: bytes, extracted_text: str, final_url: str) -> dict[str, Any]:
    """Build a conservative live record from one downloaded dissertation PDF.

    The record verifies only the observed author-authored statement and repository footnotes.
    It deliberately does not infer an exact license identifier, analysis permission,
    redistribution permission, participant mapping, source-audit readiness, or performance.
    """
    normalised = normalise_extracted_text(extracted_text)
    lower = normalised.lower()
    required = {
        "dissertation_title_present": (
            "towards a better understanding of eye movements in natural contexts" in lower
        ),
        "author_present": "ioannis agtzidis" in lower,
        "chapter_4_hand_labeled_data_sets_present": "chapter 4 hand-labeled data sets" in lower,
        "open_source_license_statement_present": OPEN_LICENSE_PHRASE.lower() in lower,
        "hollywood2_gin_footnote_present": HOLLYWOOD2_GIN_URL.lower() in lower,
        "gazecom_gin_footnote_present": GAZECOM_GIN_URL.lower() in lower,
        "hmd_gin_footnote_present": HMD_GIN_URL.lower() in lower,
    }
    missing = [name for name, present in required.items() if not present]
    if missing:
        raise RuntimeError(f"Hollywood2 author-license dissertation markers missing: {missing}")

    record: dict[str, Any] = {
        "record_type": LIVE_RECORD_TYPE,
        "status": LIVE_STATUS,
        "source": {
            "institution": "Technical University of Munich",
            "document_type": "doctoral_dissertation",
            "author": "Ioannis Agtzidis",
            "year": 2020,
            "title": "Towards a better understanding of eye movements in natural contexts",
            "requested_url": SOURCE_URL,
            "final_url": final_url,
            "bytes": len(pdf_bytes),
            "sha256": sha256_bytes(pdf_bytes),
            "normalised_extracted_text_sha256": sha256_bytes(normalised.encode("utf-8")),
        },
        "observed_statement": {
            **required,
            "statement_scope": "all_data_presented_in_dissertation_chapter_4",
            "hollywood2_repository_footnote_url": HOLLYWOOD2_GIN_URL,
            "author_describes_chapter_data_as_publicly_available_with_open_source_license": True,
        },
        "rights_interpretation": {
            "general_open_license_indication_verified": True,
            "exact_license_identifier_recovered": False,
            "exact_license_text_recovered": False,
            "repository_license_file_recovered": False,
            "gin_analysis_use_terms_status": "unresolved_exact_terms",
            "gin_raw_data_redistribution_terms_status": "unresolved_exact_terms",
            "license_inference_from_article_cc_by_permitted": False,
            "license_inference_from_underlying_hollywood2_terms_permitted": False,
        },
        "scientific_boundary": {
            "exact_gin_dataset_license_verified": False,
            "gin_analysis_use_authorized": False,
            "gin_raw_data_redistribution_authorized": False,
            "participant_identity_mapping_verified": False,
            "source_audit_ready": False,
            "model_validation_created": False,
            "cross_dataset_validation_created": False,
            "frozen_evidence_performance_claim_created": False,
        },
    }
    record["probe_fingerprint_sha256"] = sha256_bytes(canonical_bytes(record))
    return record
