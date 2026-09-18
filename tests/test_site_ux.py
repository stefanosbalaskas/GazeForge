"""Regression tests for the public documentation entry experience."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_homepage_has_three_primary_task_routes() -> None:
    homepage = _read("docs/index.md")
    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index('</div>', start)
    actions = homepage[start:end]

    assert actions.count("{ .md-button") == 3
    assert "[Take the tour](gazeforge-tour.md)" in actions
    assert "[Choose a task](documentation-map.md)" in actions
    assert "[Inspect evidence](validation-evidence-guide.md)" in actions


def test_secondary_resources_remain_available_without_competing_as_primary_actions() -> None:
    homepage = _read("docs/index.md")
    start = homepage.index('<div class="gf-resource-rail"')
    end = homepage.index('</div>', start)
    rail = homepage[start:end]

    for target in (
        "release-install.md",
        "reporting-interpretation-clinic.md",
        "https://pypi.org/project/gazeforge/",
        "citation-attribution.md",
        "https://doi.org/10.5281/zenodo.22650013",
        "gazepoint-gp3.md",
        "https://github.com/stefanosbalaskas/GazeForge",
    ):
        assert target in rail
    assert ".md-button" not in rail


def test_workflow_previews_are_visual_and_explicitly_non_empirical() -> None:
    homepage = _read("docs/index.md")

    for figure in (
        "synthetic-qc-diagnostics.svg",
        "synthetic-event-diagnostics.svg",
        "synthetic-aoi-scanpath.svg",
    ):
        assert figure in homepage

    assert homepage.count('alt="Synthetic demo') == 3
    assert "synthetic/demo data only" in homepage.lower()
    assert "not empirical validation evidence" in homepage.lower()
    assert "native 60 hz" in homepage.lower()
    assert "gazepoint" in homepage.lower()
    assert "gp3" in homepage.lower()


def test_site_navigation_is_pruned_and_search_is_shareable() -> None:
    mkdocs = _read("mkdocs.yml")

    assert "    - navigation.prune" in mkdocs
    assert "    - search.share" in mkdocs
    assert "navigation.expand" not in mkdocs
    assert "site_url: https://stefanosbalaskas.github.io/GazeForge/" in mkdocs


def test_site_ux_css_is_responsive_keyboard_visible_and_motion_safe() -> None:
    css = _read("docs/stylesheets/extra.css")

    for selector in (
        ".gf-hero-actions",
        ".gf-resource-rail",
        ".gf-task-grid",
        ".gf-preview-grid",
        ".gf-preview-card:focus-visible",
        ".gf-study-path",
        ".gf-study-path a:focus-visible",
    ):
        assert selector in css

    assert "@media screen and (max-width: 60em)" in css
    assert "@media screen and (max-width: 44.9844em)" in css
    assert "prefers-reduced-motion: no-preference" in css
    assert "prefers-reduced-motion: reduce" in css
