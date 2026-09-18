from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _help_targets(text: str) -> list[str]:
    block = re.search(
        r'<nav class="gf-help[^"]*"[^>]*>(.*?)</nav>',
        text,
        flags=re.DOTALL,
    )
    assert block is not None
    return re.findall(r'href="([^"]+)"', block.group(1))


def test_documentation_map_routes_research_tasks_to_real_pages() -> None:
    page = _read("docs/documentation-map.md")
    required = (
        "gazeforge-tour.md",
        "first-study-blueprint.md",
        "method-chooser.md",
        "artifact-dictionary.md",
        "research-evidence-bundle.md",
        "reporting-clinic.md",
        "measurement-interpretation.md",
        "estimand-preregistration.md",
        "getting-started.md",
        "worked-tracker-import.md",
        "tutorial-synthetic-qc.md",
        "qc-review-exclusion-ledger.md",
        "tutorial-ivt-baseline.md",
        "event-model-validation-clinic.md",
        "worked-dynamic-aoi-study.md",
        "practical-workflow.md",
        "study-lifecycle.md",
        "publication-readiness.md",
        "evidence-status.md",
    )
    for target in required:
        assert target in page
        assert (DOCS / target).is_file()

    assert "How-to router" in page
    assert "tutorials" in page
    assert "how-to guides" in page
    assert "explanations" in page
    assert "reference" in page
    assert "Stop rather than guess" in page
    assert "synthetic demo ≠ empirical validation" in page
    assert "adapter compatibility ≠ device validity" in page
    assert "flag ≠ invalid sample" in page
    assert "no silent extrapolation" in page
    assert "Plan a first study" in page


def test_consistent_help_order_is_present_on_entry_pages() -> None:
    expected = [
        "gazeforge-tour.md",
        "documentation-map.md",
        "troubleshooting.md",
        "runnable-examples.md",
        "https://github.com/stefanosbalaskas/GazeForge/issues",
    ]
    pages = (
        "docs/gazeforge-tour.md",
        "docs/documentation-map.md",
        "docs/first-study-blueprint.md",
        "docs/method-chooser.md",
        "docs/artifact-dictionary.md",
        "docs/research-evidence-bundle.md",
        "docs/reporting-clinic.md",
        "docs/measurement-interpretation.md",
        "docs/estimand-preregistration.md",
        "docs/troubleshooting.md",
        "docs/getting-started.md",
        "docs/learning-paths.md",
        "docs/runnable-examples.md",
        "docs/data-import-clinic.md",
        "docs/worked-tracker-import.md",
        "docs/qc-review-exclusion-ledger.md",
        "docs/event-model-validation-clinic.md",
        "docs/publication-readiness.md",
    )
    for page in pages:
        assert _help_targets(_read(page)) == expected


def test_navigation_and_homepage_discover_task_map_and_help() -> None:
    mkdocs = _read("mkdocs.yml")
    homepage = _read("docs/index.md")

    assert "Documentation map: documentation-map.md" in mkdocs
    assert "Troubleshooting & diagnostics: troubleshooting.md" in mkdocs
    assert "Method chooser: method-chooser.md" in mkdocs
    assert "Artifact & output dictionary: artifact-dictionary.md" in mkdocs
    assert "Research evidence bundle: research-evidence-bundle.md" in mkdocs
    assert "Reporting & interpretation clinic: reporting-clinic.md" in mkdocs
    assert "Measurement & interpretation clinic: measurement-interpretation.md" in mkdocs
    assert "Outcome & estimand preregistration: estimand-preregistration.md" in mkdocs
    assert "assets/python-suite-logo.png" in mkdocs

    for target in (
        "documentation-map.md",
        "troubleshooting.md",
        "gazeforge-tour.md",
        "first-study-blueprint.md",
        "method-chooser.md",
        "artifact-dictionary.md",
        "research-evidence-bundle.md",
        "reporting-clinic.md",
        "measurement-interpretation.md",
        "estimand-preregistration.md",
        "worked-tracker-import.md",
        "qc-review-exclusion-ledger.md",
        "event-model-validation-clinic.md",
        "publication-readiness.md",
    ):
        assert target in homepage

    assert "gf-onboarding-grid" in homepage
    assert "gf-flow" in homepage

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3


def test_accessibility_guards_are_explicit_but_not_overclaimed() -> None:
    css = _read("docs/stylesheets/extra.css")
    guide = _read("docs/troubleshooting.md").lower()

    assert ".gf-help a:focus-visible" in css
    assert "scroll-margin-top" in css
    assert "min-height: 2.75rem" in css
    assert "prefers-reduced-motion: no-preference" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "not proof of complete wcag conformance" in guide
    assert "manual keyboard/screen-reader review" in guide


def test_first_study_blueprint_is_concrete_and_claim_safe() -> None:
    page = _read("docs/first-study-blueprint.md")
    lower = page.lower()

    assert "research question" in lower
    assert "analysis contract" in lower
    assert "source-manifest.json" in page
    assert "decision-criteria.csv" in page
    assert "analysis-ready-table.csv" in page
    assert "software-identity.txt" in page
    assert "04_worked_advertising_study.py" in page
    assert "08_worked_qc_review_ledger.py" in page
    assert "13_worked_estimand_preregistration.py" in page
    assert "flagged and retained" in lower
    assert "no extrapolation" in lower
    assert "not a universal physiological cutoff" in lower
    assert "does not establish" in lower
    assert "trust" in lower
    assert "diagnosis" in lower

    mkdocs = _read("mkdocs.yml")
    homepage = _read("docs/index.md")
    learning = _read("docs/learning-paths.md")
    assert "First study blueprint: first-study-blueprint.md" in mkdocs
    assert "first-study-blueprint.md" in homepage
    assert "first-study-blueprint.md" in learning
