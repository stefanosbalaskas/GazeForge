"""Regression tests for task-oriented methods and runnable-example navigation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_methods_overview_is_first_methods_route_and_groups_real_pages() -> None:
    mkdocs = _read("mkdocs.yml")
    methods = _read("docs/methods-overview.md")

    overview = "      - Overview: methods-overview.md"
    adapters = "      - Adapters & validation: adapters-validation.md"
    assert overview in mkdocs
    assert mkdocs.index(overview) < mkdocs.index(adapters)

    for target in (
        "adapters-validation.md",
        "motion-quality-gating.md",
        "temporal-models.md",
        "event-level-evaluation.md",
        "dynamic-aois.md",
        "grounded-sam2-backend.md",
        "research-workflows.md",
        "hierarchical-location-scale.md",
        "full-covariance-location-random-slope-scale.md",
        "validation-evidence-guide.md",
        "reproducible-reporting.md",
    ):
        assert target in methods


def test_examples_gallery_covers_all_real_scripts_and_exact_commands() -> None:
    page = _read("docs/runnable-examples.md")

    scripts = (
        "01_synthetic_qc.py",
        "02_ivt_baseline.py",
        "03_visual_diagnostics.py",
        "end_to_end_research_workflow.py",
    )
    for script in scripts:
        assert script in page
        assert f"blob/main/examples/{script}" in page

    assert "python examples/01_synthetic_qc.py" in page
    assert "python examples/02_ivt_baseline.py" in page
    assert "python examples/03_visual_diagnostics.py --output-dir visual-demo" in page
    assert "--output-dir end-to-end-research-demo" in page
    assert "--no-figures" in page


def test_examples_gallery_names_real_outputs_and_preserves_demo_boundary() -> None:
    page = _read("docs/runnable-examples.md")

    for output in (
        "01_qc_timeline.png",
        "06_dynamic_aoi.png",
        "01_source_gaze.csv",
        "10_semantic_scanpaths.csv",
        "provenance.json",
        "workflow_manifest.json",
        "figures/03_scanpath.png",
    ):
        assert output in page

    lower = page.lower()
    assert "not empirical validation evidence" in lower
    assert "native-device" in lower
    assert "native 60 hz" in lower
    assert "gazepoint" in lower
    assert "gp3" in lower
    assert "source table remains unchanged" in lower
    assert "synthetic_demo_not_empirical_evidence" in page


def test_new_hubs_are_discoverable_without_expanding_homepage_hero() -> None:
    mkdocs = _read("mkdocs.yml")
    homepage = _read("docs/index.md")
    getting_started = _read("docs/getting-started.md")
    learning_paths = _read("docs/learning-paths.md")
    examples_readme = _read("examples/README.md")

    assert "      - Runnable examples: runnable-examples.md" in mkdocs
    assert "methods-overview.md" in homepage
    assert "runnable-examples.md" in homepage
    assert "runnable-examples.md" in getting_started
    assert "runnable-examples.md" in learning_paths
    assert "../docs/runnable-examples.md" in examples_readme

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3


def test_methods_page_keeps_empirical_evidence_boundaries_explicit() -> None:
    methods = _read("docs/methods-overview.md").lower()

    assert "derived lower-rate evidence remains derived" in methods
    assert "not participant-disjoint" in methods
    assert "task-agnostic" in methods
    assert "bounded partial public-derivative evidence" in methods
    assert "native 60 hz" in methods
    assert "gazepoint gp3" in methods
