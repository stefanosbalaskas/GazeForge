import json
import shutil
from pathlib import Path

import pytest

from gazeforge.exceptions import BenchmarkIntegrityError
from gazeforge.source_resolution_dashboard import (
    build_source_resolution_dashboard,
    render_source_resolution_dashboard_markdown,
)
from gazeforge.source_resolution_discovery import discover_source_resolution_paths

_PROTOCOLS = Path("validation/protocols")
_LOCK = Path("validation/governance/source-resolution-bundle-lock-v1.json")


def test_source_resolution_dashboard_uses_complete_validated_repository_set():
    dashboard = build_source_resolution_dashboard(_PROTOCOLS, lock_path=_LOCK)

    assert len(dashboard.records) == 3
    assert [row["dataset_key"] for row in dashboard.rows] == [
        "gaze-in-the-wild",
        "hollywood2em",
        "visus",
    ]
    assert dashboard.source_files == (
        "gaze-in-wild-source-resolution-2026-09-04.json",
        "hollywood2-source-resolution-2026-09-05.json",
        "visus-source-resolution-2026-09-04.json",
    )
    assert dashboard.bundle_fingerprint_sha256 == (
        "6518614703d3ee99b54739365f0098d1a8df580e952cdcaecd33cdcaff49cebe"
    )
    assert dashboard.reviewed_snapshot is True
    assert dashboard.reviewed_on == "2026-09-05"
    assert dashboard.lock_fingerprint_sha256 == (
        "e18f0bd4a6a6dcc6f87de50751850546ea7c790c4312a944b091da1801941362"
    )
    assert dashboard.lock_source_file == str(_LOCK)
    rows = {row["dataset_key"]: row for row in dashboard.rows}
    assert all(row["source_audit_ready"] == "false" for row in rows.values())
    assert rows["hollywood2em"]["empirical_evidence_created"] == "true"
    assert rows["gaze-in-the-wild"]["empirical_evidence_created"] == "false"
    assert rows["visus"]["empirical_evidence_created"] == "false"
    assert all(row["analysis_use_terms_status"] == "unresolved" for row in rows.values())
    assert all(
        row["raw_data_redistribution_terms_status"] == "unresolved"
        for row in rows.values()
    )


def test_source_resolution_markdown_distinguishes_governance_from_evidence():
    dashboard = build_source_resolution_dashboard(_PROTOCOLS, lock_path=_LOCK)
    markdown = render_source_resolution_dashboard_markdown(dashboard)

    assert "# Source-resolution status" in markdown
    assert "Governance status, not performance evidence" in markdown
    assert "separately frozen empirical source evidence" in markdown
    assert "## Reviewed governance snapshot" in markdown
    assert "does **not**" in markdown
    assert "authorize source-status upgrades" in markdown
    assert "Frozen Evidence layer remains a separate" in markdown
    assert dashboard.bundle_fingerprint_sha256 in markdown
    assert dashboard.lock_fingerprint_sha256 in markdown
    for row in dashboard.rows:
        assert row["dataset"] in markdown
        assert row["record_fingerprint_sha256"][:12] in markdown


def test_dashboard_without_lock_remains_available_for_diagnostic_use():
    dashboard = build_source_resolution_dashboard(_PROTOCOLS)
    markdown = render_source_resolution_dashboard_markdown(dashboard)

    assert dashboard.reviewed_snapshot is False
    assert dashboard.reviewed_on is None
    assert dashboard.lock_fingerprint_sha256 is None
    assert "## Reviewed governance snapshot" not in markdown


def test_dashboard_refuses_checkpoint_drift_against_reviewed_lock(tmp_path):
    protocols = tmp_path / "protocols"
    protocols.mkdir()
    for source in discover_source_resolution_paths(_PROTOCOLS):
        shutil.copy2(source, protocols / source.name)

    target = protocols / "visus-source-resolution-2026-09-04.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["claim_limits"][0] += " Unreviewed public-status wording."
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BenchmarkIntegrityError, match="changed since the reviewed lock"):
        build_source_resolution_dashboard(protocols, lock_path=_LOCK)
