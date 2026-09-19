from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_grouping_clinic_keeps_units_and_model_selection_separate() -> None:
    page = _read("docs/grouping-repeated-measures.md")
    lower = page.lower()

    for phrase in (
        "observation row",
        "measurement unit",
        "inferential unit",
        "generalisation unit",
        "pseudoreplication",
        "nested versus crossed",
        "stimulus-as-fixed-effect limitation",
        "small variance does not erase the design",
        "does not choose a mixed-model specification",
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
        "api-reference.md#hierarchical-location-scale-models",
    ):
        assert target in page


def test_grouping_clinic_is_discoverable_without_hero_growth() -> None:
    for path in (
        "README.md",
        "mkdocs.yml",
        "docs/index.md",
        "docs/documentation-map.md",
        "docs/method-chooser.md",
        "docs/estimand-preregistration.md",
        "docs/analysis-handoff.md",
        "docs/missing-data-assumptions.md",
        "docs/model-diagnostics-convergence.md",
        "docs/inferential-reporting-audit.md",
        "docs/sensitivity-robustness-clinic.md",
        "docs/reporting-clinic.md",
        "docs/publication-readiness.md",
        "docs/learning-paths.md",
        "docs/for-researchers.md",
        "docs/artifact-dictionary.md",
        "docs/runnable-examples.md",
        "examples/README.md",
    ):
        assert "grouping-repeated-measures" in _read(path)

    gallery = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")
    homepage = _read("docs/index.md")
    assert "20_worked_grouping_pseudoreplication_audit.py" in gallery
    assert "20_worked_grouping_pseudoreplication_audit.py" in examples_readme
    assert "twenty-two deterministic examples" in gallery
    assert "The twenty-two examples" in examples_readme

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
