from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_estimand_preregistration_clinic_has_required_scientific_contract() -> None:
    page = _read("docs/estimand-preregistration.md")
    lower = page.lower()

    for phrase in (
        "outcome, estimand, and model are different records",
        "primary / secondary / exploratory",
        "right-censored",
        "multiplicity family",
        "deviation ledger",
        "sensitivity analysis is not outcome shopping",
        "no model fit",
        "synthetic_demo_not_empirical_evidence",
        "does not establish construct validity",
    ):
        assert phrase in lower

    for target in (
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#scanpaths",
        "api-reference.md#sampling-sensitivity",
    ):
        assert target in page

    assert "13_worked_estimand_preregistration.py" in page
    assert "05_deviation_registry.csv" in page
    assert "estimator/model family unselected" not in lower
    assert "automatically" not in lower or "does not" in lower


def test_estimand_preregistration_route_is_integrated_without_hero_growth() -> None:
    paths = (
        "README.md",
        "mkdocs.yml",
        "docs/index.md",
        "docs/documentation-map.md",
        "docs/method-chooser.md",
        "docs/first-study-blueprint.md",
        "docs/study-design-templates.md",
        "docs/study-lifecycle.md",
        "docs/research-recipes.md",
        "docs/learning-paths.md",
        "docs/analysis-handoff.md",
        "docs/measurement-interpretation.md",
        "docs/reporting-clinic.md",
        "docs/publication-readiness.md",
        "docs/runnable-examples.md",
        "examples/README.md",
        "docs/artifact-dictionary.md",
    )
    for path in paths:
        assert "estimand-preregistration" in _read(path)

    runnable = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")
    learning = _read("docs/learning-paths.md")
    homepage = _read("docs/index.md")

    assert "13_worked_estimand_preregistration.py" in runnable
    assert "13_worked_estimand_preregistration.py" in examples_readme
    assert "twenty-two deterministic examples" in runnable
    assert "twenty-two deterministic examples/workflows" in learning

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
