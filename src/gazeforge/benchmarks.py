"""Benchmark manifests and deterministic validation-report freezing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass(slots=True)
class BenchmarkDatasetCard:
    """Provenance, evidence-strength, and split metadata for one benchmark dataset.

    ``annotation_origin`` describes who or what produced the reference labels.
    ``sampling_origin`` distinguishes native recordings from derived/resampled views.
    ``reference_strength`` states the strongest validation interpretation supported by the
    reference. These fields are intentionally explicit so algorithm-generated labels cannot be
    presented as human validation merely because the underlying recording was sampled at a
    desirable rate.
    """

    ANNOTATION_ORIGINS: ClassVar[frozenset[str]] = frozenset(
        {
            "expert-manual",
            "human-manual",
            "human-assisted",
            "vendor-algorithm",
            "research-algorithm",
            "derived",
            "synthetic",
            "mixed",
            "unknown",
        }
    )
    SAMPLING_ORIGINS: ClassVar[frozenset[str]] = frozenset(
        {"native", "resampled", "mixed", "synthetic", "unknown"}
    )
    REFERENCE_STRENGTHS: ClassVar[frozenset[str]] = frozenset(
        {
            "expert-human-reference",
            "human-reference",
            "derived-human-reference",
            "algorithmic-concordance",
            "synthetic-smoke-only",
            "unknown",
        }
    )

    name: str
    version: str
    source: str
    license: str
    task: str
    sampling_rates_hz: list[float] = field(default_factory=list)
    participant_count: int | None = None
    stimulus_count: int | None = None
    split_unit: str = "participant_id"
    validation_scope: str = "development"
    annotation_origin: str = "unknown"
    sampling_origin: str = "unknown"
    reference_strength: str = "unknown"
    human_annotator_count: int | None = None
    reference_description: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Reject ambiguous evidence metadata before reports are generated."""
        if self.annotation_origin not in self.ANNOTATION_ORIGINS:
            raise ValueError(f"Unknown annotation_origin: {self.annotation_origin}")
        if self.sampling_origin not in self.SAMPLING_ORIGINS:
            raise ValueError(f"Unknown sampling_origin: {self.sampling_origin}")
        if self.reference_strength not in self.REFERENCE_STRENGTHS:
            raise ValueError(f"Unknown reference_strength: {self.reference_strength}")
        if self.human_annotator_count is not None and self.human_annotator_count < 0:
            raise ValueError("human_annotator_count must be non-negative.")
        if self.annotation_origin in {"vendor-algorithm", "research-algorithm"} and (
            self.reference_strength
            in {"expert-human-reference", "human-reference", "derived-human-reference"}
        ):
            raise ValueError(
                "Algorithm-generated annotations cannot be declared a human reference."
            )
        if self.sampling_origin == "synthetic" and self.reference_strength not in {
            "synthetic-smoke-only",
            "unknown",
        }:
            raise ValueError("Synthetic sampling cannot support an empirical reference claim.")

    @property
    def is_human_reference(self) -> bool:
        """Whether the card represents a human-derived validation reference."""
        return self.reference_strength in {
            "expert-human-reference",
            "human-reference",
            "derived-human-reference",
        }

    @property
    def is_native_human_reference(self) -> bool:
        """Whether human reference labels are evaluated at the native acquisition rate."""
        return self.is_human_reference and self.sampling_origin == "native"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the dataset card."""
        return asdict(self)


def canonical_json(payload: Any) -> str:
    """Serialize JSON deterministically for reproducible report fingerprints."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def benchmark_fingerprint(payload: Any) -> str:
    """Return a SHA-256 fingerprint of canonical JSON content."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_benchmark_report(
    *,
    benchmark: BenchmarkDatasetCard,
    metrics: dict[str, Any],
    model: dict[str, Any] | None = None,
    protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a benchmark report without adding non-deterministic timestamps."""
    body = {
        "benchmark": benchmark.to_dict(),
        "model": dict(model or {}),
        "protocol": dict(protocol or {}),
        "metrics": metrics,
    }
    return {**body, "report_fingerprint_sha256": benchmark_fingerprint(body)}


def freeze_benchmark_report(
    report: dict[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a deterministic benchmark JSON artifact.

    Existing files are protected by default so a previously reported validation result cannot be
    silently replaced during a later run.
    """
    target = Path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Benchmark report already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    target.write_text(text, encoding="utf-8")
    return target
