"""Compact audit-report construction."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .model_cards import ModelCard
from .provenance import AuditTrail, fingerprint_frame


def build_audit_report(
    data: pd.DataFrame,
    *,
    trail: AuditTrail | None = None,
    model_cards: list[ModelCard] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serialisable snapshot of data, provenance, and model metadata."""
    return {
        "data": {
            "rows": int(len(data)),
            "columns": [str(c) for c in data.columns],
            "fingerprint_sha256": fingerprint_frame(data),
        },
        "operations": [] if trail is None else [r.to_dict() for r in trail.records],
        "model_cards": [] if model_cards is None else [card.to_dict() for card in model_cards],
    }
