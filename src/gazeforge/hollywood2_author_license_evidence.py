"""Conservative evidence helpers for the Hollywood2EM author license statement."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError

SOURCE_URL = "https://mediatum.ub.tum.de/doc/1538004/1538004.pdf"
LIVE_RECORD_TYPE = "hollywood2-author-license-live-probe-v1"
LIVE_STATUS = "observed_author_dissertation_open_source_license_statement"
EVIDENCE_RECORD_TYPE = "hollywood2-author-license-statement-evidence-v1"
EVIDENCE_STATUS = "verified-author-dissertation-open-license-indication-exact-terms-unresolved"
OPEN_LICENSE_PHRASE = (
    "All the data presented in this chapter are made publicly available with an open-source "
    "license"
)
HOLLYWOOD2_GIN_URL = "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"
HOLLYWOOD2_GIN_REPOSITORY = f"{HOLLYWOOD2_GIN_URL}.git"
GAZECOM_GIN_URL = "https://gin.g-node.org/ioannis.agtzidis/gazecom_annotations"
HMD_GIN_URL = "https://gin.g-node.org/ioannis.agtzidis/360_em_dataset"
GIN_COMMIT_SHA1 = "870fa6d6209c9085260918d61433a0a2c70fd497"
GROUND_TRUTH_EVIDENCE_FINGERPRINT_SHA256 = (
    "d5375b8768984ef76da02597c55b225aaff4088fd24698c0d53363e2df6b20ea"
)
UNDERLYING_RIGHTS_EVIDENCE_FINGERPRINT_SHA256 = (
    "6227045c3cc831b3669b34ca74b955847df4b26fafbf825c9a1b5473e25bc943"
)
PDF_BYTES = 44_587_570
PDF_SHA256 = "f91705cafac65facf42563d6b3827148ef4114276759466a26afbc21ff4006ee"
EXTRACTED_TEXT_SHA256 = "2e283d1f9f9f886c07f6629908f1cddc08b7d91fb1de76f50203b07e88974430"
EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256 = (
    "f99aadc6e0c3bb694fe63321aeacd8f9203868e3b611c99e98b85ebbaafa0a47"
)
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "b01da719afe18f4eb0103a17d6e8c85f3750ba299050f8026063a9ebb55b1b2e"
)


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


def _without_fingerprint(record: Mapping[str, Any], key: str) -> dict[str, Any]:
    body = dict(record)
    body.pop(key, None)
    return body


def probe_fingerprint(record: Mapping[str, Any]) -> str:
    """Recompute one live-probe fingerprint."""
    return sha256_bytes(canonical_bytes(_without_fingerprint(record, "probe_fingerprint_sha256")))


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Recompute one frozen-evidence fingerprint."""
    return sha256_bytes(
        canonical_bytes(_without_fingerprint(record, "evidence_fingerprint_sha256"))
    )


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
    record["probe_fingerprint_sha256"] = probe_fingerprint(record)
    return record


def _load_json_object(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    path = Path(record_or_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        message = f"Could not load Hollywood2 author-license evidence: {exc}"
        raise BenchmarkIntegrityError(message) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError("Hollywood2 author-license evidence must be one JSON object.")
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(f"Hollywood2 author-license field {key!r} is missing.")
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(f"Hollywood2 author-license {label} drifted.")


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(f"Hollywood2 author-license must preserve {label}.")


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(f"Hollywood2 author-license must not promote {label}.")


def _validate_source(source: Mapping[str, Any]) -> None:
    _equal(source.get("institution"), "Technical University of Munich", "institution")
    _equal(source.get("document_type"), "doctoral_dissertation", "document type")
    _equal(source.get("author"), "Ioannis Agtzidis", "author")
    _equal(source.get("year"), 2020, "year")
    _equal(
        source.get("title"),
        "Towards a better understanding of eye movements in natural contexts",
        "title",
    )
    _equal(source.get("requested_url"), SOURCE_URL, "requested URL")
    _equal(source.get("final_url"), SOURCE_URL, "final URL")
    _equal(source.get("bytes"), PDF_BYTES, "PDF byte count")
    _equal(source.get("sha256"), PDF_SHA256, "PDF SHA-256")
    _equal(
        source.get("normalised_extracted_text_sha256"),
        EXTRACTED_TEXT_SHA256,
        "extracted-text SHA-256",
    )


def _validate_statement(statement: Mapping[str, Any]) -> None:
    _true(statement.get("chapter_4_hand_labeled_data_sets_present"), "Chapter 4 marker")
    _true(statement.get("open_source_license_statement_present"), "open-license statement")
    _true(statement.get("hollywood2_gin_footnote_present"), "Hollywood2EM GIN footnote")
    _equal(
        statement.get("statement_scope"),
        "all_data_presented_in_dissertation_chapter_4",
        "statement scope",
    )
    _equal(
        statement.get("hollywood2_repository_footnote_url"),
        HOLLYWOOD2_GIN_URL,
        "Hollywood2EM GIN footnote URL",
    )
    _true(
        statement.get("author_describes_chapter_data_as_publicly_available_with_open_source_license"),
        "author open-license description",
    )


def _validate_conservative_rights(rights: Mapping[str, Any]) -> None:
    _true(rights.get("general_open_license_indication_verified"), "general open-license indication")
    _false(rights.get("exact_license_identifier_recovered"), "exact license identifier recovery")
    _false(rights.get("exact_license_text_recovered"), "exact license-text recovery")
    _false(rights.get("repository_license_file_recovered"), "repository license-file recovery")
    _equal(rights.get("gin_analysis_use_terms_status"), "unresolved_exact_terms", "analysis terms")
    _equal(
        rights.get("gin_raw_data_redistribution_terms_status"),
        "unresolved_exact_terms",
        "redistribution terms",
    )


def _validate_boundary(boundary: Mapping[str, Any], *, frozen: bool) -> None:
    if frozen:
        _true(boundary.get("author_dissertation_statement_verified"), "verified author statement")
        _true(
            boundary.get("hollywood2_gin_repository_footnote_verified"),
            "verified Hollywood2EM repository footnote",
        )
    for key, label in (
        ("exact_gin_dataset_license_verified", "exact GIN dataset license"),
        ("gin_analysis_use_authorized", "GIN analysis authorization"),
        ("gin_raw_data_redistribution_authorized", "GIN redistribution authorization"),
        ("participant_identity_mapping_verified", "participant identity mapping"),
        ("source_audit_ready", "source-audit readiness"),
        ("cross_dataset_validation_created", "cross-dataset validation"),
        ("frozen_evidence_performance_claim_created", "Frozen Evidence performance claim"),
    ):
        _false(boundary.get(key), label)
    model_key = (
        "participant_disjoint_model_validation_created" if frozen else "model_validation_created"
    )
    _false(boundary.get(model_key), "model validation")


def validate_hollywood2_author_license_evidence(
    record_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Validate the frozen author-dissertation rights-context evidence."""
    record = _load_json_object(record_or_path)
    _equal(record.get("record_type"), EVIDENCE_RECORD_TYPE, "evidence record type")
    _equal(record.get("status"), EVIDENCE_STATUS, "evidence status")
    _equal(record.get("checked_on"), "2026-09-06", "review date")
    _validate_source(_mapping(record, "author_dissertation"))
    _validate_statement(_mapping(record, "observed_statement"))

    binding = _mapping(record, "canonical_repository_binding")
    _equal(binding.get("repository"), HOLLYWOOD2_GIN_REPOSITORY, "canonical repository")
    _equal(binding.get("commit_sha1"), GIN_COMMIT_SHA1, "canonical GIN commit")
    _equal(
        binding.get("authoritative_ground_truth_evidence_fingerprint_sha256"),
        GROUND_TRUTH_EVIDENCE_FINGERPRINT_SHA256,
        "ground-truth evidence fingerprint",
    )
    _equal(
        binding.get("underlying_source_rights_evidence_fingerprint_sha256"),
        UNDERLYING_RIGHTS_EVIDENCE_FINGERPRINT_SHA256,
        "underlying-rights evidence fingerprint",
    )

    rights = _mapping(record, "rights_interpretation")
    _validate_conservative_rights(rights)
    _false(rights.get("analysis_use_authorized"), "analysis-use authorization")
    _false(rights.get("raw_data_redistribution_authorized"), "raw-data redistribution")
    _false(rights.get("article_cc_by_is_dataset_license"), "article CC BY as dataset license")
    _false(
        rights.get("underlying_hollywood2_terms_automatically_apply"),
        "automatic underlying-license inheritance",
    )
    _false(rights.get("license_inference_permitted"), "license inference")
    _validate_boundary(_mapping(record, "scientific_boundary"), frozen=True)

    execution = _mapping(record, "execution")
    _equal(execution.get("live_probe_record_type"), LIVE_RECORD_TYPE, "live record type")
    _equal(
        execution.get("live_probe_fingerprint_sha256"),
        EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256,
        "live-probe fingerprint",
    )
    _equal(execution.get("workflow_run_id"), 34028659315, "workflow run ID")
    _equal(
        execution.get("probe_head_sha"),
        "630405aee028263a45cd5756fef61bec64d53c9a",
        "probe head SHA",
    )
    _equal(execution.get("artifact_id"), 9987884009, "artifact ID")
    _equal(
        execution.get("artifact_zip_sha256"),
        "78a641ae66321ef22bf64d6543d533c483ffd99420faa937a09988272fac59be",
        "artifact ZIP SHA-256",
    )

    stored = str(record.get("evidence_fingerprint_sha256", ""))
    if stored != evidence_fingerprint(record):
        raise BenchmarkIntegrityError(
            "Hollywood2 author-license evidence self-fingerprint is invalid."
        )
    if stored != EXPECTED_EVIDENCE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError("Hollywood2 author-license immutable v1 fingerprint drifted.")
    return record


def validate_hollywood2_author_license_live_probe(
    probe_or_path: Mapping[str, Any] | str | Path,
    evidence_or_path: Mapping[str, Any] | str | Path,
) -> dict[str, Any]:
    """Bind a fresh live dissertation probe to the frozen evidence record."""
    evidence = validate_hollywood2_author_license_evidence(evidence_or_path)
    probe = _load_json_object(probe_or_path)
    _equal(probe.get("record_type"), LIVE_RECORD_TYPE, "live record type")
    _equal(probe.get("status"), LIVE_STATUS, "live status")
    stored = str(probe.get("probe_fingerprint_sha256", ""))
    if stored != probe_fingerprint(probe):
        raise BenchmarkIntegrityError(
            "Hollywood2 author-license live-probe fingerprint is invalid."
        )
    if stored != EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256:
        raise BenchmarkIntegrityError(
            "Hollywood2 author dissertation bytes/text or markers drifted."
        )

    _validate_source(_mapping(probe, "source"))
    statement = _mapping(probe, "observed_statement")
    _validate_statement(statement)
    _true(statement.get("dissertation_title_present"), "dissertation title marker")
    _true(statement.get("author_present"), "author marker")
    _true(statement.get("gazecom_gin_footnote_present"), "GazeCom GIN footnote")
    _true(statement.get("hmd_gin_footnote_present"), "360/HMD GIN footnote")
    _validate_conservative_rights(_mapping(probe, "rights_interpretation"))
    probe_rights = _mapping(probe, "rights_interpretation")
    _false(
        probe_rights.get("license_inference_from_article_cc_by_permitted"),
        "article-license inference",
    )
    _false(
        probe_rights.get("license_inference_from_underlying_hollywood2_terms_permitted"),
        "underlying-license inference",
    )
    _validate_boundary(_mapping(probe, "scientific_boundary"), frozen=False)

    frozen_source = _mapping(evidence, "author_dissertation")
    _equal(
        _mapping(probe, "source").get("sha256"),
        frozen_source.get("sha256"),
        "live PDF binding",
    )
    _equal(
        _mapping(probe, "source").get("normalised_extracted_text_sha256"),
        frozen_source.get("normalised_extracted_text_sha256"),
        "live text binding",
    )
    return probe
