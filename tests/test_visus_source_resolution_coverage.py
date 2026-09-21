from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import gazeforge.visus_source_resolution as vsr
from gazeforge.exceptions import BenchmarkIntegrityError

RECORD = Path("validation/protocols/visus-source-resolution-2026-09-04.json")


def _payload() -> dict[str, Any]:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def _write(
    tmp_path: Path,
    payload: Any,
    *,
    name: str = "status.json",
) -> Path:
    path = tmp_path / name

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    return path


def _without_stored_fingerprint(
    payload: dict[str, Any],
) -> dict[str, Any]:
    payload.pop(
        "record_fingerprint_sha256",
        None,
    )

    return payload


def test_validate_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        vsr.validate_visus_source_resolution_record("definitely-missing-visus-status.json")


def test_validate_requires_json_object(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        [],
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        vsr.validate_visus_source_resolution_record(path)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "record_type",
            "wrong",
            "record_type",
        ),
        (
            "dataset",
            "wrong",
            "dataset",
        ),
        (
            "checked_on",
            "not-a-date",
            "ISO calendar date",
        ),
        (
            "status",
            "   ",
            "status cannot be empty",
        ),
    ],
)
def test_top_level_identity_guards(
    tmp_path: Path,
    field: str,
    value: Any,
    match: str,
) -> None:
    payload = _payload()
    payload[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=match,
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


@pytest.mark.parametrize(
    "field",
    [
        "empirical_evidence_created",
        "source_audit_ready",
        "current_authoritative_download_found",
    ],
)
def test_required_boolean_guards(
    tmp_path: Path,
    field: str,
) -> None:
    payload = _payload()
    payload[field] = "false"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be boolean",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_authoritative_publication_mapping_guard(
    tmp_path: Path,
) -> None:
    payload = _payload()

    payload["authoritative_publication"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_publication_doi_guard(
    tmp_path: Path,
) -> None:
    payload = _payload()

    payload["authoritative_publication"]["doi"] = "10.0000/wrong"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="publication DOI is unexpected",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_publication_dataset_license_claim_guard(
    tmp_path: Path,
) -> None:
    payload = _payload()

    payload["authoritative_publication"]["publication_states_dataset_license"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not be represented",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_rights_mapping_guard(
    tmp_path: Path,
) -> None:
    payload = _payload()

    payload["rights"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "analysis_use_terms_status",
            "unknown",
        ),
        (
            "raw_data_redistribution_terms_status",
            "unknown",
        ),
    ],
)
def test_rights_state_enum_guards(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    payload = _payload()

    payload["rights"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="rights statuses",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_rights_license_inference_guard(
    tmp_path: Path,
) -> None:
    payload = _payload()

    payload["rights"]["license_inference_permitted"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot infer a dataset license",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_annotation_mapping_guard(
    tmp_path: Path,
) -> None:
    payload = _payload()

    payload["annotation_independence"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be an object",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "independent_annotation_streams_verified",
            "false",
        ),
        (
            "human_human_agreement_ready",
            0,
        ),
    ],
)
def test_annotation_boolean_guards(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    payload = _payload()

    payload["annotation_independence"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="flags must be boolean",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


@pytest.mark.parametrize(
    "field",
    [
        "current_authoritative_download_found",
        "empirical_evidence_created",
    ],
)
def test_unresolved_distribution_promotion_guards(
    tmp_path: Path,
    field: str,
) -> None:
    payload = _payload()

    payload[field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="unresolved VISUS distribution",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


@pytest.mark.parametrize(
    "field",
    [
        "analysis_use_terms_status",
        "raw_data_redistribution_terms_status",
    ],
)
def test_unresolved_rights_must_remain_unresolved(
    tmp_path: Path,
    field: str,
) -> None:
    payload = _payload()

    payload["rights"][field] = "verified"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="separately unresolved",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_unresolved_independent_annotation_guard(
    tmp_path: Path,
) -> None:
    payload = _payload()

    payload["annotation_independence"]["independent_annotation_streams_verified"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot verify independent annotation streams",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_audit_ready_requires_current_authoritative_copy(
    tmp_path: Path,
) -> None:
    payload = _without_stored_fingerprint(_payload())

    payload["status"] = "authoritative_distribution_verified"

    payload["source_audit_ready"] = True

    payload["current_authoritative_download_found"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="requires a current authoritative copy",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_empirical_requires_source_audit_readiness(
    tmp_path: Path,
) -> None:
    payload = _without_stored_fingerprint(_payload())

    payload["status"] = "authoritative_distribution_verified"

    payload["current_authoritative_download_found"] = True

    payload["source_audit_ready"] = False

    payload["empirical_evidence_created"] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="cannot precede source-audit readiness",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


@pytest.mark.parametrize(
    "claim_limits",
    [
        None,
        [],
        [""],
        ["   "],
        [123],
        ["valid", ""],
    ],
)
def test_claim_limits_structure_guards(
    tmp_path: Path,
    claim_limits: Any,
) -> None:
    payload = _payload()

    payload["claim_limits"] = claim_limits

    with pytest.raises(
        BenchmarkIntegrityError,
        match="explicit non-empty claim limits",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "a" * 63,
        "g" * 64,
        "not-a-fingerprint",
    ],
)
def test_stored_fingerprint_format_guard(
    tmp_path: Path,
    stored: str,
) -> None:
    payload = _payload()

    payload["record_fingerprint_sha256"] = stored

    with pytest.raises(
        BenchmarkIntegrityError,
        match="64 hex digits",
    ):
        vsr.validate_visus_source_resolution_record(
            _write(
                tmp_path,
                payload,
            )
        )


def test_record_without_stored_fingerprint_is_valid(
    tmp_path: Path,
) -> None:
    payload = _without_stored_fingerprint(_payload())

    summary = vsr.validate_visus_source_resolution_record(
        _write(
            tmp_path,
            payload,
        )
    )

    assert len(summary["record_fingerprint_sha256"]) == 64


def test_verified_non_empirical_checkpoint_success(
    tmp_path: Path,
) -> None:
    payload = _without_stored_fingerprint(_payload())

    payload["status"] = "authoritative_distribution_verified"

    payload["current_authoritative_download_found"] = True

    payload["source_audit_ready"] = True

    payload["empirical_evidence_created"] = False

    payload["rights"]["analysis_use_terms_status"] = "verified"

    payload["rights"]["raw_data_redistribution_terms_status"] = "not_permitted"

    payload["annotation_independence"]["independent_annotation_streams_verified"] = True

    payload["annotation_independence"]["human_human_agreement_ready"] = True

    summary = vsr.validate_visus_source_resolution_record(
        _write(
            tmp_path,
            payload,
        )
    )

    assert summary["current_authoritative_download_found"] is True

    assert summary["source_audit_ready"] is True

    assert summary["empirical_evidence_created"] is False

    assert summary["rights"]["analysis_use_terms_status"] == "verified"

    assert summary["annotation_independence"]["human_human_agreement_ready"] is True


def test_fingerprint_helper_ignores_stored_fingerprint() -> None:
    payload = {
        "a": 1,
    }

    first = vsr._fingerprint(payload)

    payload["record_fingerprint_sha256"] = "0" * 64

    second = vsr._fingerprint(payload)

    assert first == second


def test_load_typed_record_from_generated_checkpoint(
    tmp_path: Path,
) -> None:
    payload = _without_stored_fingerprint(_payload())

    path = _write(
        tmp_path,
        payload,
    )

    typed = vsr.load_visus_source_resolution_record(path)

    assert typed.path == path
    assert typed.current_authoritative_download_found is False
    assert typed.source_audit_ready is False
    assert typed.empirical_evidence_created is False
    assert typed.analysis_use_terms_status == "unresolved"
    assert typed.raw_data_redistribution_terms_status == "unresolved"
    assert typed.independent_annotation_streams_verified is False
    assert typed.human_human_agreement_ready is False


def test_valid_stored_fingerprint_round_trip(
    tmp_path: Path,
) -> None:
    payload = _payload()

    payload["record_fingerprint_sha256"] = vsr._fingerprint(payload)

    path = _write(
        tmp_path,
        payload,
    )

    summary = vsr.validate_visus_source_resolution_record(path)

    assert summary["record_fingerprint_sha256"] == payload["record_fingerprint_sha256"]
