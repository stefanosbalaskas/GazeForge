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
        "hollywood2-source-resolution-2026-09-04.json",
        "visus-source-resolution-2026-09-04.json",
    )
    assert len(dashboard.bundle_fingerprint_sha256) == 64
    assert dashboard.reviewed_snapshot is True
    assert dashboard.reviewed_on == "2026-09-04"
    assert dashboard.lock_fingerprint_sha256 == (
        "f68ad9d2ff7f4348049a9342c9d787f08dfc31e01d7507a6f3e0fcb2ca46528d"
    )
    assert dashboard.lock_source_file == str(_LOCK)
    assert all(row["source_audit_ready"] == "false" for row in dashboard.rows)
    assert all(row["empirical_evidence_created"] == "false" for row in dashboard.rows)
    assert all(row["analysis_use_terms_status"] == "unresolved" for row in dashboard.rows)
    assert all(
        row["raw_data_redistribution_terms_status"] == "unresolved"
        for row in dashboard.rows
    )


def test_source_resolution_markdown_is_explicitly_non_empirical_and_reviewed():
    dashboard = build_source_resolution_dashboard(_PROTOCOLS, lock_path=_LOCK)
    markdown = render_source_resolution_dashboard_markdown(dashboard)

    assert "# Source-resolution status" in markdown
    assert "Non-empirical governance status" in markdown
    assert "does **not** mean" in markdown
    assert "## Reviewed governance snapshot" in markdown
    assert "does **not**" in markdown
    assert "authorize a source-status upgrade" in markdown
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
