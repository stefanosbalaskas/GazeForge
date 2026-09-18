from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
FILES = {
    "first_party": WORKFLOWS / "gaze-in-wild-first-party-readiness.yml",
    "exact_copy": WORKFLOWS / "gaze-in-wild-exact-copy-review.yml",
    "figshare": WORKFLOWS / "gaze-in-wild-figshare-distribution-rights.yml",
}

EXPECTED_PATHS = {
    "first_party": {
        "src/gazeforge/gaze_in_wild_first_party_readiness.py",
        "tests/test_gaze_in_wild_first_party_readiness.py",
        "docs/gaze-in-wild-first-party-readiness.md",
        "validation/evidence/gaze-in-wild/**",
        ".github/workflows/gaze-in-wild-first-party-readiness.yml",
    },
    "exact_copy": {
        "src/gazeforge/gaze_in_wild_exact_copy_review.py",
        "src/gazeforge/gaze_in_wild_quarantine_exit.py",
        "tests/test_gaze_in_wild_exact_copy_review.py",
        "docs/gaze-in-wild-exact-copy-review.md",
        ".github/workflows/gaze-in-wild-exact-copy-review.yml",
    },
    "figshare": {
        "scripts/gaze_in_wild_figshare_live_probe.py",
        "src/gazeforge/gaze_in_wild_figshare_evidence.py",
        "tests/test_gaze_in_wild_figshare_evidence.py",
        (
            "validation/evidence/gaze-in-wild/"
            "gaze-in-wild-figshare-distribution-rights-evidence-v1.json"
        ),
        ".github/workflows/gaze-in-wild-figshare-distribution-rights.yml",
    },
}


def _load(path: Path) -> dict[str, object]:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_focused_giw_workflows_do_not_fan_out_on_generic_mkdocs_changes() -> None:
    for path in FILES.values():
        payload = _load(path)
        triggers = payload["on"]
        for event in ("push", "pull_request"):
            assert "mkdocs.yml" not in triggers[event]["paths"]


def test_focused_giw_workflows_supersede_stale_runs_per_pr_or_ref() -> None:
    expected_group = (
        "${{ github.workflow }}-"
        "${{ github.event.pull_request.number || github.ref }}"
    )
    for path in FILES.values():
        payload = _load(path)
        concurrency = payload["concurrency"]
        assert concurrency["group"] == expected_group
        assert concurrency["cancel-in-progress"] == "true"
        assert "workflow_dispatch" in payload["on"]


def test_material_giw_paths_and_fail_closed_jobs_remain_present() -> None:
    for key, path in FILES.items():
        payload = _load(path)
        triggers = payload["on"]
        for event in ("push", "pull_request"):
            assert EXPECTED_PATHS[key] <= set(triggers[event]["paths"])

    first = FILES["first_party"].read_text(encoding="utf-8")
    exact = FILES["exact_copy"].read_text(encoding="utf-8")
    figshare = FILES["figshare"].read_text(encoding="utf-8")
    assert "pytest -q tests/test_gaze_in_wild_first_party_readiness.py" in first
    assert "tests/test_gaze_in_wild_quarantine_exit.py" in exact
    assert "validate_gaze_in_wild_figshare_evidence" in figshare
    assert "gaze_in_wild_figshare_live_probe.py" in figshare
