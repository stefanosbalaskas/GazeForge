import json
import shutil
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.source_resolution_cli import main as source_resolution_main
from gazeforge.source_resolution_discovery import discover_source_resolution_paths
from gazeforge.source_resolution_lock import (
    build_source_resolution_bundle_lock,
    load_source_resolution_bundle_lock,
    validate_source_resolution_bundle_lock,
)

ROOT = Path(__file__).parents[1]
PROTOCOLS = ROOT / "validation" / "protocols"
LOCK = ROOT / "validation" / "governance" / "source-resolution-bundle-lock-v1.json"
REVIEW_BASIS = [
    "Reviewed unresolved source-resolution checkpoint set for VISUS, Hollywood2EM, and "
    "Gaze-in-the-Wild.",
    "Any checkpoint-content or evidence-state change requires intentional lock replacement and "
    "scientific review before merge.",
]


def test_builder_reproduces_committed_reviewed_lock():
    built = build_source_resolution_bundle_lock(
        PROTOCOLS,
        reviewed_on="2026-09-04",
        review_basis=REVIEW_BASIS,
    )
    committed = json.loads(LOCK.read_text(encoding="utf-8"))

    assert built == committed
    assert built["bundle_fingerprint_sha256"] == (
        "543bc47b29074049eb3f94a93a4ee952ccadc56b2d15347ff736da1f7127261c"
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
    assert {row["dataset_key"] for row in typed.records} == {
        "gaze-in-the-wild",
        "hollywood2em",
        "visus",
    }


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


def test_cli_can_require_reviewed_bundle_lock(capsys):
    assert (
        source_resolution_main(
            ["--directory", str(PROTOCOLS), "--lock", str(LOCK)]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["validation_bundle"]["record_count"] == 3
    assert payload["bundle_lock"]["matches_current_bundle"] is True
    assert payload["bundle_lock"]["scientific_boundary"]["authorizes_source_audit_ready"] is False


def test_cli_lock_requires_directory():
    checkpoint = PROTOCOLS / "visus-source-resolution-2026-09-04.json"
    with pytest.raises(SystemExit):
        source_resolution_main([str(checkpoint), "--lock", str(LOCK)])
