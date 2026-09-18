from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_reviewer_replication_guide_has_access_validity_and_api_boundaries() -> None:
    page = _read("docs/reviewer-replication.md")
    lower = page.lower()

    for phrase in (
        "reproducibility is not validity",
        "fully_rerunnable",
        "rerunnable_with_private_input",
        "inspectable_only",
        "claim → artifact → hash → api",
        "private data, licensing, and redistribution",
        "technical ability to copy a file is not permission to redistribute it",
        "matching hashes",
        "copy-ready archive statements",
        "synthetic_demo_not_empirical_evidence",
    ):
        assert phrase in lower

    for target in (
        "api-reference.md#schema",
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#dynamic-aois",
        "api-reference.md#scanpaths",
        "api-reference.md#visual-diagnostics",
        "api-reference.md#structural-validation-scope",
        "api-reference.md#sampling-sensitivity",
    ):
        assert target in page

    assert "14_worked_reviewer_replication_bundle.py" in page
    assert "artifact_hash_ledger.csv" in page
    assert "private/restricted empirical source data are **not bundled by default**" in lower


def test_reviewer_replication_route_is_integrated_without_hero_growth() -> None:
    paths = (
        "README.md",
        "mkdocs.yml",
        "docs/index.md",
        "docs/documentation-map.md",
        "docs/artifact-dictionary.md",
        "docs/reporting-clinic.md",
        "docs/measurement-interpretation.md",
        "docs/publication-readiness.md",
        "docs/reproducible-reporting.md",
        "docs/learning-paths.md",
        "docs/for-researchers.md",
        "docs/runnable-examples.md",
        "examples/README.md",
    )
    for path in paths:
        assert "reviewer-replication" in _read(path)

    runnable = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")
    learning = _read("docs/learning-paths.md")
    reporting = _read("docs/reporting-clinic.md")
    homepage = _read("docs/index.md")

    assert "14_worked_reviewer_replication_bundle.py" in runnable
    assert "14_worked_reviewer_replication_bundle.py" in examples_readme
    assert "sixteen deterministic examples" in runnable
    assert "sixteen deterministic examples/workflows" in learning
    assert 'aria-label="Eight-stage publication path"' in reporting

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
