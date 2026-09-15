import json
from html import escape
from pathlib import Path

import pandas as pd

from gazeforge.benchmarks import BenchmarkDatasetCard, build_benchmark_report
from gazeforge.dashboard import BenchmarkDashboard, build_benchmark_dashboard
from gazeforge.evidence_cards import (
    render_benchmark_dashboard_with_cards,
    render_frozen_report_cards,
    render_verified_suite_cards,
)
from gazeforge.public_evidence import build_public_benchmark_dashboard


def _report(name: str = "Example-human-benchmark"):
    card = BenchmarkDatasetCard(
        name=name,
        version="1.0",
        source="external-test-source",
        license="test-only",
        task="eye-event classification",
        sampling_rates_hz=[500.0, 60.0],
        participant_count=10,
        split_unit="participant_id",
        validation_scope="external-empirical-benchmark",
        annotation_origin="expert-manual",
        sampling_origin="resampled",
        reference_strength="derived-human-reference",
        human_annotator_count=2,
    )
    return build_benchmark_report(
        benchmark=card,
        model={"models": ["I-VT", "RandomForest", "ContextMLP"]},
        protocol={"n_splits": 5},
        metrics={"summary": [{"model": "RandomForest", "accuracy": 0.8}]},
    )


def test_report_cards_come_from_validated_dashboard_and_use_short_fingerprint(
    tmp_path,
):
    report = _report()
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    dashboard = build_benchmark_dashboard(tmp_path)

    cards = render_frozen_report_cards(dashboard)
    assert "gf-evidence-grid" in cards
    assert "Frozen report" in cards
    assert "Example-human-benchmark" in cards
    assert "resampled" in cards
    assert "derived-human-reference" in cards
    assert "I-VT, RandomForest, ContextMLP" in cards
    assert report["report_fingerprint_sha256"][:12] in cards
    assert report["report_fingerprint_sha256"] not in cards


def test_card_renderer_html_escapes_validated_values(tmp_path):
    report = _report("<script>alert('x')</script>")
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    cards = render_frozen_report_cards(build_benchmark_dashboard(tmp_path))

    assert "<script>" not in cards
    assert escape("<script>alert('x')</script>", quote=True) in cards


def test_empty_dashboard_creates_no_cards_and_preserves_canonical_empty_state():
    dashboard = BenchmarkDashboard(
        reports=(),
        table=pd.DataFrame(),
        source_files=(),
    )
    assert render_verified_suite_cards(dashboard) == ""
    assert render_frozen_report_cards(dashboard) == ""

    markdown = render_benchmark_dashboard_with_cards(dashboard)
    assert "gf-evidence-grid" not in markdown
    assert "No integrity-checked frozen empirical benchmark reports" in markdown


def test_scientific_review_provenance_only_renders_when_present():
    suite_table = pd.DataFrame(
        [
            {
                "suite": "Reviewed suite",
                "status": "frozen",
                "report_count": 2,
                "target_sampling_rate_hz": "60",
                "model": "Example model",
                "reference_stream_id": "reviewed-reference",
                "human_human_agreement_included": "true",
                "source_manifest_fingerprint_sha256": "a" * 64,
                "suite_fingerprint_sha256": "b" * 64,
                "scientific_review_reviewer": "Reviewer A",
                "scientific_reviewed_at": "2026-09-15T00:00:00Z",
                "scientific_review_scope": "public-frozen-evidence",
                "scientific_review_fingerprint_sha256": "c" * 64,
            },
            {
                "suite": "Unreviewed suite",
                "status": "verified",
                "report_count": 1,
                "target_sampling_rate_hz": "60",
                "model": "Baseline",
                "reference_stream_id": "reference",
                "human_human_agreement_included": "false",
                "source_manifest_fingerprint_sha256": "d" * 64,
                "suite_fingerprint_sha256": "e" * 64,
                "scientific_review_reviewer": "",
                "scientific_reviewed_at": "",
                "scientific_review_scope": "",
                "scientific_review_fingerprint_sha256": "",
            },
        ]
    )
    dashboard = BenchmarkDashboard(
        reports=(),
        table=pd.DataFrame(),
        source_files=(),
        suites=(),
        suite_table=suite_table,
        suite_source_files=(),
    )

    cards = render_verified_suite_cards(dashboard)
    reviewed_card, unreviewed_card = cards.split("</article>")[:2]
    assert "Reviewer A" in reviewed_card
    assert "public-frozen-evidence" in reviewed_card
    assert "cccccccccccc" in reviewed_card
    assert "Reviewed by" not in unreviewed_card
    assert "Review fingerprint" not in unreviewed_card


def test_repository_public_dashboard_cards_match_publication_gated_rows():
    root = Path(__file__).resolve().parents[1]
    dashboard = build_public_benchmark_dashboard(root / "validation")
    markdown = render_benchmark_dashboard_with_cards(dashboard)

    for _, row in dashboard.suite_table.iterrows():
        assert escape(str(row["suite"]), quote=True) in markdown
        assert str(row["suite_fingerprint_sha256"])[:12] in markdown
    for _, row in dashboard.table.iterrows():
        assert escape(str(row["benchmark"]), quote=True) in markdown
        assert str(row["report_fingerprint_sha256"])[:12] in markdown

    published_benchmarks = "\n".join(
        str(value)
        for value in dashboard.table.get(
            "benchmark",
            pd.Series(dtype=str),
        )
    )
    assert "Gaze-in-the-Wild" not in published_benchmarks
