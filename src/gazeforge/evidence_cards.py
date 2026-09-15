"""Readable evidence cards generated only from validated benchmark dashboard rows."""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd

from .dashboard import BenchmarkDashboard, render_benchmark_dashboard_markdown
from .exceptions import BenchmarkIntegrityError

_CARD_FINGERPRINT_LENGTH = 12


def _text(value: Any) -> str:
    """Return a stable display string while treating missing pandas values as empty."""
    if value is None or value is pd.NA:
        return ""
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _html(value: Any) -> str:
    return escape(_text(value), quote=True)


def _short_fingerprint(value: Any) -> str:
    return _text(value)[:_CARD_FINGERPRINT_LENGTH]


def _fact(label: str, value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return (
        '<div class="gf-evidence-fact">'
        f"<dt>{escape(label)}</dt>"
        f"<dd>{escape(text, quote=True)}</dd>"
        "</div>"
    )


def _fingerprint(label: str, value: Any) -> str:
    short = _short_fingerprint(value)
    if not short:
        return ""
    return (
        '<span class="gf-evidence-fingerprint">'
        f"<span>{escape(label)}</span>"
        f"<code>{escape(short, quote=True)}</code>"
        "</span>"
    )


def _review_facts(row: pd.Series) -> tuple[str, str]:
    review_fingerprint = _text(
        row.get("scientific_review_fingerprint_sha256", "")
    )
    if not review_fingerprint:
        return "", ""
    facts = "".join(
        part
        for part in (
            _fact("Reviewed by", row.get("scientific_review_reviewer", "")),
            _fact("Reviewed at", row.get("scientific_reviewed_at", "")),
            _fact("Review scope", row.get("scientific_review_scope", "")),
        )
        if part
    )
    provenance = _fingerprint("Review fingerprint", review_fingerprint)
    return facts, provenance


def render_verified_suite_cards(dashboard: BenchmarkDashboard) -> str:
    """Render responsive cards from already validated public suite rows."""
    if dashboard.suite_table.empty:
        return ""

    cards: list[str] = []
    for _, row in dashboard.suite_table.iterrows():
        review_facts, review_provenance = _review_facts(row)
        facts = "".join(
            part
            for part in (
                _fact("Reports", row.get("report_count", "")),
                _fact(
                    "Target rate (Hz)",
                    row.get("target_sampling_rate_hz", ""),
                ),
                _fact("Model", row.get("model", "")),
                _fact(
                    "Reference stream",
                    row.get("reference_stream_id", ""),
                ),
                review_facts,
            )
            if part
        )
        provenance = "".join(
            part
            for part in (
                _fingerprint(
                    "Source manifest",
                    row.get("source_manifest_fingerprint_sha256", ""),
                ),
                _fingerprint(
                    "Suite fingerprint",
                    row.get("suite_fingerprint_sha256", ""),
                ),
                review_provenance,
            )
            if part
        )
        kicker = "Verified suite · " + _html(row.get("status", ""))
        cards.append(
            '<article class="gf-evidence-card" role="listitem">'
            f'<div class="gf-evidence-kicker">{kicker}</div>'
            f"<h3>{_html(row.get('suite', ''))}</h3>"
            f'<dl class="gf-evidence-facts">{facts}</dl>'
            f'<div class="gf-evidence-provenance">{provenance}</div>'
            "</article>"
        )

    return (
        '<div class="gf-evidence-grid" role="list">'
        + "".join(cards)
        + "</div>"
    )


def render_frozen_report_cards(dashboard: BenchmarkDashboard) -> str:
    """Render responsive cards from already validated public report rows."""
    if dashboard.table.empty:
        return ""

    cards: list[str] = []
    for _, row in dashboard.table.iterrows():
        review_facts, review_provenance = _review_facts(row)
        facts = "".join(
            part
            for part in (
                _fact("Version", row.get("version", "")),
                _fact(
                    "Sampling origin",
                    row.get("sampling_origin", ""),
                ),
                _fact(
                    "Sampling rate (Hz)",
                    row.get("sampling_rates_hz", ""),
                ),
                _fact(
                    "Reference strength",
                    row.get("reference_strength", ""),
                ),
                _fact("Model family", row.get("models", "")),
                _fact(
                    "Annotation origin",
                    row.get("annotation_origin", ""),
                ),
                review_facts,
            )
            if part
        )
        provenance = "".join(
            part
            for part in (
                _fingerprint(
                    "Report fingerprint",
                    row.get("report_fingerprint_sha256", ""),
                ),
                review_provenance,
            )
            if part
        )
        cards.append(
            '<article class="gf-evidence-card" role="listitem">'
            '<div class="gf-evidence-kicker">Frozen report</div>'
            f"<h3>{_html(row.get('benchmark', ''))}</h3>"
            f'<dl class="gf-evidence-facts">{facts}</dl>'
            f'<div class="gf-evidence-provenance">{provenance}</div>'
            "</article>"
        )

    return (
        '<div class="gf-evidence-grid" role="list">'
        + "".join(cards)
        + "</div>"
    )


def _insert_cards_before_table(markdown: str, heading: str, cards: str) -> str:
    if not cards:
        return markdown
    heading_index = markdown.find(heading)
    if heading_index < 0:
        raise BenchmarkIntegrityError(
            "Evidence card renderer could not find expected section heading: "
            f"{heading.strip()}"
        )
    table_index = markdown.find("\n| ", heading_index)
    if table_index < 0:
        raise BenchmarkIntegrityError(
            "Evidence card renderer could not find provenance table after: "
            f"{heading.strip()}"
        )
    return (
        markdown[:table_index]
        + "\n\n"
        + cards
        + "\n"
        + markdown[table_index:]
    )


def render_benchmark_dashboard_with_cards(dashboard: BenchmarkDashboard) -> str:
    """Add readable cards to the canonical dashboard without replacing audit tables."""
    markdown = render_benchmark_dashboard_markdown(dashboard)
    markdown = _insert_cards_before_table(
        markdown,
        "## Verified report suites\n\n",
        render_verified_suite_cards(dashboard),
    )
    markdown = _insert_cards_before_table(
        markdown,
        "## Frozen reports\n\n",
        render_frozen_report_cards(dashboard),
    )
    return markdown
