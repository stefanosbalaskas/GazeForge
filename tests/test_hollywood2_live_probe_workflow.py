from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/hollywood2-gin-live-probe.yml"


def test_live_probe_is_scoped_to_material_hollywood2_changes() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    material_paths = (
        '      - "scripts/hollywood2_gin_live_probe.py"',
        '      - "scripts/hollywood2_gin_resilient_probe.py"',
        '      - "src/gazeforge/hollywood2_evidence.py"',
        '      - "src/gazeforge/hollywood2_coordinate_metadata.py"',
        '      - "src/gazeforge/hollywood2_coordinate_evidence.py"',
        '      - "src/gazeforge/source_resolution.py"',
        '      - "src/gazeforge/source_resolution_dashboard.py"',
        '      - "tests/test_hollywood2_evidence.py"',
        '      - "tests/test_hollywood2_gin_resilient_probe.py"',
        '      - "tests/test_hollywood2_source_resolution.py"',
        '      - "validation/evidence/hollywood2/**"',
        '      - "validation/protocols/hollywood2-source-resolution-*.json"',
        '      - "validation/history/source-resolution/hollywood2-source-resolution-*.json"',
        '      - "validation/governance/source-resolution-bundle-lock-v1.json"',
        '      - "docs/hollywood2-authoritative-evidence.md"',
        '      - "docs/hollywood2-source-resolution.md"',
    )
    for path in material_paths:
        assert path in workflow

    unrelated_paths = (
        '      - "tests/test_docs_hook.py"',
        '      - "docs/api-reference.md"',
        '      - ".github/workflows/ci.yml"',
        '      - ".github/workflows/docs.yml"',
        '      - ".github/workflows/hollywood2-gin-live-probe.yml"',
        '      - ".github/workflows/hollywood2-coordinate-metadata-probe.yml"',
    )
    for path in unrelated_paths:
        assert path not in workflow


def test_live_probe_keeps_manual_dispatch_and_fail_closed_behavior() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "  workflow_dispatch:" in workflow
    assert "for attempt in 1 2 3 4 5; do" in workflow
    assert 'delay=$((attempt * 20))' in workflow
    assert "Validate fail-closed availability record" in workflow
    assert 'assert record["status"] == "canonical_repository_route_unavailable"' in workflow
    assert 'boundary["scientific_reproduction_failure_inferred"] is False' in workflow
    assert "Upload deterministic probe record" in workflow
    assert "Fail closed when canonical GIN route is unavailable" in workflow
    assert 'if: steps.live_probe.outputs.exit_code != \'0\'' in workflow
    assert "exit 1" in workflow
