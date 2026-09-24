from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import gazeforge.hollywood2_gin_host_metadata as host
import gazeforge.hollywood2_rights_evidence as rights
from gazeforge.exceptions import BenchmarkIntegrityError

HOST_EVIDENCE = Path("validation/evidence/hollywood2/hollywood2-gin-host-metadata-evidence-v1.json")

RIGHTS_EVIDENCE = Path(
    "validation/evidence/hollywood2/hollywood2-underlying-source-rights-evidence-v1.json"
)


def _host_record():
    return json.loads(HOST_EVIDENCE.read_text(encoding="utf-8"))


def _rights_record():
    return json.loads(RIGHTS_EVIDENCE.read_text(encoding="utf-8"))


def _fetch(
    body: bytes,
    *,
    url: str,
    status: int = 200,
    content_type: str = "application/json",
    sha256: str = "0" * 64,
):
    return {
        "requested_url": url,
        "final_url": url,
        "http_status": status,
        "content_type": content_type,
        "bytes": len(body),
        "sha256": sha256,
        "body": body,
    }


def _zero_datacite(index: int):
    body = json.dumps(
        {
            "meta": {
                "total": 0,
            },
            "data": [],
        }
    ).encode("utf-8")

    return _fetch(
        body,
        url=f"https://example.invalid/datacite/{index}",
        status=200,
    )


def _bounded_host_probe():
    denial_sha = "1" * 64

    return host.build_probe_record(
        _fetch(
            b"forbidden",
            url="https://example.invalid/api",
            status=403,
            content_type="text/plain",
            sha256=denial_sha,
        ),
        _fetch(
            b"forbidden",
            url="https://example.invalid/page",
            status=403,
            content_type="text/html",
            sha256=denial_sha,
        ),
        [_zero_datacite(index) for index in range(4)],
    )


def _accessible_host_probe():
    api_body = json.dumps(
        {
            "id": 1,
            "name": "hollywood2_em",
            "full_name": ("ioannis.agtzidis/hollywood2_em"),
            "private": False,
            "default_branch": "master",
        }
    ).encode("utf-8")

    return host.build_probe_record(
        _fetch(
            api_body,
            url="https://example.invalid/api",
        ),
        _fetch(
            b"<html>Hollywood2_em</html>",
            url="https://example.invalid/page",
            content_type="text/html",
        ),
        [_zero_datacite(index) for index in range(4)],
    )


# ============================================================
# HOST METADATA BASIC HELPERS
# ============================================================


def test_host_sha256_bytes():
    assert host.sha256_bytes(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_host_canonical_bytes_deterministic():
    assert host.canonical_bytes(
        {
            "b": 2,
            "a": 1,
        }
    ) == host.canonical_bytes(
        {
            "a": 1,
            "b": 2,
        }
    )


def test_host_without_fingerprint():
    original = {
        "x": 1,
        "fp": "abc",
    }

    result = host._without_fingerprint(
        original,
        "fp",
    )

    assert result == {"x": 1}
    assert original["fp"] == "abc"


def test_host_probe_fp_ignores_stored():
    record = {
        "x": 1,
        "probe_fingerprint_sha256": "a",
    }

    first = host.probe_fingerprint(record)

    record["probe_fingerprint_sha256"] = "b"

    assert host.probe_fingerprint(record) == first


def test_host_evidence_fp_ignores_stored():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": "a",
    }

    first = host.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "b"

    assert host.evidence_fingerprint(record) == first


# ============================================================
# HOST LICENSE PATH WALKER
# ============================================================


def test_host_license_paths_nested():
    value = {
        "license": "MIT",
        "nested": {
            "licence_name": "BSD",
        },
        "items": [
            {
                "license_info": {
                    "name": "Apache",
                    "number": 2,
                }
            }
        ],
    }

    found = host._license_key_paths(value)

    paths = {item["path"] for item in found}

    assert "license" in paths
    assert "nested.licence_name" in paths
    assert "items[0].license_info" in paths


def test_host_license_paths_complex_value():
    value = {
        "license": [
            "MIT",
            "BSD",
        ]
    }

    found = host._license_key_paths(value)

    assert found == [
        {
            "path": "license",
            "value": "<list>",
        }
    ]


def test_host_license_paths_none():
    found = host._license_key_paths(
        {
            "license": None,
        }
    )

    assert found == [
        {
            "path": "license",
            "value": None,
        }
    ]


# ============================================================
# HOST REPOSITORY URL DETECTION
# ============================================================


@pytest.mark.parametrize(
    "value",
    [
        ("https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"),
        {"url": ("https://gin.g-node.org/ioannis.agtzidis/hollywood2_em/")},
        [{"nested": ("http://web.gin.g-node.org/ioannis.agtzidis/hollywood2_em")}],
    ],
)
def test_host_contains_repo_url_true(
    value,
):
    assert host._contains_repository_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "https://example.invalid",
        1,
        None,
        {"x": "nothing"},
        [
            "nothing",
            2,
        ],
    ],
)
def test_host_contains_repo_url_false(
    value,
):
    assert not host._contains_repository_url(value)


# ============================================================
# HOST API SUMMARY
# ============================================================


def test_host_summarize_api_bad_json():
    summary = host.summarize_api(
        _fetch(
            b"{",
            url="https://example.invalid/api",
        )
    )

    assert summary["json_object"] is False

    assert summary["license_key_paths"] == []


def test_host_summarize_api_nonobject():
    summary = host.summarize_api(
        _fetch(
            b"[]",
            url="https://example.invalid/api",
        )
    )

    assert summary["json_object"] is False


def test_host_summarize_api_selected_fields():
    body = json.dumps(
        {
            "id": 10,
            "name": "hollywood2_em",
            "full_name": "x/y",
            "description": "desc",
            "private": False,
            "archived": False,
            "empty": False,
            "default_branch": "master",
            "updated_at": "2026",
            "size": 10,
            "website": None,
            "ignored": [
                1,
                2,
            ],
            "license": {
                "key": "mit",
            },
        }
    ).encode()

    summary = host.summarize_api(
        _fetch(
            body,
            url="https://example.invalid/api",
        )
    )

    assert summary["json_object"] is True

    assert summary["id"] == 10

    assert summary["license_key_paths"][0]["path"] == "license"


def test_host_summarize_page_utf8():
    summary = host.summarize_page(
        _fetch(
            (b"<html>HOLLYWOOD2_EM License Licence</html>"),
            url="https://example.invalid/page",
            content_type="text/html",
        )
    )

    assert summary["contains_license_word"] is True

    assert summary["contains_licence_word"] is True

    assert summary["contains_repository_slug"] is True


def test_host_summarize_page_bad_utf8():
    summary = host.summarize_page(
        _fetch(
            b"\xff\xfe",
            url="https://example.invalid/page",
            content_type="text/html",
        )
    )

    assert not summary["contains_license_word"]

    assert not summary["contains_repository_slug"]


# ============================================================
# HOST DATACITE SUMMARY
# ============================================================


def test_host_summarize_datacite_bad_json():
    summary = host.summarize_datacite(
        _fetch(
            b"{",
            url="https://example.invalid/dc",
        )
    )

    assert summary["json_object"] is False

    assert summary["reported_total"] is None

    assert summary["returned_record_count"] == 0


def test_host_summarize_datacite_nonobject():
    summary = host.summarize_datacite(
        _fetch(
            b"[]",
            url="https://example.invalid/dc",
        )
    )

    assert summary["json_object"] is False

    assert summary["returned_record_count"] == 0


def test_host_summarize_datacite_bad_meta_data():
    body = json.dumps(
        {
            "meta": [],
            "data": {},
        }
    ).encode()

    summary = host.summarize_datacite(
        _fetch(
            body,
            url="https://example.invalid/dc",
        )
    )

    assert summary["reported_total"] is None

    assert summary["returned_record_count"] == 0


def test_host_summarize_datacite_skips_bad_rows():
    body = json.dumps(
        {
            "meta": {
                "total": 3,
            },
            "data": [
                "bad",
                {
                    "id": "x",
                    "attributes": "bad",
                },
                {
                    "id": "y",
                    "attributes": {"url": ("https://example.invalid")},
                },
            ],
        }
    ).encode()

    summary = host.summarize_datacite(
        _fetch(
            body,
            url="https://example.invalid/dc",
        )
    )

    assert summary["returned_record_count"] == 3

    assert summary["exact_repository_match_count"] == 0


def test_host_summarize_datacite_exact_match():
    body = json.dumps(
        {
            "meta": {
                "total": 1,
            },
            "data": [
                {
                    "id": "10.1/example",
                    "attributes": {
                        "doi": "10.1/example",
                        "url": ("https://gin.g-node.org/ioannis.agtzidis/hollywood2_em"),
                        "publisher": "Example",
                        "publicationYear": 2020,
                        "types": {"resourceType": "Dataset"},
                        "titles": [{"title": "Hollywood2"}],
                        "rightsList": [{"rights": "Example"}],
                        "ignored": object().__class__.__name__,
                    },
                }
            ],
        }
    ).encode()

    summary = host.summarize_datacite(
        _fetch(
            body,
            url="https://example.invalid/dc",
        )
    )

    assert summary["exact_repository_match_count"] == 1

    match = summary["exact_repository_matches"][0]

    assert match["id"] == "10.1/example"


# ============================================================
# HOST LICENSE VALUE HELPER
# ============================================================


@pytest.mark.parametrize(
    "paths",
    [
        [
            {
                "path": "license",
                "value": "MIT",
            }
        ],
        [
            {
                "path": "license",
                "value": {
                    "name": "MIT",
                },
            }
        ],
    ],
)
def test_host_nonempty_license_true(paths):
    assert host._nonempty_license_value(paths)


@pytest.mark.parametrize(
    "paths",
    [
        [],
        [
            {
                "path": "license",
                "value": "",
            }
        ],
        [
            {
                "path": "license",
                "value": {
                    "name": "",
                },
            }
        ],
        [
            {
                "path": "license",
                "value": None,
            }
        ],
    ],
)
def test_host_nonempty_license_false(paths):
    assert not host._nonempty_license_value(paths)


# ============================================================
# HOST BUILD PROBE
# ============================================================


def test_host_build_probe_denied():
    probe = _bounded_host_probe()

    assert probe["record_type"] == host.LIVE_RECORD_TYPE

    assert probe["rights_interpretation"]["host_api_metadata_accessible"] is False

    assert probe["rights_interpretation"]["analysis_use_authorized"] is False


def test_host_build_probe_accessible_no_license():
    probe = _accessible_host_probe()

    rights_boundary = probe["rights_interpretation"]

    assert rights_boundary["host_api_metadata_accessible"] is True

    assert rights_boundary["host_api_exposes_license_key"] is False


def test_host_build_probe_license_observation():
    api_body = json.dumps(
        {
            "license": {
                "key": "mit",
            }
        }
    ).encode()

    probe = host.build_probe_record(
        _fetch(
            api_body,
            url="https://example.invalid/api",
        ),
        _fetch(
            b"<html>license</html>",
            url="https://example.invalid/page",
            content_type="text/html",
        ),
    )

    boundary = probe["rights_interpretation"]

    assert boundary["host_api_exposes_license_key"]

    assert boundary["host_api_exposes_nonempty_license_value"]

    assert not boundary["exact_license_identifier_verified"]


# ============================================================
# HOST GENERIC VALIDATOR HELPERS
# ============================================================


def test_host_load_mapping_copy():
    original = {"x": 1}

    result = host._load_json_object(original)

    assert result == original
    assert result is not original


def test_host_load_missing(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        host._load_json_object(tmp_path / "missing.json")


def test_host_load_bad_json(tmp_path):
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        host._load_json_object(path)


def test_host_load_nonobject(tmp_path):
    path = tmp_path / "bad.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        host._load_json_object(path)


def test_host_mapping_missing():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        host._mapping(
            {},
            "missing",
        )


def test_host_equal_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        host._equal(
            1,
            2,
            "fixture",
        )


def test_host_true_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        host._true(
            False,
            "fixture",
        )


def test_host_false_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        host._false(
            True,
            "fixture",
        )


# ============================================================
# HOST FROZEN EVIDENCE
# ============================================================


def test_host_frozen_valid():
    record = host.validate_hollywood2_gin_host_metadata_evidence(HOST_EVIDENCE)

    assert record["evidence_fingerprint_sha256"] == host.EXPECTED_EVIDENCE_FINGERPRINT_SHA256


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "record_type",
            "bad",
            "record type",
        ),
        (
            "status",
            "bad",
            "evidence status",
        ),
        (
            "checked_on",
            "1900-01-01",
            "review date",
        ),
    ],
)
def test_host_frozen_identity(
    field,
    value,
    message,
):
    record = _host_record()
    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match=message,
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


def test_host_frozen_binding_missing():
    record = _host_record()
    record["canonical_repository_binding"] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "repository",
            "bad",
        ),
        (
            "commit_sha1",
            "0" * 40,
        ),
        (
            ("authoritative_ground_truth_evidence_fingerprint_sha256"),
            "0" * 64,
        ),
        (
            ("annotation_provenance_evidence_fingerprint_sha256"),
            "0" * 64,
        ),
        (
            ("gin_history_evidence_fingerprint_sha256"),
            "0" * 64,
        ),
        (
            ("underlying_source_rights_evidence_fingerprint_sha256"),
            "0" * 64,
        ),
        (
            ("author_license_statement_evidence_fingerprint_sha256"),
            "0" * 64,
        ),
    ],
)
def test_host_frozen_binding_drift(
    field,
    value,
):
    record = _host_record()

    record["canonical_repository_binding"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


@pytest.mark.parametrize(
    ("surface", "field", "value"),
    [
        (
            "gin_page",
            "http_status",
            200,
        ),
        (
            "gin_page",
            "bytes",
            1,
        ),
        (
            "gin_page",
            "sha256",
            "0" * 64,
        ),
        (
            "gin_page",
            "metadata_accessible",
            True,
        ),
        (
            "gin_api",
            "http_status",
            200,
        ),
        (
            "gin_api",
            "bytes",
            1,
        ),
        (
            "gin_api",
            "sha256",
            "0" * 64,
        ),
        (
            "gin_api",
            "metadata_accessible",
            True,
        ),
        (
            "gin_api",
            "json_object",
            True,
        ),
        (
            "gin_api",
            "license_key_paths",
            [
                {
                    "path": "license",
                    "value": "MIT",
                }
            ],
        ),
    ],
)
def test_host_frozen_surface_drift(
    surface,
    field,
    value,
):
    record = _host_record()

    record["live_observation"][surface][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


def test_host_frozen_surface_identity_flag():
    record = _host_record()

    record["live_observation"]["page_and_api_response_sha256_identical"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


@pytest.mark.parametrize(
    "queries",
    [
        None,
        [],
        [
            {},
        ],
    ],
)
def test_host_frozen_datacite_ledger_shape(
    queries,
):
    record = _host_record()

    record["live_observation"]["datacite_queries"] = queries

    with pytest.raises(
        BenchmarkIntegrityError,
        match="query ledger drifted",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


def test_host_frozen_datacite_row_type():
    record = _host_record()

    record["live_observation"]["datacite_queries"][0] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="row is invalid",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "query_label",
            "bad",
        ),
        (
            "reported_total",
            -1,
        ),
        (
            "returned_record_count",
            -1,
        ),
        (
            "exact_repository_match_count",
            1,
        ),
        (
            "response_sha256",
            "0" * 64,
        ),
    ],
)
def test_host_frozen_datacite_row_drift(
    field,
    value,
):
    record = _host_record()

    record["live_observation"]["datacite_queries"][0][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "gin_host_license_metadata_inspected",
        "host_metadata_license_absence_verified",
        "datacite_exact_repository_registration_recovered",
        "exact_license_identifier_recovered",
        "exact_license_text_recovered",
        "analysis_use_authorized",
        "raw_data_redistribution_authorized",
        "registry_zero_match_is_global_absence_claim",
    ],
)
def test_host_rights_false_boundaries(
    field,
):
    record = _host_record()

    record["rights_interpretation"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "gin_analysis_use_terms_status",
            "resolved",
        ),
        (
            ("gin_raw_data_redistribution_terms_status"),
            "resolved",
        ),
    ],
)
def test_host_rights_status_drift(
    field,
    value,
):
    record = _host_record()

    record["rights_interpretation"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


def test_host_clarification_requirement():
    record = _host_record()

    record["rights_interpretation"]["author_or_host_clarification_required_for_exact_terms"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "participant_identity_mapping_verified",
        "source_audit_ready",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "independent_human_human_agreement_created",
        "frozen_evidence_performance_claim_created",
    ],
)
def test_host_scientific_boundary(
    field,
):
    record = _host_record()

    record["scientific_boundary"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "live_probe_record_type",
            "bad",
        ),
        (
            "live_probe_fingerprint_sha256",
            "0" * 64,
        ),
        (
            "live_probe_json_sha256",
            "0" * 64,
        ),
        (
            "workflow_run_id",
            1,
        ),
        (
            "probe_head_sha",
            "0" * 40,
        ),
        (
            "artifact_id",
            1,
        ),
        (
            "artifact_zip_sha256",
            "0" * 64,
        ),
    ],
)
def test_host_execution_drift(
    field,
    value,
):
    record = _host_record()

    record["execution"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


def test_host_self_fingerprint():
    record = _host_record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


def test_host_immutable_fingerprint(
    monkeypatch,
):
    record = _host_record()

    record["evidence_fingerprint_sha256"] = "f" * 64

    monkeypatch.setattr(
        host,
        "evidence_fingerprint",
        lambda value: "f" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable v1 fingerprint",
    ):
        host.validate_hollywood2_gin_host_metadata_evidence(record)


# ============================================================
# HOST LIVE PROBE VALIDATOR
# ============================================================


def test_host_live_bounded_valid():
    probe = _bounded_host_probe()

    result = host.validate_hollywood2_gin_host_metadata_live_probe(
        probe,
        HOST_EVIDENCE,
    )

    assert result == probe


def test_host_live_accessible_valid():
    probe = _accessible_host_probe()

    result = host.validate_hollywood2_gin_host_metadata_live_probe(
        probe,
        HOST_EVIDENCE,
    )

    assert result == probe


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "record_type",
            "bad",
        ),
        (
            "status",
            "bad",
        ),
        (
            "repository",
            "bad",
        ),
    ],
)
def test_host_live_identity(
    field,
    value,
):
    probe = _bounded_host_probe()
    probe[field] = value

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


def test_host_live_bad_self_fingerprint():
    probe = _bounded_host_probe()

    probe["probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fingerprint is invalid",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


def test_host_live_api_mapping_missing():
    probe = _bounded_host_probe()
    probe["api"] = None

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


def test_host_live_denied_status_drift():
    probe = _bounded_host_probe()

    probe["api"]["http_status"] = 404

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


def test_host_live_denied_json_promotion():
    probe = _bounded_host_probe()

    probe["api"]["json_object"] = True

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


def test_host_live_denied_page_status():
    probe = _bounded_host_probe()

    probe["page"]["http_status"] = 200

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


def test_host_live_denied_identity_mismatch():
    probe = _bounded_host_probe()

    probe["page"]["sha256"] = "2" * 64

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="response identity",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


def test_host_live_accessible_license_key():
    probe = _accessible_host_probe()

    probe["api"]["license_key_paths"] = [
        {
            "path": "license",
            "value": "MIT",
        }
    ]

    probe["rights_interpretation"]["host_api_exposes_license_key"] = True

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="license key paths",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "contains_license_word",
        "contains_licence_word",
    ],
)
def test_host_live_accessible_page_keyword(
    field,
):
    probe = _accessible_host_probe()

    probe["page"][field] = True

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


@pytest.mark.parametrize(
    "queries",
    [
        [],
        None,
        [
            {},
        ],
    ],
)
def test_host_live_query_shape(queries):
    probe = _bounded_host_probe()
    probe["datacite_queries"] = queries

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fresh query ledger",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


def test_host_live_query_row_type():
    probe = _bounded_host_probe()

    probe["datacite_queries"][0] = "bad"

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="fresh DataCite row invalid",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "http_status",
            500,
        ),
        (
            "json_object",
            False,
        ),
        (
            "exact_repository_match_count",
            1,
        ),
    ],
)
def test_host_live_query_contract(
    field,
    value,
):
    probe = _bounded_host_probe()

    probe["datacite_queries"][0][field] = value

    if field == "exact_repository_match_count":
        probe["rights_interpretation"]["datacite_exact_repository_match_count"] = 1

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "host_api_exposes_license_key",
        "host_api_exposes_nonempty_license_value",
        "exact_license_identifier_verified",
        "analysis_use_authorized",
        "raw_data_redistribution_authorized",
        "license_inference_from_page_keyword_permitted",
        "registry_zero_match_is_global_absence_claim",
    ],
)
def test_host_live_rights_promotion(
    field,
):
    probe = _bounded_host_probe()

    probe["rights_interpretation"][field] = True

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "participant_identity_mapping_verified",
        "source_audit_ready",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "frozen_evidence_performance_claim_created",
    ],
)
def test_host_live_scientific_promotion(
    field,
):
    probe = _bounded_host_probe()

    probe["scientific_boundary"][field] = True

    probe["probe_fingerprint_sha256"] = host.probe_fingerprint(probe)

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        host.validate_hollywood2_gin_host_metadata_live_probe(
            probe,
            HOST_EVIDENCE,
        )


# ============================================================
# RIGHTS BASIC HELPERS
# ============================================================


def test_rights_canonical_bytes():
    assert rights._canonical_bytes(
        {
            "b": 2,
            "a": 1,
        }
    ) == rights._canonical_bytes(
        {
            "a": 1,
            "b": 2,
        }
    )


def test_rights_fingerprint_ignores_stored():
    record = {
        "x": 1,
        "evidence_fingerprint_sha256": "a",
    }

    first = rights.evidence_fingerprint(record)

    record["evidence_fingerprint_sha256"] = "b"

    assert rights.evidence_fingerprint(record) == first


def test_rights_probe_fp_ignores_stored():
    record = {
        "x": 1,
        "probe_fingerprint_sha256": "a",
    }

    first = rights._probe_fingerprint(record)

    record["probe_fingerprint_sha256"] = "b"

    assert rights._probe_fingerprint(record) == first


def test_rights_load_mapping_copy():
    original = {"x": 1}

    result, path = rights._load(original)

    assert result == original
    assert result is not original
    assert path is None


def test_rights_load_missing(tmp_path):
    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        rights._load(tmp_path / "missing.json")


def test_rights_load_bad_json(tmp_path):
    path = tmp_path / "bad.json"

    path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="Could not load",
    ):
        rights._load(path)


def test_rights_load_nonobject(tmp_path):
    path = tmp_path / "bad.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must be a JSON object",
    ):
        rights._load(path)


def test_rights_mapping_missing():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        rights._mapping(
            {},
            "missing",
        )


def test_rights_equal_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights._equal(
            1,
            2,
            "fixture",
        )


def test_rights_true_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        rights._true(
            False,
            "fixture",
        )


def test_rights_false_failure():
    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        rights._false(
            True,
            "fixture",
        )


# ============================================================
# RIGHTS FROZEN EVIDENCE
# ============================================================


def test_rights_frozen_valid():
    record = rights.validate_hollywood2_rights_evidence(RIGHTS_EVIDENCE)

    assert record["evidence_fingerprint_sha256"] == rights.EXPECTED_EVIDENCE_FINGERPRINT_SHA256


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "record_type",
            "bad",
        ),
        (
            "status",
            "bad",
        ),
        (
            "checked_on",
            "1900-01-01",
        ),
    ],
)
def test_rights_identity_drift(
    field,
    value,
):
    record = _rights_record()
    record[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        (
            "description_page",
            "requested_url",
            "bad",
        ),
        (
            "description_page",
            "final_url",
            "bad",
        ),
        (
            "description_page",
            "http_status",
            404,
        ),
        (
            "description_page",
            "bytes",
            1,
        ),
        (
            "description_page",
            "sha256",
            "0" * 64,
        ),
        (
            "description_page",
            "normalised_text_sha256",
            "0" * 64,
        ),
        (
            "licence_page",
            "requested_url",
            "bad",
        ),
        (
            "licence_page",
            "final_url",
            "bad",
        ),
        (
            "licence_page",
            "http_status",
            404,
        ),
        (
            "licence_page",
            "bytes",
            1,
        ),
        (
            "licence_page",
            "sha256",
            "0" * 64,
        ),
        (
            "licence_page",
            "normalised_text_sha256",
            "0" * 64,
        ),
        (
            "download_endpoint",
            "requested_url",
            "bad",
        ),
        (
            "download_endpoint",
            "published_archive_name",
            "bad",
        ),
        (
            "download_endpoint",
            "published_link_scheme",
            "https",
        ),
        (
            "download_endpoint",
            "final_url",
            "bad",
        ),
        (
            "download_endpoint",
            "final_scheme",
            "http",
        ),
        (
            "download_endpoint",
            "http_status",
            404,
        ),
        (
            "download_endpoint",
            "access_state",
            "downloaded",
        ),
    ],
)
def test_rights_page_identity_drift(
    section,
    field,
    value,
):
    record = _rights_record()

    record["institutional_source"][section][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "anonymous_direct_archive_access_verified",
        "authenticated_archive_access_tested",
        "full_corpus_downloaded",
    ],
)
def test_rights_download_promotion(
    field,
):
    record = _rights_record()

    record["institutional_source"]["download_endpoint"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "participant_count",
            15,
        ),
        (
            "active_participant_count",
            11,
        ),
        (
            "free_viewing_participant_count",
            5,
        ),
        (
            "sampling_rate_hz",
            120.0,
        ),
        (
            "eye_tracker",
            "other",
        ),
        (
            "display_resolution_pixels",
            [
                1920,
                1080,
            ],
        ),
        (
            "display_size_cm",
            [
                1,
                1,
            ],
        ),
        (
            "viewing_distance_cm",
            50.0,
        ),
    ],
)
def test_rights_recording_context(
    field,
    value,
):
    record = _rights_record()

    record["recording_context"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "academic_use_only",
        "limited_nonexclusive_nonassignable_nontransferable",
        "citation_of_mathe_sminchisescu_papers_required",
        "commercial_or_other_unpermitted_use_requires_prior_permission",
    ],
)
def test_rights_positive_rights_flags(
    field,
):
    record = _rights_record()

    record["underlying_rights"][field] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "standard_grant_allows_dataset_transfer",
        "article_cc_by_is_dataset_license",
    ],
)
def test_rights_negative_rights_flags(
    field,
):
    record = _rights_record()

    record["underlying_rights"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "analysis_use_terms_status",
            "unresolved",
        ),
        (
            "raw_archive_redistribution_status",
            "permitted",
        ),
        (
            "license_scope",
            "other",
        ),
    ],
)
def test_rights_underlying_statuses(
    field,
    value,
):
    record = _rights_record()

    record["underlying_rights"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "commit_sha1",
            "0" * 40,
        ),
        (
            "analysis_use_terms_status",
            "verified",
        ),
        (
            "raw_data_redistribution_terms_status",
            "verified",
        ),
    ],
)
def test_rights_annotation_status(
    field,
    value,
):
    record = _rights_record()

    record["annotation_repository_rights"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "repository_license_file_recovered",
        "dataset_specific_license_verified",
        "underlying_license_automatically_applies_to_annotation_repository",
        "article_cc_by_is_dataset_license",
        "license_inference_permitted",
    ],
)
def test_rights_annotation_promotion(
    field,
):
    record = _rights_record()

    record["annotation_repository_rights"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "published_participant_count",
            15,
        ),
        (
            "published_active_count",
            11,
        ),
        (
            "published_free_viewing_count",
            5,
        ),
        (
            "gin_file_subject_tokens",
            [
                "001",
            ],
        ),
        (
            "gin_file_subject_token_count",
            1,
        ),
    ],
)
def test_rights_participant_mapping_identity(
    field,
    value,
):
    record = _rights_record()

    record["participant_mapping"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_rights_evidence(record)


def test_rights_token_count_flag():
    record = _rights_record()

    record["participant_mapping"]["token_count_matches_published_participant_count"] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "file_subject_token_to_participant_mapping_verified",
        "participant_group_membership_by_file_token_verified",
        "mapping_inference_permitted",
    ],
)
def test_rights_mapping_promotions(
    field,
):
    record = _rights_record()

    record["participant_mapping"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "underlying_hollywood2_gaze_source_identified",
        "underlying_hollywood2_current_description_verified",
        "underlying_hollywood2_current_licence_verified",
        "underlying_hollywood2_download_endpoint_resolved",
        "underlying_hollywood2_current_rights_context_frozen",
        "underlying_hollywood2_standard_academic_analysis_use_verified",
        "underlying_hollywood2_standard_raw_archive_redistribution_not_permitted",
    ],
)
def test_rights_scientific_positive(
    field,
):
    record = _rights_record()

    record["scientific_boundary"][field] = False

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must preserve",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    "field",
    [
        "underlying_hollywood2_corpus_bytes_downloaded",
        "underlying_hollywood2_archive_manifest_verified",
        "gin_annotation_repository_license_verified",
        "gin_annotation_repository_redistribution_verified",
        "annotation_repository_rights_resolved",
        "file_subject_token_to_participant_mapping_verified",
        "participant_group_membership_by_file_token_verified",
        "participant_identity_mapping_verified",
        "model_validation_created",
        "participant_disjoint_model_validation_created",
        "cross_dataset_validation_created",
        "frozen_evidence_performance_claim_created",
    ],
)
def test_rights_scientific_negative(
    field,
):
    record = _rights_record()

    record["scientific_boundary"][field] = True

    with pytest.raises(
        BenchmarkIntegrityError,
        match="must not promote",
    ):
        rights.validate_hollywood2_rights_evidence(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "live_probe_record_type",
            "bad",
        ),
        (
            "live_probe_fingerprint_sha256",
            "0" * 64,
        ),
    ],
)
def test_rights_execution(
    field,
    value,
):
    record = _rights_record()

    record["execution"][field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_rights_evidence(record)


def test_rights_self_fingerprint():
    record = _rights_record()

    record["evidence_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        rights.validate_hollywood2_rights_evidence(record)


def test_rights_immutable_fingerprint(
    monkeypatch,
):
    record = _rights_record()

    record["evidence_fingerprint_sha256"] = "f" * 64

    monkeypatch.setattr(
        rights,
        "evidence_fingerprint",
        lambda value: "f" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="immutable v1 fingerprint",
    ):
        rights.validate_hollywood2_rights_evidence(record)


# ============================================================
# RIGHTS LIVE-PROBE BRANCH ISOLATION
# ============================================================


def _synthetic_rights_probe():
    evidence = _rights_record()

    return {
        "record_type": (rights.LIVE_RECORD_TYPE),
        "status": rights.LIVE_STATUS,
        "description_page": copy.deepcopy(evidence["institutional_source"]["description_page"]),
        "licence_page": copy.deepcopy(evidence["institutional_source"]["licence_page"]),
        "download_endpoint": copy.deepcopy(evidence["institutional_source"]["download_endpoint"]),
        "verified_recording_context": (copy.deepcopy(evidence["recording_context"])),
        "verified_underlying_rights": (copy.deepcopy(evidence["underlying_rights"])),
        "probe_fingerprint_sha256": (rights.EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256),
    }


def _force_rights_probe_fp(
    monkeypatch,
):
    monkeypatch.setattr(
        rights,
        "_probe_fingerprint",
        lambda value: rights.EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256,
    )


def test_rights_live_probe_valid(
    monkeypatch,
):
    _force_rights_probe_fp(monkeypatch)

    result = rights.validate_hollywood2_underlying_source_probe(
        _synthetic_rights_probe(),
        RIGHTS_EVIDENCE,
    )

    assert result["evidence_fingerprint_sha256"] == rights.EXPECTED_EVIDENCE_FINGERPRINT_SHA256


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "record_type",
            "bad",
        ),
        (
            "status",
            "bad",
        ),
    ],
)
def test_rights_live_identity(
    monkeypatch,
    field,
    value,
):
    _force_rights_probe_fp(monkeypatch)

    probe = _synthetic_rights_probe()
    probe[field] = value

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


def test_rights_live_self_fingerprint():
    probe = _synthetic_rights_probe()

    probe["probe_fingerprint_sha256"] = "0" * 64

    with pytest.raises(
        BenchmarkIntegrityError,
        match="self-fingerprint",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


def test_rights_live_expected_fingerprint(
    monkeypatch,
):
    probe = _synthetic_rights_probe()

    probe["probe_fingerprint_sha256"] = "f" * 64

    monkeypatch.setattr(
        rights,
        "_probe_fingerprint",
        lambda value: "f" * 64,
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="source or rights page drifted",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


@pytest.mark.parametrize(
    "section",
    [
        "description_page",
        "licence_page",
    ],
)
def test_rights_live_section_missing(
    monkeypatch,
    section,
):
    _force_rights_probe_fp(monkeypatch)

    probe = _synthetic_rights_probe()
    probe[section] = None

    with pytest.raises(
        BenchmarkIntegrityError,
        match="is missing",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "requested_url",
        "final_url",
        "http_status",
        "content_type",
        "bytes",
        "sha256",
        "normalised_text_sha256",
    ],
)
def test_rights_live_description_drift(
    monkeypatch,
    field,
):
    _force_rights_probe_fp(monkeypatch)

    probe = _synthetic_rights_probe()

    probe["description_page"][field] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "requested_url",
        "final_url",
        "http_status",
        "content_type",
        "bytes",
        "sha256",
        "normalised_text_sha256",
    ],
)
def test_rights_live_licence_drift(
    monkeypatch,
    field,
):
    _force_rights_probe_fp(monkeypatch)

    probe = _synthetic_rights_probe()

    probe["licence_page"][field] = "bad"

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "requested_url",
        "published_link_scheme",
        "final_url",
        "final_scheme",
        "transport_encrypted",
        "probe_method",
        "http_status",
        "content_type",
        "content_length",
        "content_range",
        "content_disposition",
        "accept_ranges",
        "sampled_bytes",
        "full_corpus_downloaded",
    ],
)
def test_rights_live_download_drift(
    monkeypatch,
    field,
):
    _force_rights_probe_fp(monkeypatch)

    probe = _synthetic_rights_probe()

    original = probe["download_endpoint"].get(field)

    probe["download_endpoint"][field] = (
        not original
        if isinstance(
            original,
            bool,
        )
        else "bad"
    )

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


def test_rights_live_recording_context(
    monkeypatch,
):
    _force_rights_probe_fp(monkeypatch)

    probe = _synthetic_rights_probe()

    probe["verified_recording_context"]["participant_count"] = 99

    with pytest.raises(
        BenchmarkIntegrityError,
        match="recording context",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


@pytest.mark.parametrize(
    "field",
    [
        "academic_use_only",
        "limited_nonexclusive_nonassignable_nontransferable",
        "standard_grant_allows_dataset_transfer",
        "citation_of_mathe_sminchisescu_papers_required",
        "commercial_or_other_unpermitted_use_requires_prior_permission",
    ],
)
def test_rights_live_rights_drift(
    monkeypatch,
    field,
):
    _force_rights_probe_fp(monkeypatch)

    probe = _synthetic_rights_probe()

    original = probe["verified_underlying_rights"][field]

    probe["verified_underlying_rights"][field] = not original

    with pytest.raises(
        BenchmarkIntegrityError,
        match="drifted",
    ):
        rights.validate_hollywood2_underlying_source_probe(
            probe,
            RIGHTS_EVIDENCE,
        )


# ============================================================
# RIGHTS TYPED LOADER
# ============================================================


def test_rights_typed_loader():
    result = rights.load_hollywood2_rights_evidence(RIGHTS_EVIDENCE)

    assert result.fingerprint_sha256 == rights.EXPECTED_EVIDENCE_FINGERPRINT_SHA256

    assert result.live_probe_fingerprint_sha256 == rights.EXPECTED_LIVE_PROBE_FINGERPRINT_SHA256

    assert result.participant_count == 16

    assert result.analysis_use_terms_status == "verified_academic_use_only"

    assert result.raw_archive_redistribution_status == ("not_permitted_under_standard_grant")
