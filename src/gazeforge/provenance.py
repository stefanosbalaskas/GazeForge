"""Stable fingerprints and auditable operation provenance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd


def fingerprint_frame(data: pd.DataFrame) -> str:
    """Create a stable SHA-256 fingerprint from values, index, columns, and dtypes."""
    payload = pd.util.hash_pandas_object(data, index=True).values.tobytes()
    header = json.dumps(
        {
            "columns": [str(c) for c in data.columns],
            "dtypes": [str(t) for t in data.dtypes],
            "shape": data.shape,
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(header + payload).hexdigest()


@dataclass(slots=True)
class ProvenanceRecord:
    """One auditable analysis operation."""

    operation: str
    input_fingerprint: str
    output_fingerprint: str
    parameters: dict[str, Any] = field(default_factory=dict)
    model_name: str | None = None
    model_version: str | None = None
    warnings: list[str] = field(default_factory=list)
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record."""
        return asdict(self)


@dataclass
class AuditTrail:
    """Mutable collection of provenance records."""

    records: list[ProvenanceRecord] = field(default_factory=list)

    def add(
        self,
        *,
        operation: str,
        input_data: pd.DataFrame,
        output_data: pd.DataFrame,
        parameters: dict[str, Any] | None = None,
        model_name: str | None = None,
        model_version: str | None = None,
        warnings: list[str] | None = None,
    ) -> ProvenanceRecord:
        """Fingerprint and append one operation."""
        record = ProvenanceRecord(
            operation=operation,
            input_fingerprint=fingerprint_frame(input_data),
            output_fingerprint=fingerprint_frame(output_data),
            parameters=dict(parameters or {}),
            model_name=model_name,
            model_version=model_version,
            warnings=list(warnings or []),
        )
        self.records.append(record)
        return record

    def to_frame(self) -> pd.DataFrame:
        """Return records as a flat table."""
        return pd.DataFrame([record.to_dict() for record in self.records])

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize records to JSON."""
        return json.dumps([record.to_dict() for record in self.records], indent=indent, default=str)
