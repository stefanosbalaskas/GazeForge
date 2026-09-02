"""Machine-readable model cards for scientific use."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ModelCard:
    """Minimal model card required for auditable GazeForge inference."""

    name: str
    version: str
    task: str
    intended_use: str
    sampling_rates_hz: list[float] = field(default_factory=list)
    training_data: str = "unspecified"
    validation_data: str = "unspecified"
    metrics: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    ethical_constraints: list[str] = field(
        default_factory=lambda: [
            "Do not infer diagnoses, protected traits, or unsupported latent mental states "
            "from gaze."
        ]
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
