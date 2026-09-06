import json

from gazeforge.hollywood2_gin_host_metadata import build_probe_record


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
        _fetch(b"<html>Hollywood2_em</html>", url="https://example.test/repo", content_type="text/html"),
    )

    rights = record["rights_interpretation"]
    assert rights["host_api_exposes_license_key"] is False
    assert rights["host_api_exposes_nonempty_license_value"] is False
    assert rights["exact_license_identifier_verified"] is False


def test_non_json_api_response_is_retained_as_response_identity_only():
    record = build_probe_record(
        _fetch(b"forbidden", url="https://example.test/api", status=403, content_type="text/plain"),
        _fetch(b"<html>Hollywood2_em</html>", url="https://example.test/repo", content_type="text/html"),
    )

    assert record["api"]["json_object"] is False
    assert record["api"]["license_key_paths"] == []
    assert record["rights_interpretation"]["exact_license_identifier_verified"] is False
