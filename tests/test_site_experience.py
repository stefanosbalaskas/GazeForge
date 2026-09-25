from __future__ import annotations

import re
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
    "docs/api-workflow-map.md",
    "docs/tags.md",
)

ARTICLE_PAGES = (
    "docs/articles/raw-gaze-to-defensible-analysis.md",
    "docs/articles/qc-flags-are-not-exclusions.md",
    "docs/articles/ai-proposals-are-not-ground-truth.md",
    "docs/articles/missing-is-not-zero.md",
    "docs/articles/participant-held-out-validation.md",
    "docs/articles/reviewer-ready-evidence.md",
)

SVG_ACCESSIBILITY_SET = (
    "docs/assets/figures/research-lifecycle.svg",
    "docs/assets/figures/evidence-ladder.svg",
    "docs/assets/figures/event-validation-workflow.svg",
    "docs/assets/figures/dynamic-aoi-support.svg",
    "docs/assets/figures/location-scale-workflow.svg",
    "docs/assets/figures/denominator-states.svg",
    "docs/assets/figures/provenance-chain.svg",
    "docs/assets/figures/validation-split-boundaries.svg",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_site_experience_hubs_exist() -> None:
    for relative in HUBS:
        assert (ROOT / relative).is_file(), relative


def test_site_experience_svg_assets_are_valid_and_accessible() -> None:
    namespace = {"svg": "http://www.w3.org/2000/svg"}

    for relative in SVG_ACCESSIBILITY_SET:
        root = ET.parse(ROOT / relative).getroot()
        assert root.tag.endswith("svg")
        assert root.attrib.get("role") == "img"

        title = root.find("svg:title", namespace)
        desc = root.find("svg:desc", namespace)

        assert title is not None
        assert title.text
        assert desc is not None
        assert desc.text


def test_mkdocs_exposes_discovery_privacy_and_prefetch_features() -> None:
    text = _read("mkdocs.yml")

    assert "navigation.instant.prefetch" in text
    assert "  - Explore:" in text
    assert "      - Examples gallery: examples-gallery.md" in text
    assert "      - Plot gallery: plot-gallery.md" in text
    assert "      - Workflow gallery: workflow-gallery.md" in text
    assert "      - Guides: guides.md" in text
    assert "      - API → workflow map: api-workflow-map.md" in text
    assert "\n  - meta\n" in text
    assert "\n  - privacy:\n" in text
    assert "enabled: !ENV [CI, false]" in text
    assert "\n  - tags\n" in text


def test_docs_workflow_audits_external_runtime_assets() -> None:
    text = _read(".github/workflows/docs.yml")

    assert "mkdocs build --strict" in text
    assert "python scripts/check_site_external_assets.py site" in text
    assert (ROOT / "scripts" / "check_site_external_assets.py").is_file()


def test_homepage_exposes_current_release_and_explore_routes() -> None:
    text = _read("docs/index.md")

    assert "<strong>0.1.0a2</strong>" in text
    assert 'python -m pip install "gazeforge==0.1.0a2"' in text
    assert "**GazeForge 0.1.0a2**" in text
    assert "## Explore by what you need to do" in text
    assert "examples-gallery/" in text
    assert "plot-gallery/" in text
    assert "workflow-gallery/" in text
    assert "api-workflow-map.md" in text
    assert "https://doi.org/10.5281/zenodo.22650012" in text


def test_current_install_surfaces_do_not_point_to_a1() -> None:
    for relative in (
        "docs/index.md",
        "docs/getting-started.md",
        "docs/gazeforge-tour.md",
        "docs/documentation-map.md",
        "docs/release-install.md",
    ):
        text = _read(relative)
        assert 'pip install "gazeforge==0.1.0a1"' not in text, relative


def test_generated_changelog_hook_has_no_stale_a1_literal() -> None:
    text = _read("scripts/mkdocs_hooks.py")
    assert "immutable `0.1.0a1`" not in text
    assert "latest frozen PyPI/GitHub Release artifact" in text


def test_example_gallery_tracks_repository_inventory() -> None:
    page = _read("docs/examples-gallery.md")
    examples = sorted((ROOT / "examples").glob("*.py"))

    assert len(examples) >= 22

    for path in examples:
        assert path.name in page, path.name


def test_plot_gallery_tracks_svg_inventory() -> None:
    page = _read("docs/plot-gallery.md")
    figures = sorted((ROOT / "docs" / "assets" / "figures").glob("*.svg"))

    assert len(figures) >= 11

    for path in figures:
        assert path.name in page, path.name


def test_new_markdown_pages_do_not_have_empty_image_alt_text() -> None:
    for relative in (*HUBS, *ARTICLE_PAGES):
        text = _read(relative)
        for alt in re.findall(r"!\[([^\]]*)\]\(", text):
            assert alt.strip(), relative


def test_new_markdown_links_to_source_pages_exist() -> None:
    for relative in (*HUBS, *ARTICLE_PAGES):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")

        for target in re.findall(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)", text):
            target_path = target.split("#", 1)[0]
            resolved = (path.parent / target_path).resolve()
            assert resolved.is_file(), f"{relative}: {target}"


def test_api_workflow_map_is_grounded_in_runnable_examples() -> None:
    text = _read("docs/api-workflow-map.md")

    required = (
        "canonicalize_gaze()",
        "ai_flag_anomalies()",
        "ivt_classify_events()",
        "map_fixations_to_aois()",
        "DynamicAOIKeyframe",
        "compare_event_models_grouped()",
        "adapt_gazepoint_samples()",
        "fingerprint_frame()",
        "00_gazeforge_tour.py",
        "05_worked_dynamic_aoi_study.py",
        "06_worked_event_model_validation.py",
        "07_worked_tracker_import_qc.py",
        "10_worked_analysis_handoff.py",
    )

    for phrase in required:
        assert phrase in text
