"""Tests for fail-closed evidence-status generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gazeforge.benchmarks import benchmark_fingerprint
from gazeforge.evidence_status import (
    EvidenceState,
    build_evidence_status,
    render_evidence_status_json,
    render_evidence_status_markdown,
)
from gazeforge.exceptions import BenchmarkIntegrityError

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_test_status_fixture(root: Path, *, expected_name: str = "Fixture") -> Path:
    report_body = {
        "benchmark": {
            "name": "Fixture",
            "sampling_origin": "native",
            "split_unit": "participant_id",
        },
        "metrics": {"accuracy": 0.75},
        "model": {"name": "fixture-model"},
        "protocol": {"reviewed": True},
    }
    report = {
        **report_body,
        "report_fingerprint_sha256": benchmark_fingerprint(report_body),
    }
    source = root / "validation" / "evidence" / "fixture.json"
    _write_json(source, report)

    row = {
        "dataset": "Fixture dataset",
        "slug": "fixture",
        "state": "frozen_empirical_evidence",
        "summary": "Fixture reviewed evidence.",
        "scope": "test scope",
        "sampling_origin": "native",
        "reference_strength": "human-reference",
        "source_path": "validation/evidence/fixture.json",
        "git_blob_sha1": _git_blob_sha1(source.read_bytes()),
        "fingerprint_field": "report_fingerprint_sha256",
        "fingerprint": report["report_fingerprint_sha256"],
        "validator": "benchmark_report",
        "required_equals": {"benchmark.name": expected_name},
        "blockers": [],
    }
    body = {"schema_version": 1, "records": [row]}
    manifest = {
        **body,
        "manifest_fingerprint_sha256": benchmark_fingerprint(body),
    }
    manifest_path = root / "validation" / "evidence-status-manifest.json"
    _write_json(manifest_path, manifest)
    return source


def test_repository_evidence_status_matches_reviewed_boundaries() -> None:
    bundle = build_evidence_status(PROJECT_ROOT)
    records = {record.slug: record for record in bundle.records}

    assert records["lund2013"].state is EvidenceState.FROZEN_EMPIRICAL_EVIDENCE
    assert records["hollywood2"].state is EvidenceState.FROZEN_EMPIRICAL_EVIDENCE
    assert records["gaze-in-the-wild"].state is EvidenceState.REVIEWED_EMPIRICAL_EVIDENCE
    assert records["visus"].state is EvidenceState.BOUNDED_EMPIRICAL_EVIDENCE
    assert records["native-60hz-gp3"].state is EvidenceState.EMPIRICAL_EXECUTION_PENDING

    assert any("participant-held-out" in item for item in records["hollywood2"].blockers)
    assert any("task-stratified" in item for item in records["gaze-in-the-wild"].blockers)
    assert any("partial public derivative" in item for item in records["visus"].blockers)


def test_evidence_status_rendering_is_deterministic_and_self_describing() -> None:
    first = build_evidence_status(PROJECT_ROOT)
    second = build_evidence_status(PROJECT_ROOT)

    assert first.bundle_fingerprint_sha256 == second.bundle_fingerprint_sha256
    assert render_evidence_status_json(first) == render_evidence_status_json(second)

    markdown = render_evidence_status_markdown(first)
    assert "Frozen empirical evidence" in markdown
    assert "Reviewed empirical evidence" in markdown
    assert "Bounded empirical evidence" in markdown
    assert "Empirical execution pending" in markdown
    assert "Status is not inferred" in markdown


def test_changed_evidence_bytes_fail_closed(tmp_path: Path) -> None:
    source = _write_test_status_fixture(tmp_path)
    build_evidence_status(tmp_path)

    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["metrics"]["accuracy"] = 0.99
    _write_json(source, payload)

    with pytest.raises(BenchmarkIntegrityError, match="byte identity mismatch"):
        build_evidence_status(tmp_path)


def test_semantic_gate_mismatch_fails_closed(tmp_path: Path) -> None:
    _write_test_status_fixture(tmp_path, expected_name="Different reviewed dataset")

    with pytest.raises(BenchmarkIntegrityError, match="semantic gate failed"):
        build_evidence_status(tmp_path)


def test_manifest_tampering_fails_closed(tmp_path: Path) -> None:
    _write_test_status_fixture(tmp_path)
    manifest_path = tmp_path / "validation" / "evidence-status-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["records"][0]["state"] = "reviewed_empirical_evidence"
    _write_json(manifest_path, manifest)

    with pytest.raises(BenchmarkIntegrityError, match="manifest fingerprint mismatch"):
        build_evidence_status(tmp_path)


def test_policy_only_record_cannot_claim_an_artifact(tmp_path: Path) -> None:
    source = _write_test_status_fixture(tmp_path)
    manifest_path = tmp_path / "validation" / "evidence-status-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["records"][0]
    row["validator"] = "policy_only"
    body = {
        "schema_version": manifest["schema_version"],
        "records": manifest["records"],
    }
    manifest["manifest_fingerprint_sha256"] = benchmark_fingerprint(body)
    _write_json(manifest_path, manifest)
    assert source.is_file()

    with pytest.raises(BenchmarkIntegrityError, match="must not bind a source artifact"):
        build_evidence_status(tmp_path)
