from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_missing_data_handoff_keeps_assumptions_and_treatments_explicit() -> None:
    page = _read("docs/missing-data-assumptions.md")
    lower = page.lower()

    for phrase in (
        "mcar, mar, and mnar are not software labels",
        "source/reason ≠ mechanism ≠ statistical treatment",
        "complete-case analysis is not neutral preprocessing",
        "imputation is not an automatic cleaning step",
        "not_selected_by_gazeforge",
        "synthetic_demo_not_empirical_evidence",
    ):
        assert phrase in lower

    for target in (
        "denominator-exposure-censoring.md",
        "analysis-handoff.md",
        "sensitivity-robustness-clinic.md",
        "api-reference.md#schema",
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#dynamic-aois",
        "api-reference.md#scanpaths",
        "api-reference.md#sampling-sensitivity",
    ):
        assert target in page


def test_missing_data_handoff_is_discoverable_without_hero_growth() -> None:
    for path in (
        "README.md",
        "mkdocs.yml",
        "docs/index.md",
        "docs/documentation-map.md",
        "docs/method-chooser.md",
        "docs/denominator-exposure-censoring.md",
        "docs/analysis-handoff.md",
        "docs/estimand-preregistration.md",
        "docs/sensitivity-robustness-clinic.md",
        "docs/reporting-clinic.md",
        "docs/publication-readiness.md",
        "docs/learning-paths.md",
        "docs/for-researchers.md",
        "docs/artifact-dictionary.md",
        "docs/runnable-examples.md",
        "examples/README.md",
    ):
        assert "missing-data-assumptions" in _read(path)

    gallery = _read("docs/runnable-examples.md")
    examples_readme = _read("examples/README.md")
    homepage = _read("docs/index.md")
    assert "18_worked_missing_data_assumptions_audit.py" in gallery
    assert "18_worked_missing_data_assumptions_audit.py" in examples_readme
    assert "twenty deterministic examples" in gallery
    assert "The twenty examples" in examples_readme

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
