"""Fail-closed validation for the frozen VISUS Osnabrueck derivative recovery."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .exceptions import BenchmarkIntegrityError
from .visus_authoritative_source_recheck import (
    EXPECTED_RECORD_FINGERPRINT_SHA256 as SOURCE_RECHECK_FINGERPRINT,
)
from .visus_authoritative_source_recheck import validate_visus_authoritative_source_recheck
from .visus_supplement_recovery_exhaustion import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256 as SUPPLEMENT_RECOVERY_FINGERPRINT,
)
from .visus_supplement_recovery_exhaustion import (
    validate_visus_supplement_recovery_exhaustion,
)

RECORD_TYPE = "visus-osnabrueck-derivative-recovery-evidence-v1"
STATUS = "reviewed-full-11-scenario-25-participant-institutional-usf-derivative-recovered"
EXPECTED_EVIDENCE_FINGERPRINT_SHA256 = (
    "78b538ad35e411fe9e7020d47c759d2d6d246c96887bf76da979e23f35335d32"
)

DEFAULT_SOURCE_RECHECK_PATH = Path(
    "validation/evidence/visus-source-recheck/"
    "visus-authoritative-source-recheck-2026-09-09.json"
)
DEFAULT_SUPPLEMENT_RECOVERY_PATH = Path(
    "validation/evidence/visus-source-recheck/"
    "visus-2021-supplement-recovery-exhaustion-evidence-v1.json"
)

_EXPECTED_SOURCE_BINDING = {
    "authoritative_source_recheck_record_fingerprint_sha256": SOURCE_RECHECK_FINGERPRINT,
    "supplement_recovery_exhaustion_evidence_fingerprint_sha256": SUPPLEMENT_RECOVERY_FINGERPRINT,
    "reconnaissance_branch": "research/visus-osnabrueck-derivative-probe",
    "reconnaissance_head_sha1": "f4d614f67e519a90aa8326f562fac2be9772e825",
    "workflow_name": "VISUS Osnabrueck derivative recovery probe",
    "workflow_run_id": 34504772669,
    "workflow_run_number": 6,
    "workflow_conclusion": "success",
    "artifact_id": 10163474159,
    "artifact_name": "visus-osnabrueck-derivative-probe",
    "artifact_digest_sha256": (
        "f4b40d146cc7cd17478da6bb2752ce7f80028f62bbf6356dd9ffc5ab6d048e76"
    ),
    "artifact_created_at_utc": "2026-09-10T16:56:17Z",
    "artifact_zip_size_bytes": 54901,
}

_EXPECTED_PROBE_BINDINGS = (
    (
        "visus_osnabrueck_all_usf_probe.json",
        851103,
        "bdeb16ed2efd74200f742e8909abdc42e4aa48dccfdbcc65780f0ab65e9da69c",
    ),
    (
        "visus_osnabrueck_derivative_probe.json",
        3797,
        "36f32482c1cfef4dc821a43a82d771d7860b039a028b06035d7b41b1ff2e3a88",
    ),
    (
        "visus_osnabrueck_k1_member_probe.json",
        91168,
        "4e5e57d0344b831e7aec17108d0b6a6267829cd8e204ffef185b19309c2ea16c",
    ),
    (
        "visus_osnabrueck_zip_directory_probe.json",
        12961,
        "6191c59fc746963ac7f8561964f893347e4402123cbd46d51ab5e2aa21738d61",
    ),
)

_EXPECTED_SCENARIOS = (
    (
        "K1",
        "01-car pursuit_usf.mkv",
        2,
        ("Red Car", "White Car"),
        "4176b6afa4ec9c8709aa2fc8fa798a7d87863dd51f386fd45b614b4d9c339b25",
    ),
    (
        "K2",
        "02-turning car_usf.mkv",
        1,
        ("Red Car",),
        "5660eb03f0782e621579e91b0aff5fcfbb09aed5786b6e06da65ba1bda54f619",
    ),
    (
        "K3",
        "03-dialog_usf.mkv",
        3,
        ("Left Face", "Right Face", "Shirt"),
        "9af0cc8d1885de1aa0c45d6687779fa0892286fb7871ce6c99141e891bd0668f",
    ),
    (
        "K4",
        "04-thimblerig_usf.mkv",
        3,
        ("Cup2", "Cup1", "Cup3"),
        "91ae5edc1213c1192630d24c9924277157ac488ccb4b84e92c8845f88db7c241",
    ),
    (
        "K5",
        "05-memory_usf.mkv",
        1,
        ("Cards",),
        "51e0d7d82bce5909ed7a6909b583c6c7447da939ac890995a53f049153853094",
    ),
    (
        "K6",
        "06-UNO_usf.mkv",
        4,
        ("Left Hand", "Right Hand", "Stack Covered", "Stack Uncovered"),
        "7dfbe52693acfe46f76f360a19e67d232f86e17c6e1ea4cfd695354224070736",
    ),
    (
        "K7",
        "07-kite_usf.mkv",
        2,
        ("Person", "Kite"),
        "48600d3f2aecf880a6b33807ead29b7cbf0304a7ae09b2d5c9a4851082f95d10",
    ),
    (
        "K8",
        "08-case exchange_usf.mkv",
        4,
        ("Persons", "Textbox", "Case", "Suspects"),
        "a1cb41da48d001dbfb904bc7d4565d67a3e1691b78280d1a80f029b144359a14",
    ),
    (
        "K9",
        "09-ball game_usf.mkv",
        5,
        ("Ball", "Player White", "Player Red1", "Player Red2", "Player Red3"),
        "943069068c93c18f3f36f546b5af40daa55a08861426e5bfb19837bbac7a2b1b",
    ),
    (
        "K10",
        "10-bag search_usf.mkv",
        6,
        ("Red Bag", "Yellow Bag", "Blue Bag", "Red-White Bag", "Personen", "Brown Bag"),
        "2d90ab718ba919e9cc1dba666bb6280666fe8cc4576bbcdadefd58899408fc56",
    ),
    (
        "K11",
        "11-person search_usf.mkv",
        3,
        ("Hooded", "Red Shirt and Hat", "Persons"),
        "0f72d1bd4df8b826a0edd9084ceaf8f37f1aac4fc91a9bd6ae2ccd75fc75bc76",
    ),
)

_FALSE_AUTHORITY_FIELDS = (
    "current_authoritative_original_visus_copy_recovered",
    "exact_original_visus_file_identity_proven",
    "original_visus_dataset_license_resolved",
    "analysis_use_rights_resolved",
    "raw_source_redistribution_rights_resolved",
    "legacy_insecure_tls_retrieval_is_authority_evidence",
    "annotation_identity_to_original_viper_xml_proven",
    "independent_annotation_streams_verified",
    "source_audit_stage_authorized",
    "human_human_validation_authorized",
    "model_human_validation_authorized",
    "cross_dataset_validation_authorized",
    "native_60hz_gp3_validity_authorized",
    "empirical_frozen_evidence_authorized",
    "raw_source_redistribution_authorized",
    "new_empirical_performance_claim_authorized",
)

_TRUE_DERIVATIVE_FIELDS = (
    "full_11_scenario_25_participant_derivative_structurally_recovered",
    "historical_institutional_derivative_distribution_recovered",
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def evidence_fingerprint(record: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 excluding the self-fingerprint field."""
    body = dict(record)
    body.pop("evidence_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def scenario_structural_fingerprint(row: Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 excluding a scenario's self-fingerprint."""
    body = dict(row)
    body.pop("scenario_structural_fingerprint_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _load(record_or_path: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(record_or_path, Mapping):
        return dict(record_or_path)
    try:
        payload = json.loads(Path(record_or_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrityError(
            f"Could not load VISUS Osnabrueck derivative evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkIntegrityError(
            "VISUS Osnabrueck derivative evidence must contain one JSON object."
        )
    return payload


def _mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise BenchmarkIntegrityError(
            f"VISUS Osnabrueck derivative field {key!r} must be an object."
        )
    return value


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise BenchmarkIntegrityError(
            f"VISUS Osnabrueck derivative {label} drifted."
        )


def _true(value: Any, label: str) -> None:
    if value is not True:
        raise BenchmarkIntegrityError(
            f"VISUS Osnabrueck derivative must preserve {label}."
        )


def _false(value: Any, label: str) -> None:
    if value is not False:
        raise BenchmarkIntegrityError(
            f"VISUS Osnabrueck derivative must not promote {label}."
        )


def _validate_prior_bindings(
    record: Mapping[str, Any],
    *,
    source_recheck_path: str | Path,
    supplement_recovery_path: str | Path,
) -> None:
    source = validate_visus_authoritative_source_recheck(source_recheck_path)
    _equal(
        source["record_fingerprint_sha256"],
        SOURCE_RECHECK_FINGERPRINT,
        "authoritative-source recheck fingerprint",
    )
    supplement = validate_visus_supplement_recovery_exhaustion(
        supplement_recovery_path,
        source_recheck_path=source_recheck_path,
    )
    _equal(
        supplement["evidence_fingerprint_sha256"],
        SUPPLEMENT_RECOVERY_FINGERPRINT,
        "supplement-recovery fingerprint",
    )
    _equal(dict(_mapping(record, "source_binding")), _EXPECTED_SOURCE_BINDING, "source binding")


def _validate_probe_bindings(record: Mapping[str, Any]) -> None:
    rows = record.get("probe_bindings")
    if not isinstance(rows, list):
        raise BenchmarkIntegrityError("VISUS Osnabrueck probe bindings must be a list.")
    observed: list[tuple[str, int, str]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise BenchmarkIntegrityError("VISUS Osnabrueck probe binding must be an object.")
        _equal(
            set(row),
            {"filename", "raw_file_bytes", "raw_file_sha256"},
            "probe-binding schema",
        )
        observed.append(
            (str(row["filename"]), int(row["raw_file_bytes"]), str(row["raw_file_sha256"]))
        )
    _equal(tuple(observed), _EXPECTED_PROBE_BINDINGS, "probe bindings")


def _validate_institutional_source(record: Mapping[str, Any]) -> None:
    source = _mapping(record, "institutional_derivative_source")
    _equal(
        source.get("source_page_url"),
        (
            "https://www.ikw.uni-osnabrueck.de/en/research_groups/computer_vision/"
            "research/interactive_3d_modelling/multimedia_container/wacv17.html"
        ),
        "source-page URL",
    )
    _equal(
        source.get("legacy_bundle_url"),
        "https://w3o.ikw.uni-osnabrueck.de/media/cv/mm_mkv/Kurzhals.zip",
        "legacy bundle URL",
    )
    _true(source.get("source_page_labels_kurzhals_dataset"), "Kurzhals dataset labeling")
    _equal(source.get("source_page_stated_video_count"), 11, "source-page video count")
    _true(
        source.get("source_page_states_converted_datasets_provided_for_research_purposes"),
        "the bounded research-purpose distribution statement",
    )
    _true(
        source.get("source_page_requires_converter_and_original_dataset_citation"),
        "the source-page citation requirement",
    )
    _false(
        source.get("research_purpose_statement_is_formal_dataset_license"),
        "the research-purpose statement as a formal dataset license",
    )
    _false(
        source.get("legacy_host_tls_verification_succeeded"),
        "successful TLS verification on the legacy host",
    )
    _true(source.get("legacy_host_insecure_tls_retrieval_used"), "recording insecure TLS retrieval")
    _true(source.get("archive_zip_magic_verified"), "ZIP magic verification")
    _equal(
        source.get("archive_last_modified_http"),
        "Wed, 03 Jan 2018 11:40:54 GMT",
        "archive Last-Modified header",
    )
    _equal(source.get("archive_remote_size_bytes"), 2598730485, "archive byte size")
    _equal(source.get("archive_entry_count"), 26, "archive entry count")
    _equal(
        dict(source.get("archive_compression_method_counts", {})),
        {"8": 26},
        "archive compression methods",
    )
    _equal(source.get("usf_mkv_count"), 13, "USF MKV count")
    _equal(source.get("ass_mkv_count"), 13, "ASS MKV count")
    _equal(source.get("standard_usf_member_count"), 11, "standard USF count")
    _equal(
        tuple(source.get("polygon_variant_usf_members", ())),
        ("01-car pursuit_poly_usf.mkv", "02-turning car_poly_usf.mkv"),
        "polygon USF members",
    )
    _equal(
        tuple(source.get("polygon_variant_ass_members", ())),
        ("01-car pursuit_poly_ass.mkv", "02-turning car_poly_ass.mkv"),
        "polygon ASS members",
    )
    _equal(source.get("standard_usf_compressed_bytes"), 1288160237, "standard USF compressed bytes")
    _equal(
        source.get("standard_usf_uncompressed_bytes"),
        1305649112,
        "standard USF uncompressed bytes",
    )


def _validate_conversion_method(record: Mapping[str, Any]) -> None:
    method = _mapping(record, "conversion_method_evidence")
    _equal(method.get("jemr_article_doi"), "10.16910/jemr.10.5.4", "JEMR DOI")
    _equal(
        method.get("jemr_article_title"),
        "Visual Analytics of Gaze Data with Standard Multimedia Players",
        "JEMR title",
    )
    _true(
        method.get("jemr_article_states_usf_encapsulates_complete_gaze_metadata_without_loss"),
        "the JEMR USF lossless statement",
    )
    _true(
        method.get("jemr_article_states_ass_carries_selected_metadata_only"),
        "the JEMR ASS limitation statement",
    )
    _true(
        method.get("jemr_article_states_converted_gaze_datasets_exist"),
        "the JEMR converted-dataset statement",
    )
    _equal(method.get("jemr_article_license"), "CC BY 4.0", "JEMR article license")
    _false(
        method.get("jemr_article_license_is_visus_derivative_dataset_license"),
        "the JEMR article license as a VISUS derivative license",
    )
    _false(
        method.get("converter_transform_fidelity_independently_proven_for_this_archive"),
        "independent transform-fidelity proof",
    )


def _validate_structural_recovery(record: Mapping[str, Any]) -> None:
    recovery = _mapping(record, "structural_recovery")
    _equal(recovery.get("scenario_count"), 11, "scenario count")
    _equal(recovery.get("participant_count_per_scenario"), 25, "participant count")
    _equal(
        tuple(recovery.get("expected_participant_numbers", ())),
        tuple(range(1, 26)),
        "participant-number roster",
    )
    _equal(
        dict(recovery.get("expected_task_group_counts", {})),
        {"A": 13, "B": 12},
        "A/B group counts",
    )
    for key in (
        "all_crc_valid",
        "all_ebml_valid",
        "all_have_exact_participants_1_to_25",
        "all_video_resolution_1920x1080",
        "all_video_avg_frame_rate_25fps",
        "all_participant_payloads_have_gaze_fixation_timestamp_point_terms",
    ):
        _true(recovery.get(key), key.replace("_", " "))

    rows = recovery.get("scenario_structures")
    if not isinstance(rows, list) or len(rows) != 11:
        raise BenchmarkIntegrityError(
            "VISUS Osnabrueck evidence must preserve eleven scenario structures."
        )
    compressed_total = 0
    uncompressed_total = 0
    for row, expected in zip(rows, _EXPECTED_SCENARIOS, strict=True):
        if not isinstance(row, Mapping):
            raise BenchmarkIntegrityError("VISUS Osnabrueck scenario structure must be an object.")
        scenario_id, member_name, aoi_count, aoi_titles, expected_fp = expected
        _equal(row.get("scenario_id"), scenario_id, f"{scenario_id} identity")
        _equal(row.get("member_name"), member_name, f"{scenario_id} member name")
        _true(row.get("crc_match"), f"{scenario_id} CRC match")
        _true(row.get("ebml_magic"), f"{scenario_id} EBML identity")
        _equal(row.get("participant_track_count"), 25, f"{scenario_id} participant count")
        _equal(
            tuple(row.get("participant_numbers", ())),
            tuple(range(1, 26)),
            f"{scenario_id} participant roster",
        )
        _equal(
            dict(row.get("task_group_counts", {})),
            {"A": 13, "B": 12},
            f"{scenario_id} A/B group counts",
        )
        _true(
            row.get("participant_payload_required_terms_all_present"),
            f"{scenario_id} gaze/fixation/timestamp/point terms",
        )
        _equal(row.get("aoi_track_count"), aoi_count, f"{scenario_id} AOI count")
        _equal(tuple(row.get("aoi_titles", ())), aoi_titles, f"{scenario_id} AOI titles")
        video = _mapping(row, "video")
        _equal(video.get("width"), 1920, f"{scenario_id} width")
        _equal(video.get("height"), 1080, f"{scenario_id} height")
        _equal(video.get("avg_frame_rate"), "25/1", f"{scenario_id} frame rate")
        claimed = str(row.get("scenario_structural_fingerprint_sha256", ""))
        _equal(claimed, expected_fp, f"{scenario_id} structural fingerprint")
        _equal(
            scenario_structural_fingerprint(row),
            expected_fp,
            f"{scenario_id} canonical structure",
        )
        compressed_total += int(row.get("compressed_size", -1))
        uncompressed_total += int(row.get("uncompressed_size", -1))
    _equal(compressed_total, 1288160237, "scenario compressed-byte sum")
    _equal(uncompressed_total, 1305649112, "scenario uncompressed-byte sum")


def _validate_authority_boundary(record: Mapping[str, Any]) -> None:
    boundary = _mapping(record, "authority_and_rights_boundary")
    _equal(
        set(boundary),
        set(_TRUE_DERIVATIVE_FIELDS) | set(_FALSE_AUTHORITY_FIELDS),
        "authority-boundary schema",
    )
    for key in _TRUE_DERIVATIVE_FIELDS:
        _true(boundary.get(key), key.replace("_", " "))
    for key in _FALSE_AUTHORITY_FIELDS:
        _false(boundary.get(key), key.replace("_", " "))


def validate_visus_osnabrueck_derivative_recovery(
    record_or_path: Mapping[str, Any] | str | Path,
    *,
    source_recheck_path: str | Path = DEFAULT_SOURCE_RECHECK_PATH,
    supplement_recovery_path: str | Path = DEFAULT_SUPPLEMENT_RECOVERY_PATH,
) -> dict[str, Any]:
    """Validate the immutable Osnabrueck VISUS derivative-recovery checkpoint.

    This validator intentionally separates structural recovery of a historical
    institutional derivative from authority over the original VISUS benchmark,
    formal reuse rights, and permission to create empirical Frozen Evidence.
    """
    record = _load(record_or_path)
    _equal(record.get("record_type"), RECORD_TYPE, "record type")
    _equal(record.get("checked_on"), "2026-09-10", "review date")
    _equal(record.get("status"), STATUS, "status")

    _validate_prior_bindings(
        record,
        source_recheck_path=source_recheck_path,
        supplement_recovery_path=supplement_recovery_path,
    )
    _validate_probe_bindings(record)
    _validate_institutional_source(record)
    _validate_conversion_method(record)
    _validate_structural_recovery(record)
    _validate_authority_boundary(record)

    requirements = record.get("remaining_resolution_requirements")
    if not isinstance(requirements, list) or len(requirements) != 5:
        raise BenchmarkIntegrityError(
            "VISUS Osnabrueck evidence must preserve five remaining resolution requirements."
        )
    if any(not isinstance(item, str) or not item.strip() for item in requirements):
        raise BenchmarkIntegrityError(
            "VISUS Osnabrueck resolution requirements must be non-empty strings."
        )

    limits = record.get("claim_limits")
    if not isinstance(limits, list) or len(limits) != 8:
        raise BenchmarkIntegrityError(
            "VISUS Osnabrueck evidence must preserve eight claim limits."
        )
    if any(not isinstance(item, str) or not item.strip() for item in limits):
        raise BenchmarkIntegrityError(
            "VISUS Osnabrueck claim limits must be non-empty strings."
        )

    claimed = str(record.get("evidence_fingerprint_sha256", ""))
    _equal(claimed, EXPECTED_EVIDENCE_FINGERPRINT_SHA256, "evidence fingerprint")
    _equal(
        evidence_fingerprint(record),
        EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
        "canonical evidence body",
    )
    return record
