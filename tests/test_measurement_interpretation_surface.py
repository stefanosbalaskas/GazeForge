from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_measurement_interpretation_clinic_is_claim_safe_and_api_linked() -> None:
    page = _read("docs/measurement-interpretation.md")
    lower = page.lower()

    for phrase in (
        "observable",
        "construct bridge",
        "validity threats",
        "right-censored",
        "sensitivity",
        "do not infer automatically",
        "synthetic_demo_not_empirical_evidence",
    ):
        assert phrase in lower

    for target in (
        "api-reference.md#quality-control",
        "api-reference.md#eye-events",
        "api-reference.md#semantic-aois",
        "api-reference.md#scanpaths",
        "api-reference.md#sampling-sensitivity",
        "api-reference.md#structural-validation-scope",
    ):
        assert target in page

    assert "10.3758/s13428-023-02187-1" in page
    assert "10.3758/s13428-017-0998-z" in page
    assert "10.3758/s13428-021-01762-8" not in page
    assert "does not rely on the retracted" in lower


def test_measurement_interpretation_route_is_discoverable() -> None:
    mkdocs = _read("mkdocs.yml")
    homepage = _read("docs/index.md")
    readme = _read("README.md")
    chooser = _read("docs/method-chooser.md")
    methods = _read("docs/methods-overview.md")
    researchers = _read("docs/for-researchers.md")
    terminology = _read("docs/research-terminology.md")
    handoff = _read("docs/analysis-handoff.md")
    reporting = _read("docs/reporting-clinic.md")
    readiness = _read("docs/publication-readiness.md")
    learning = _read("docs/learning-paths.md")
    runnable = _read("docs/runnable-examples.md")

    for page in (
        mkdocs,
        homepage,
        readme,
        chooser,
        methods,
        researchers,
        terminology,
        handoff,
        reporting,
        readiness,
        learning,
        runnable,
    ):
        assert "measurement-interpretation" in page

    assert "12_worked_measurement_interpretation_audit.py" in runnable
    assert "fifteen deterministic examples" in runnable
    assert "fifteen deterministic examples/workflows" in learning
    assert "estimand-preregistration.md" in _read("docs/measurement-interpretation.md")

    start = homepage.index('<div class="gf-hero-actions"')
    end = homepage.index("</div>", start)
    assert homepage[start:end].count("{ .md-button") == 3
