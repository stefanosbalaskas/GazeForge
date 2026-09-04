from pathlib import Path

from gazeforge.source_resolution_dashboard import (
    build_source_resolution_dashboard,
    render_source_resolution_dashboard_markdown,
)

_PROTOCOLS = Path("validation/protocols")


def test_source_resolution_dashboard_uses_complete_validated_repository_set():
    dashboard = build_source_resolution_dashboard(_PROTOCOLS)

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
    assert all(row["source_audit_ready"] == "false" for row in dashboard.rows)
    assert all(row["empirical_evidence_created"] == "false" for row in dashboard.rows)
    assert all(row["analysis_use_terms_status"] == "unresolved" for row in dashboard.rows)
    assert all(
        row["raw_data_redistribution_terms_status"] == "unresolved"
        for row in dashboard.rows
    )


def test_source_resolution_markdown_is_explicitly_non_empirical():
    dashboard = build_source_resolution_dashboard(_PROTOCOLS)
    markdown = render_source_resolution_dashboard_markdown(dashboard)

    assert "# Source-resolution status" in markdown
    assert "Non-empirical governance status" in markdown
    assert "does **not** mean" in markdown
    assert "Frozen Evidence layer remains a separate" in markdown
    assert dashboard.bundle_fingerprint_sha256 in markdown
    for row in dashboard.rows:
        assert row["dataset"] in markdown
        assert row["record_fingerprint_sha256"][:12] in markdown
