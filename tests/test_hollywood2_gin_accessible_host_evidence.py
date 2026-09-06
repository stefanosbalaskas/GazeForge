import copy
import json
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.hollywood2_gin_accessible_host_evidence import (
    validate_hollywood2_gin_accessible_host_evidence,
    validate_hollywood2_gin_accessible_host_live_probe,
)
from gazeforge.hollywood2_gin_host_metadata import build_probe_record

EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-gin-host-metadata-accessible-evidence-v1.json"
)


def _fetch(body: bytes, *, url: str, status: int = 200, content_type: str = "application/json"):
    return {
        "requested_url": url,
        "final_url": url,
        "http_status": status,
        "content_type": content_type,
        "bytes": len(body),
        "sha256": "0" * 64,
        "body": body,
    }


def _datacite_zero(url: str) -> dict:
    body = json.dumps({"meta": {"total": 0}, "data": []}).encode()
    return _fetch(body, url=url)


def test_accessible_host_frozen_evidence_validates():
    record = validate_hollywood2_gin_accessible_host_evidence(EVIDENCE)
    assert record["rights_interpretation"]["gin_host_metadata_inspected"] is True
    assert record["rights_interpretation"]["exact_license_identifier_recovered"] is False
    assert record["scientific_boundary"]["source_audit_ready"] is False


def test_accessible_host_frozen_evidence_rejects_rights_promotion():
    record = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    record["rights_interpretation"]["analysis_use_authorized"] = True
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_accessible_host_evidence(record)


def test_fresh_accessible_host_without_license_terms_preserves_boundary():
    api_body = json.dumps(
        {
            "id": 834,
            "name": "hollywood2_em",
            "full_name": "ioannis.agtzidis/hollywood2_em",
            "private": False,
            "empty": False,
            "default_branch": "master",
        }
    ).encode()
    probe = build_probe_record(
        _fetch(api_body, url="https://gin.g-node.org/api/v1/repos/ioannis.agtzidis/hollywood2_em"),
        _fetch(
            b"<html>hollywood2_em</html>",
            url="https://gin.g-node.org/ioannis.agtzidis/hollywood2_em",
            content_type="text/html",
        ),
        [
            _datacite_zero("https://api.datacite.org/dois?query=hollywood2"),
            _datacite_zero("https://api.datacite.org/dois?query=hollywood2_em"),
            _datacite_zero("https://api.datacite.org/dois?query=ioannis.agtzidis"),
            _datacite_zero("https://api.datacite.org/dois?query=gin.g-node.org"),
        ],
    )
    validate_hollywood2_gin_accessible_host_live_probe(probe, EVIDENCE)


def test_fresh_accessible_host_license_key_fails_closed():
    api_body = json.dumps(
        {
            "id": 834,
            "name": "hollywood2_em",
            "full_name": "ioannis.agtzidis/hollywood2_em",
            "license": {"spdx_id": "MIT"},
        }
    ).encode()
    probe = build_probe_record(
        _fetch(api_body, url="https://gin.g-node.org/api/v1/repos/ioannis.agtzidis/hollywood2_em"),
        _fetch(
            b"<html>hollywood2_em</html>",
            url="https://gin.g-node.org/ioannis.agtzidis/hollywood2_em",
            content_type="text/html",
        ),
        [
            _datacite_zero("https://api.datacite.org/dois?query=hollywood2"),
            _datacite_zero("https://api.datacite.org/dois?query=hollywood2_em"),
            _datacite_zero("https://api.datacite.org/dois?query=ioannis.agtzidis"),
            _datacite_zero("https://api.datacite.org/dois?query=gin.g-node.org"),
        ],
    )
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_accessible_host_live_probe(probe, EVIDENCE)


def test_fresh_datacite_exact_repository_match_fails_closed():
    api_body = json.dumps(
        {
            "id": 834,
            "name": "hollywood2_em",
            "full_name": "ioannis.agtzidis/hollywood2_em",
        }
    ).encode()
    match_body = json.dumps(
        {
            "meta": {"total": 1},
            "data": [
                {
                    "id": "10.1234/example",
                    "attributes": {
                        "url": "https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"
                    },
                }
            ],
        }
    ).encode()
    zero = _datacite_zero("https://api.datacite.org/dois?query=zero")
    probe = build_probe_record(
        _fetch(api_body, url="https://gin.g-node.org/api/v1/repos/ioannis.agtzidis/hollywood2_em"),
        _fetch(
            b"<html>hollywood2_em</html>",
            url="https://gin.g-node.org/ioannis.agtzidis/hollywood2_em",
            content_type="text/html",
        ),
        [
            _fetch(match_body, url="https://api.datacite.org/dois?query=hollywood2"),
            copy.deepcopy(zero),
            copy.deepcopy(zero),
            copy.deepcopy(zero),
        ],
    )
    with pytest.raises(BenchmarkIntegrityError):
        validate_hollywood2_gin_accessible_host_live_probe(probe, EVIDENCE)


def test_fresh_403_transport_state_does_not_erase_reviewed_accessible_evidence():
    forbidden = _fetch(
        b"forbidden",
        url="https://gin.g-node.org/blocked",
        status=403,
        content_type="text/plain",
    )
    probe = build_probe_record(
        copy.deepcopy(forbidden),
        copy.deepcopy(forbidden),
        [
            _datacite_zero("https://api.datacite.org/dois?query=hollywood2"),
            _datacite_zero("https://api.datacite.org/dois?query=hollywood2_em"),
            _datacite_zero("https://api.datacite.org/dois?query=ioannis.agtzidis"),
            _datacite_zero("https://api.datacite.org/dois?query=gin.g-node.org"),
        ],
    )
    probe["api"]["sha256"] = "a" * 64
    probe["page"]["sha256"] = "a" * 64
    from gazeforge.hollywood2_gin_host_metadata import probe_fingerprint

    probe["probe_fingerprint_sha256"] = probe_fingerprint(probe)
    validate_hollywood2_gin_accessible_host_live_probe(probe, EVIDENCE)
