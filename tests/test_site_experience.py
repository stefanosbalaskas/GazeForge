from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]

HUBS = (
    "docs/explore.md",
    "docs/articles.md",
    "docs/examples-gallery.md",
    "docs/plot-gallery.md",
    "docs/workflow-gallery.md",
    "docs/guides.md",
    "docs/tags.md",
)

SVGS = (
    "docs/assets/figures/research-lifecycle.svg",
    "docs/assets/figures/evidence-ladder.svg",
    "docs/assets/figures/event-validation-workflow.svg",
    "docs/assets/figures/dynamic-aoi-support.svg",
    "docs/assets/figures/location-scale-workflow.svg",
)

EXAMPLES = (
    "00_gazeforge_tour.py",
    "01_synthetic_qc.py",
    "02_ivt_baseline.py",
    "03_visual_diagnostics.py",
    "04_worked_advertising_study.py",
    "05_worked_dynamic_aoi_study.py",
    "06_worked_event_model_validation.py",
    "07_worked_tracker_import_qc.py",
    "08_worked_qc_review_ledger.py",
    "09_worked_research_evidence_bundle.py",
    "10_worked_analysis_handoff.py",
    "11_worked_manuscript_reporting_bundle.py",
    "12_worked_measurement_interpretation_audit.py",
    "13_worked_estimand_preregistration.py",
    "14_worked_reviewer_replication_bundle.py",
    "15_worked_sensitivity_robustness_audit.py",
    "16_worked_denominator_exposure_audit.py",
    "17_worked_model_diagnostics_audit.py",
    "18_worked_missing_data_assumptions_audit.py",
    "19_worked_inferential_reporting_audit.py",
    "20_worked_grouping_pseudoreplication_audit.py",
    "end_to_end_research_workflow.py",
)


def test_site_experience_hubs_exist() -> None:
    for relative in HUBS:
        assert (ROOT / relative).is_file(), relative


def test_site_experience_svg_assets_are_valid_and_accessible() -> None:
    namespace = {"svg": "http://www.w3.org/2000/svg"}

    for relative in SVGS:
        root = ET.parse(ROOT / relative).getroot()
        assert root.tag.endswith("svg")
        assert root.attrib.get("role") == "img"

        title = root.find("svg:title", namespace)
        desc = root.find("svg:desc", namespace)

        assert title is not None
        assert title.text
        assert desc is not None
        assert desc.text


def test_mkdocs_exposes_explore_and_discovery_features() -> None:
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")

    assert "navigation.instant.prefetch" in text
    assert "  - Explore:" in text
    assert "      - Examples gallery: examples-gallery.md" in text
    assert "      - Plot gallery: plot-gallery.md" in text
    assert "      - Workflow gallery: workflow-gallery.md" in text
    assert "      - Guides: guides.md" in text
    assert "\n  - tags\n" in text


def test_homepage_exposes_current_release_and_explore_routes() -> None:
    text = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "<strong>0.1.0a2</strong>" in text
    assert "## Explore by what you need to do" in text
    assert "examples-gallery/" in text
    assert "plot-gallery/" in text
    assert "workflow-gallery/" in text


def test_generated_changelog_hook_has_no_stale_a1_literal() -> None:
    text = (ROOT / "scripts" / "mkdocs_hooks.py").read_text(encoding="utf-8")
    assert "immutable `0.1.0a1`" not in text


def test_existing_example_inventory_is_represented() -> None:
    page = (ROOT / "docs" / "examples-gallery.md").read_text(encoding="utf-8")

    for name in EXAMPLES:
        assert name in page
