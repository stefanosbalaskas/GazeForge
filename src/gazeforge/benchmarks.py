"""Benchmark manifests and deterministic validation-report freezing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BenchmarkDatasetCard:
    """Provenance and split metadata for one benchmark dataset."""

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
    notes: list[str] = field(default_factory=list)

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
