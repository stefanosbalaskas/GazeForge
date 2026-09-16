"""Regression tests for researcher lifecycle and publication guidance."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_lifecycle_navigation_places_research_route_after_import_clinic() -> None:
    mkdocs = _read("mkdocs.yml")
    import_entry = "      - Real-data import clinic: data-import-clinic.md"
    lifecycle_entry = "      - Study lifecycle: study-lifecycle.md"
    examples_entry = "      - Runnable examples: runnable-examples.md"

    assert import_entry in mkdocs
    assert lifecycle_entry in mkdocs
    assert examples_entry in mkdocs
    assert mkdocs.index(import_entry) < mkdocs.index(lifecycle_entry) < mkdocs.index(examples_entry)
    assert "      - Worked advertising/interface study: worked-advertising-study.md" in mkdocs
    assert "      - Publication readiness: publication-readiness.md" in mkdocs
    assert "      - Research terminology: research-terminology.md" in mkdocs


def test_lifecycle_covers_ten_stages_and_claim_boundaries() -> None:
    lifecycle = _read("docs/study-lifecycle.md").lower()

    for stage in (
        "1. define the question",
        "2. record acquisition facts",
        "3. preserve source identity",
        "4. canonicalise explicitly",
        "5. add qc evidence",
        "6. build measurement outputs",
        "7. validate the estimand",
        "8. audit rate and provenance",
        "9. freeze the evidence bundle",
        "10. report qualified claims",
    ):
        assert stage in lifecycle

    for boundary in (
        "successful import = device validity",
        "qc flag = invalid observation",
        "derived 60 hz = native 60 hz validity",
        "latent states from gaze alone",
    ):
        assert boundary in lifecycle


def test_publication_readiness_covers_reproducibility_and_validation() -> None:
    page = _read("docs/publication-readiness.md").lower()

    for concept in (
        "native acquisition rate",
        "participant",
        "trial",
        "canonicalisation",
        "qc flags",
        "exclusion",
        "aoi",
        "scanpath",
        "held-out",
        "leakage",
        "native versus derived",
        "reference labels",
        "calibration",
        "event-level",
        "software",
        "environment",
        "fingerprint",
        "manifest",
        "figure",
        "evidence boundary",
    ):
        assert concept in page


def test_terminology_separates_easy_to_overstate_claims() -> None:
    page = _read("docs/research-terminology.md").lower()

    for distinction in (
        "native sampling rate",
        "derived sampling rate",
        "participant-disjoint",
        "source-token-disjoint",
        "stimulus-disjoint",
        "dataset-held-out",
        "import compatibility",
        "device validity",
        "qc/anomaly flag",
        "invalid sample",
        "ai-proposed aoi",
        "human-reviewed",
        "sample-level",
        "event-level",
        "calibrated",
        "software demo",
        "empirical validation evidence",
        "fingerprint/checksum",
    ):
        assert distinction in page


def test_worked_study_is_discoverable_and_explicitly_synthetic() -> None:
    worked = _read("docs/worked-advertising-study.md")
    lower = worked.lower()

    for label in ("`brand`", "`claim`", "`disclosure`", "`product`"):
        assert label in worked

    for target in (
        "data-import-clinic.md",
        "validation-evidence-guide.md",
        "publication-readiness.md",
        "reproducible-reporting.md",
        "examples/04_worked_advertising_study.py",
    ):
        assert target in worked

    assert "synthetic_demo_not_empirical_evidence" in worked
    assert "not empirical validation evidence" in lower
    assert "native 60 hz" in lower
    assert "gazepoint" in lower
    assert "gp3" in lower
    assert "persuasion" in lower


def test_lifecycle_links_are_visible_without_expanding_homepage_hero() -> None:
    homepage = _read("docs/index.md")
    researchers = _read("docs/for-researchers.md")
    learning = _read("docs/learning-paths.md")
    reporting = _read("docs/reproducible-reporting.md")

    for page in (homepage, researchers, learning, reporting):
        assert "study-lifecycle.md" in page

    assert "publication-readiness.md" in reporting
    assert "research-terminology.md" in reporting

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
