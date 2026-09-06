import json
from copy import deepcopy
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_gin_host_metadata import (
    EXPECTED_EVIDENCE_FINGERPRINT_SHA256,
    build_probe_record,
    probe_fingerprint,
    validate_hollywood2_gin_host_metadata_evidence,
    validate_hollywood2_gin_host_metadata_live_probe,
)

EVIDENCE_PATH = Path(
    "validation/evidence/hollywood2/hollywood2-gin-host-metadata-evidence-v1.json"
)


def _fetch(
    body: bytes,
    *,
    url: str,
    status: int = 200,
    content_type: str = "application/json",
):
    return {
        "requested_url": url,
        "final_url": url,
        "http_status": status,
        "content_type": content_type,
        "bytes": len(body),
        "sha256": "0" * 64,
        "body": body,
    }


def _empty_datacite(url: str):
    body = json.dumps({"meta": {"total": 0}, "data": []}).encode()
    return _fetch(body, url=url)


def _fresh_bounded_probe():
    return build_probe_record(
        _fetch(b"forbidden", url="https://example.test/api", status=403),
        _fetch(
            b"forbidden",
            url="https://example.test/repo",
            status=403,
            content_type="text/html",
        ),
        [
            _empty_datacite("https://api.datacite.org/dois?query=hollywood2"),
            _empty_datacite("https://api.datacite.org/dois?query=hollywood2_em"),
            _empty_datacite("https://api.datacite.org/dois?query=ioannis.agtzidis"),
            _empty_datacite("https://api.datacite.org/dois?query=exact_repository_fragment"),
        ],
    )


def test_host_metadata_never_promotes_api_license_without_review():
    api_body = json.dumps(
        {
            "id": 1,
            "name": "hollywood2_em",
            "full_name": "ioannis.agtzidis/hollywood2_em",
            "private": False,
            "default_branch": "master",
            "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT"},
        }
    ).encode()
    record = build_probe_record(
        _fetch(api_body, url="https://example.test/api"),
        _fetch(
            b"<html>Hollywood2_em license</html>",
            url="https://example.test/repo",
            content_type="text/html",
        ),
    )

    rights = record["rights_interpretation"]
    boundary = record["scientific_boundary"]
    assert rights["host_api_exposes_license_key"] is True
    assert rights["host_api_exposes_nonempty_license_value"] is True
    assert rights["exact_license_identifier_verified"] is False
    assert rights["analysis_use_authorized"] is False
    assert rights["raw_data_redistribution_authorized"] is False
    assert boundary["source_audit_ready"] is False


def test_host_metadata_records_absent_license_field_without_inference():
    api_body = json.dumps(
        {
            "id": 1,
            "name": "hollywood2_em",
            "full_name": "ioannis.agtzidis/hollywood2_em",
            "private": False,
            "default_branch": "master",
        }
    ).encode()
    record = build_probe_record(
        _fetch(api_body, url="https://example.test/api"),
        _fetch(
            b"<html>Hollywood2_em</html>",
            url="https://example.test/repo",
            content_type="text/html",
        ),
    )

    rights = record["rights_interpretation"]
    assert rights["host_api_exposes_license_key"] is False
    assert rights["host_api_exposes_nonempty_license_value"] is False
    assert rights["exact_license_identifier_verified"] is False


def test_non_json_api_response_is_retained_as_response_identity_only():
    record = build_probe_record(
        _fetch(
            b"forbidden",
            url="https://example.test/api",
            status=403,
            content_type="text/plain",
        ),
        _fetch(
            b"<html>Hollywood2_em</html>",
            url="https://example.test/repo",
            content_type="text/html",
        ),
    )

    assert record["api"]["json_object"] is False
    assert record["api"]["license_key_paths"] == []
    assert record["rights_interpretation"]["exact_license_identifier_verified"] is False


def test_datacite_exact_repository_match_is_observed_but_not_auto_authorized():
    datacite_body = json.dumps(
        {
            "meta": {"total": 1},
            "data": [
                {
                    "id": "10.1234/example",
                    "attributes": {
                        "doi": "10.1234/example",
                        "url": "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em",
                        "publisher": "Example",
                        "publicationYear": 2020,
                        "titles": [{"title": "Hollywood2EM"}],
                        "rightsList": [
                            {"rights": "MIT License", "rightsIdentifier": "MIT"}
                        ],
                    },
                }
            ],
        }
    ).encode()
    record = build_probe_record(
        _fetch(b"forbidden", url="https://example.test/api", status=403),
        _fetch(b"forbidden", url="https://example.test/repo", status=403),
        [_fetch(datacite_body, url="https://api.datacite.org/dois?query=hollywood2")],
    )

    registry = record["datacite_queries"][0]
    rights = record["rights_interpretation"]
    assert registry["exact_repository_match_count"] == 1
    assert registry["exact_repository_matches"][0]["id"] == "10.1234/example"
    assert rights["datacite_exact_repository_match_count"] == 1
    assert rights["exact_license_identifier_verified"] is False
    assert rights["analysis_use_authorized"] is False
    assert rights["raw_data_redistribution_authorized"] is False


def test_zero_datacite_match_never_becomes_global_absence_claim():
    datacite_body = json.dumps({"meta": {"total": 0}, "data": []}).encode()
    record = build_probe_record(
        _fetch(b"forbidden", url="https://example.test/api", status=403),
        _fetch(b"forbidden", url="https://example.test/repo", status=403),
        [_fetch(datacite_body, url="https://api.datacite.org/dois?query=hollywood2")],
    )

    rights = record["rights_interpretation"]
    assert rights["datacite_exact_repository_match_count"] == 0
    assert rights["registry_zero_match_is_global_absence_claim"] is False
    assert rights["exact_license_identifier_verified"] is False


def test_frozen_host_metadata_evidence_validates_exactly():
    record = validate_hollywood2_gin_host_metadata_evidence(EVIDENCE_PATH)
    assert record["evidence_fingerprint_sha256"] == EXPECTED_EVIDENCE_FINGERPRINT_SHA256
    assert record["rights_interpretation"]["host_metadata_license_absence_verified"] is False
    assert record["rights_interpretation"]["analysis_use_authorized"] is False
    assert record["scientific_boundary"]["source_audit_ready"] is False


def test_frozen_evidence_rejects_permission_promotion():
    record = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    tampered = deepcopy(record)
    tampered["rights_interpretation"]["analysis_use_authorized"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_host_metadata_evidence(tampered)


def test_fresh_bounded_probe_binds_semantically_to_frozen_evidence():
    probe = _fresh_bounded_probe()
    validated = validate_hollywood2_gin_host_metadata_live_probe(probe, EVIDENCE_PATH)
    assert validated["rights_interpretation"]["datacite_exact_repository_match_count"] == 0


def test_fresh_probe_rejects_new_exact_datacite_repository_match():
    probe = _fresh_bounded_probe()
    probe["datacite_queries"][0]["exact_repository_match_count"] = 1
    probe["rights_interpretation"]["datacite_exact_repository_match_count"] = 1
    probe["probe_fingerprint_sha256"] = probe_fingerprint(probe)
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_host_metadata_live_probe(probe, EVIDENCE_PATH)
