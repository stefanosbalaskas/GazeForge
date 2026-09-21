import json
import shutil
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.source_resolution_cli import main as source_resolution_main
from gazeforge.source_resolution_discovery import discover_source_resolution_paths
import gazeforge.source_resolution_lock as source_lock
from gazeforge.source_resolution_lock import (
    _fingerprint,
    _require_hex,
    _require_review_basis,
    _validated_lock_records,
    build_source_resolution_bundle_lock,
    load_source_resolution_bundle_lock,
    validate_source_resolution_bundle_lock,
)

ROOT = Path(__file__).parents[1]
PROTOCOLS = ROOT / "validation" / "protocols"
LOCK = ROOT / "validation" / "governance" / "source-resolution-bundle-lock-v1.json"
REVIEW_BASIS = [
    "Reviewed current source-resolution checkpoint set for VISUS, Hollywood2EM, and "
    "Gaze-in-the-Wild; Hollywood2EM references separately frozen empirical source "
    "evidence and Gaze-in-the-Wild now binds first-author processing provenance plus "
    "publication-level Supplementary Table 1 participant/task context while exact "
    "dataset copy, rights, distributed-file identity, complete trial-to-task mapping, "
    "and source-audit readiness remain unresolved.",
    "This governance lock snapshots checkpoint identities only; it does not authorize "
    "empirical evidence, rights, source-audit readiness, or Frozen Evidence publication.",
]


def test_builder_reproduces_committed_reviewed_lock():
    built = build_source_resolution_bundle_lock(
        PROTOCOLS,
        reviewed_on="2026-09-05",
        review_basis=REVIEW_BASIS,
    )
    committed = json.loads(LOCK.read_text(encoding="utf-8"))

    assert built == committed
    assert built["bundle_fingerprint_sha256"] == (
        "57064fea405e4a2e944bb066dd2dd7bff919ec12fb380d9cc1a8ba67d3bbbc5a"
    )
    assert built["lock_fingerprint_sha256"] == (
        "705fab1f67b564da5deef8c004822c424e714037ec4e0067831fad8cbee3e713"
    )
    assert built["scientific_boundary"]["non_empirical_governance_only"] is True
    assert built["scientific_boundary"]["authorizes_empirical_evidence"] is False


def test_committed_lock_validates_and_loads_typed_identity():
    summary = validate_source_resolution_bundle_lock(LOCK, PROTOCOLS)
    typed = load_source_resolution_bundle_lock(LOCK, PROTOCOLS)

    assert summary["matches_current_bundle"] is True
    assert summary["record_count"] == 3
    assert typed.record_count == 3
    assert typed.bundle_fingerprint_sha256 == summary["bundle_fingerprint_sha256"]
    assert typed.lock_fingerprint_sha256 == summary["lock_fingerprint_sha256"]
    records = {row["dataset_key"]: row for row in typed.records}
    assert set(records) == {"gaze-in-the-wild", "hollywood2em", "visus"}
    assert records["gaze-in-the-wild"]["record_fingerprint_sha256"] == (
        "22bbdef6e6f2823d10c84fd099596700d9db19c54aecfb76484c7625fd9ebb08"
    )
    assert records["hollywood2em"]["status"] == (
        "canonical_repository_and_ground_truth_recovered_terms_and_participant_"
        "mapping_unresolved"
    )


def test_lock_refuses_scientifically_valid_but_unreviewed_checkpoint_change(tmp_path):
    protocols = tmp_path / "protocols"
    protocols.mkdir()
    for source in discover_source_resolution_paths(PROTOCOLS):
        shutil.copy2(source, protocols / source.name)

    target = protocols / "visus-source-resolution-2026-09-04.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["claim_limits"][0] += " Reviewed wording changed."
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="changed since the reviewed lock"):
        validate_source_resolution_bundle_lock(LOCK, protocols)


def test_lock_refuses_weakened_scientific_boundary(tmp_path):
    payload = json.loads(LOCK.read_text(encoding="utf-8"))
    payload["scientific_boundary"]["authorizes_empirical_evidence"] = True
    altered = tmp_path / "lock.json"
    altered.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="scientific_boundary"):
        validate_source_resolution_bundle_lock(altered, PROTOCOLS)


def test_lock_is_governance_only_even_when_a_checkpoint_references_empirical_evidence():
    summary = validate_source_resolution_bundle_lock(LOCK, PROTOCOLS)
    payload = source_resolution_main

    assert summary["scientific_boundary"]["non_empirical_governance_only"] is True
    assert summary["scientific_boundary"]["authorizes_empirical_evidence"] is False
    assert callable(payload)


def test_cli_can_require_reviewed_bundle_lock(capsys):
    assert (
        source_resolution_main(
            ["--directory", str(PROTOCOLS), "--lock", str(LOCK)]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["validation_bundle"]["record_count"] == 3
    records = {
        row["dataset_key"]: row
        for row in payload["validation_bundle"]["records"]
    }
    assert records["hollywood2em"]["empirical_evidence_created"] is True
    assert payload["bundle_lock"]["matches_current_bundle"] is True
    assert payload["bundle_lock"]["scientific_boundary"]["authorizes_source_audit_ready"] is False


def test_cli_lock_requires_directory():
    checkpoint = PROTOCOLS / "visus-source-resolution-2026-09-04.json"
    with pytest.raises(SystemExit):
        source_resolution_main([str(checkpoint), "--lock", str(LOCK)])



def _write_lock(path: Path, payload: dict) -> Path:
    payload["lock_fingerprint_sha256"] = _fingerprint(payload)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _built_lock() -> dict:
    return build_source_resolution_bundle_lock(
        PROTOCOLS,
        reviewed_on="2026-09-05",
        review_basis=REVIEW_BASIS,
    )


def test_lock_hash_helper_normalizes_and_rejects_invalid_values():
    assert _require_hex("A" * 64, field="hash") == "a" * 64

    for value in ("abc", "g" * 64):
        with pytest.raises(BenchmarkIntegrityError, match="64 hexadecimal digits"):
            _require_hex(value, field="hash")


@pytest.mark.parametrize("value", [None, [], "review", [""]])
def test_lock_review_basis_rejects_missing_or_blank_entries(value):
    with pytest.raises(BenchmarkIntegrityError, match="review_basis"):
        _require_review_basis(value)


def test_lock_review_basis_strips_reviewed_entries():
    assert _require_review_basis([" reviewed ", " source audit "]) == (
        "reviewed",
        "source audit",
    )


@pytest.mark.parametrize("value", [None, [], "records"])
def test_lock_record_validation_requires_nonempty_list(value):
    with pytest.raises(BenchmarkIntegrityError, match="record identities"):
        _validated_lock_records(value)


def test_lock_record_validation_rejects_nonobject_missing_and_duplicate_rows():
    with pytest.raises(BenchmarkIntegrityError, match="JSON objects"):
        _validated_lock_records(["not-a-record"])

    with pytest.raises(BenchmarkIntegrityError, match="dataset_key and status"):
        _validated_lock_records(
            [
                {
                    "dataset_key": "visus",
                    "status": "",
                    "record_fingerprint_sha256": "a" * 64,
                }
            ]
        )

    duplicate = [
        {
            "dataset_key": "visus",
            "status": "review",
            "record_fingerprint_sha256": "a" * 64,
        },
        {
            "dataset_key": "visus",
            "status": "review",
            "record_fingerprint_sha256": "b" * 64,
        },
    ]
    with pytest.raises(BenchmarkIntegrityError, match="duplicate dataset identities"):
        _validated_lock_records(duplicate)


def test_lock_record_validation_sorts_and_normalizes_hashes():
    records = _validated_lock_records(
        [
            {
                "dataset_key": "visus",
                "status": "review",
                "record_fingerprint_sha256": "B" * 64,
            },
            {
                "dataset_key": "gaze-in-the-wild",
                "status": "pending",
                "record_fingerprint_sha256": "A" * 64,
            },
        ]
    )

    assert [row["dataset_key"] for row in records] == [
        "gaze-in-the-wild",
        "visus",
    ]
    assert records[0]["record_fingerprint_sha256"] == "a" * 64
    assert records[1]["record_fingerprint_sha256"] == "b" * 64


def test_lock_builder_rejects_invalid_date_and_review_basis():
    with pytest.raises(BenchmarkIntegrityError, match="ISO date"):
        build_source_resolution_bundle_lock(
            PROTOCOLS,
            reviewed_on="not-a-date",
            review_basis=REVIEW_BASIS,
        )

    for basis in ([], [""]):
        with pytest.raises(BenchmarkIntegrityError, match="review_basis cannot be empty"):
            build_source_resolution_bundle_lock(
                PROTOCOLS,
                reviewed_on="2026-09-05",
                review_basis=basis,
            )


def test_lock_validation_rejects_missing_invalid_and_nonobject_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_source_resolution_bundle_lock(tmp_path / "missing.json", PROTOCOLS)

    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff")
    with pytest.raises(BenchmarkIntegrityError, match="valid UTF-8 JSON"):
        validate_source_resolution_bundle_lock(invalid_utf8, PROTOCOLS)

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="valid UTF-8 JSON"):
        validate_source_resolution_bundle_lock(invalid_json, PROTOCOLS)

    array_json = tmp_path / "array.json"
    array_json.write_text("[]", encoding="utf-8")
    with pytest.raises(BenchmarkIntegrityError, match="must be a JSON object"):
        validate_source_resolution_bundle_lock(array_json, PROTOCOLS)


def test_lock_validation_rejects_metadata_contract_corruption(tmp_path):
    cases = [
        ("lock_type", "wrong", "lock_type"),
        ("reviewed_on", "bad-date", "ISO date"),
        ("review_basis", [], "review_basis"),
        ("scientific_boundary", {}, "scientific_boundary"),
        ("records", [], "record identities"),
        ("record_count", True, "positive integer"),
        ("record_count", 0, "positive integer"),
        ("bundle_fingerprint_sha256", "bad", "64 hexadecimal digits"),
        ("lock_fingerprint_sha256", "bad", "64 hexadecimal digits"),
    ]

    for index, (field, value, message) in enumerate(cases):
        payload = _built_lock()
        payload[field] = value
        path = tmp_path / f"invalid-{index}.json"
        if field == "lock_fingerprint_sha256":
            path.write_text(json.dumps(payload), encoding="utf-8")
        else:
            _write_lock(path, payload)
        with pytest.raises(BenchmarkIntegrityError, match=message):
            validate_source_resolution_bundle_lock(path, PROTOCOLS)


def test_lock_validation_rejects_declared_record_count_mismatch(tmp_path):
    payload = _built_lock()
    payload["record_count"] += 1
    path = _write_lock(tmp_path / "count.json", payload)

    with pytest.raises(BenchmarkIntegrityError, match="does not match its record identity list"):
        validate_source_resolution_bundle_lock(path, PROTOCOLS)


def test_lock_validation_rejects_content_fingerprint_mismatch(tmp_path):
    payload = _built_lock()
    payload["review_basis"].append("tampered after fingerprinting")
    path = tmp_path / "fingerprint.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="fingerprint does not match"):
        validate_source_resolution_bundle_lock(path, PROTOCOLS)


def test_lock_validation_rejects_current_bundle_count_and_record_drift(
    tmp_path,
    monkeypatch,
):
    payload = _built_lock()
    path = _write_lock(tmp_path / "lock.json", payload)
    original_bundle = source_lock.validate_source_resolution_directory(PROTOCOLS)

    count_drift = dict(original_bundle)
    count_drift["record_count"] = int(payload["record_count"]) + 1
    monkeypatch.setattr(
        source_lock,
        "validate_source_resolution_directory",
        lambda directory: count_drift,
    )
    with pytest.raises(BenchmarkIntegrityError, match="checkpoint count differs"):
        validate_source_resolution_bundle_lock(path, PROTOCOLS)

    record_drift = dict(original_bundle)
    record_drift["records"] = [dict(row) for row in original_bundle["records"]]
    record_drift["records"][0]["status"] = "reviewed-but-different"
    monkeypatch.setattr(
        source_lock,
        "validate_source_resolution_directory",
        lambda directory: record_drift,
    )
    with pytest.raises(BenchmarkIntegrityError, match="record identities differ"):
        validate_source_resolution_bundle_lock(path, PROTOCOLS)


def test_lock_validation_rejects_current_bundle_fingerprint_drift(
    tmp_path,
    monkeypatch,
):
    payload = _built_lock()
    path = _write_lock(tmp_path / "lock.json", payload)
    changed = source_lock.validate_source_resolution_directory(PROTOCOLS)
    changed = dict(changed)
    changed["bundle_fingerprint_sha256"] = "f" * 64
    monkeypatch.setattr(
        source_lock,
        "validate_source_resolution_directory",
        lambda directory: changed,
    )

    with pytest.raises(BenchmarkIntegrityError, match="changed since the reviewed lock"):
        validate_source_resolution_bundle_lock(path, PROTOCOLS)
