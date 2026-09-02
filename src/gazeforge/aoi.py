"""Semantic areas of interest (AOIs), AI providers, and human review."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol

import numpy as np
import pandas as pd

from .exceptions import OptionalDependencyError, SchemaError
from .provenance import AuditTrail


@dataclass(frozen=True, slots=True)
class AOI:
    """Rectangular semantic area of interest with provenance metadata."""

    aoi_id: str
    label: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    confidence: float = 1.0
    source: str = "manual"
    model_name: str | None = None
    model_version: str | None = None

    def __post_init__(self) -> None:
        if self.xmax <= self.xmin or self.ymax <= self.ymin:
            raise ValueError("AOI bounds must satisfy xmax > xmin and ymax > ymin.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("AOI confidence must be between 0 and 1.")


class AOIProvider(Protocol):
    """Protocol implemented by semantic AOI proposal engines."""

    model_name: str
    model_version: str

    def detect(self, image: Any, labels: Sequence[str]) -> list[AOI]:
        """Return semantic AOI proposals."""


@dataclass
class CallableAOIProvider:
    """Adapter for custom/local detectors used by research teams."""

    detector: Callable[[Any, Sequence[str]], Iterable[AOI]]
    model_name: str = "custom"
    model_version: str = "unspecified"

    def detect(self, image: Any, labels: Sequence[str]) -> list[AOI]:
        """Run the supplied detector."""
        return list(self.detector(image, labels))


@dataclass
class HuggingFaceZeroShotAOIProvider:
    """Optional OWL-ViT zero-shot object detector via Transformers."""

    model_name: str = "google/owlvit-base-patch32"
    model_version: str = "huggingface-main"
    device: int | str = -1
    _pipeline: Any = None

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise OptionalDependencyError(
                    "HuggingFaceZeroShotAOIProvider requires the 'vision' extra: "
                    "python -m pip install 'gazeforge[vision]'"
                ) from exc
            self._pipeline = pipeline(
                task="zero-shot-object-detection",
                model=self.model_name,
                device=self.device,
            )
        return self._pipeline

    def detect(self, image: Any, labels: Sequence[str]) -> list[AOI]:
        """Return open-vocabulary rectangular proposals."""
        if not labels:
            raise ValueError("At least one semantic label is required.")
        detector = self._get_pipeline()
        raw = detector(image, candidate_labels=list(labels))
        aois: list[AOI] = []
        for i, item in enumerate(raw):
            box = item["box"]
            aois.append(
                AOI(
                    aoi_id=f"ai_{i:04d}",
                    label=str(item["label"]),
                    xmin=float(box["xmin"]),
                    ymin=float(box["ymin"]),
                    xmax=float(box["xmax"]),
                    ymax=float(box["ymax"]),
                    confidence=float(item["score"]),
                    source="ai",
                    model_name=self.model_name,
                    model_version=self.model_version,
                )
            )
        return aois


def detect_semantic_aois(
    image: Any,
    *,
    labels: Sequence[str],
    provider: AOIProvider,
    min_confidence: float = 0.10,
) -> list[AOI]:
    """Generate semantic AOI proposals and retain only proposals above a threshold."""
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be in [0, 1].")
    proposals = provider.detect(image, labels)
    return [aoi for aoi in proposals if aoi.confidence >= min_confidence]


def aois_to_frame(aois: Sequence[AOI]) -> pd.DataFrame:
    """Convert AOIs to an ordinary reviewable table."""
    return pd.DataFrame(
        [
            {
                "aoi_id": a.aoi_id,
                "label": a.label,
                "xmin": a.xmin,
                "ymin": a.ymin,
                "xmax": a.xmax,
                "ymax": a.ymax,
                "confidence": a.confidence,
                "source": a.source,
                "model_name": a.model_name,
                "model_version": a.model_version,
            }
            for a in aois
        ]
    )


def apply_aoi_review(
    aois: Sequence[AOI],
    decisions: pd.DataFrame,
) -> tuple[list[AOI], pd.DataFrame]:
    """Apply explicit human accept/reject/relabel/rebound decisions."""
    required = {"aoi_id", "action"}
    if not required.issubset(decisions.columns):
        raise SchemaError(f"AOI review decisions require columns: {sorted(required)}.")

    by_id = {a.aoi_id: a for a in aois}
    reviewed = dict(by_id)
    log_rows: list[dict[str, Any]] = []

    for _, row in decisions.iterrows():
        aoi_id = str(row["aoi_id"])
        if aoi_id not in by_id:
            raise SchemaError(f"Review references unknown AOI: {aoi_id}")
        action = str(row["action"]).strip().lower()
        before = reviewed.get(aoi_id, by_id[aoi_id])

        if action == "accept":
            after = replace(before, source="human_reviewed")
        elif action == "reject":
            reviewed.pop(aoi_id, None)
            after = None
        elif action == "relabel":
            if pd.isna(row.get("label")):
                raise SchemaError(f"Relabel action for {aoi_id} requires a label.")
            after = replace(before, label=str(row["label"]), source="human_corrected")
            reviewed[aoi_id] = after
        elif action == "replace_bounds":
            coords = [row.get(c) for c in ("xmin", "ymin", "xmax", "ymax")]
            if any(pd.isna(v) for v in coords):
                raise SchemaError(f"replace_bounds action for {aoi_id} requires all bounds.")
            after = replace(
                before,
                xmin=float(coords[0]),
                ymin=float(coords[1]),
                xmax=float(coords[2]),
                ymax=float(coords[3]),
                source="human_corrected",
            )
            reviewed[aoi_id] = after
        else:
            raise SchemaError(f"Unsupported AOI review action: {action!r}.")

        if action == "accept":
            reviewed[aoi_id] = after
        log_rows.append(
            {
                "aoi_id": aoi_id,
                "action": action,
                "before_label": before.label,
                "after_label": None if after is None else after.label,
                "reviewed": True,
            }
        )

    return list(reviewed.values()), pd.DataFrame(log_rows)


def map_fixations_to_aois(
    fixations: pd.DataFrame,
    aois: Sequence[AOI],
    *,
    x_col: str = "x_px",
    y_col: str = "y_px",
    overlap_rule: str = "highest_confidence",
    trail: AuditTrail | None = None,
) -> pd.DataFrame:
    """Assign each fixation to at most one AOI while preserving unassigned rows."""
    if x_col not in fixations or y_col not in fixations:
        raise SchemaError(f"Fixations require coordinate columns {x_col!r} and {y_col!r}.")
    if overlap_rule not in {"highest_confidence", "smallest_area", "first"}:
        raise ValueError("overlap_rule must be highest_confidence, smallest_area, or first.")

    out = fixations.copy()
    assigned_id: list[str | None] = []
    assigned_label: list[str | None] = []
    assigned_conf: list[float] = []
    assigned_source: list[str | None] = []

    for x, y in zip(
        pd.to_numeric(out[x_col], errors="coerce"),
        pd.to_numeric(out[y_col], errors="coerce"),
        strict=True,
    ):
        if not np.isfinite(x) or not np.isfinite(y):
            candidates: list[AOI] = []
        else:
            candidates = [
                a for a in aois if a.xmin <= x <= a.xmax and a.ymin <= y <= a.ymax
            ]

        if not candidates:
            chosen = None
        elif overlap_rule == "highest_confidence":
            chosen = max(
                candidates,
                key=lambda a: (a.confidence, -(a.xmax - a.xmin) * (a.ymax - a.ymin)),
            )
        elif overlap_rule == "smallest_area":
            chosen = min(
                candidates,
                key=lambda a: (a.xmax - a.xmin) * (a.ymax - a.ymin),
            )
        else:
            chosen = candidates[0]

        assigned_id.append(None if chosen is None else chosen.aoi_id)
        assigned_label.append(None if chosen is None else chosen.label)
        assigned_conf.append(np.nan if chosen is None else chosen.confidence)
        assigned_source.append(None if chosen is None else chosen.source)

    out["aoi_id"] = assigned_id
    out["aoi_label"] = assigned_label
    out["aoi_confidence"] = assigned_conf
    out["aoi_source"] = assigned_source

    if trail is not None:
        trail.add(
            operation="map_fixations_to_aois",
            input_data=fixations,
            output_data=out,
            parameters={
                "x_col": x_col,
                "y_col": y_col,
                "overlap_rule": overlap_rule,
                "n_aois": len(aois),
            },
        )
    return out
