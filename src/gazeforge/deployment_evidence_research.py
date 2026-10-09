"""Experimental resource/performance comparison with evidence-type guards.

A Pareto frontier is computed only for genuinely comparable measurement types,
datasets and split scopes. No model is selected or deployment certified.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def deployment_evidence_frontier(
    records: pd.DataFrame,
    *,
    score_col: str = "macro_f1",
    latency_col: str = "latency_ms",
    memory_col: str = "memory_mb",
    energy_col: str = "energy_mj",
) -> pd.DataFrame:
    """Mark Pareto-nondominated complete candidates without a single winner.

    Scores are maximized; latency, RAM and energy are minimized. Evidence type
    must be explicitly all measured or all estimated; cross-type ranking is
    prohibited. A common dataset, split scope and metric definition are required.
    """
    required = ["model_id", "dataset_id", "split_scope", "evidence_type",
                score_col, latency_col, memory_col, energy_col]
    if not isinstance(records, pd.DataFrame) or len(records) < 2:
        raise ValueError("at least two deployment records required")
    if len(set(required)) != len(required) or not set(required).issubset(records.columns):
        raise ValueError("required deployment columns missing or duplicated")
    frame = records.loc[:, required].copy()
    for column in ("model_id", "dataset_id", "split_scope", "evidence_type"):
        if frame[column].isna().any() or (frame[column].astype(str).str.strip() == "").any():
            raise ValueError(f"{column} must be fully declared")
    if frame["model_id"].duplicated().any():
        raise ValueError("model_id must be unique")
    for name in ("dataset_id", "split_scope", "evidence_type"):
        if frame[name].nunique() != 1:
            raise ValueError(f"{name} must be common across comparable candidates")
    if frame["evidence_type"].iloc[0] not in {"hardware_measured", "analytical_estimate"}:
        raise ValueError("evidence_type must state hardware_measured or analytical_estimate")
    values = frame[[score_col, latency_col, memory_col, energy_col]].apply(
        pd.to_numeric, errors="coerce"
    ).to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.any(values[:, 1:] < 0):
        raise ValueError("performance and resource measures must be finite; resources nonnegative")
    if np.any((values[:, 0] < 0) | (values[:, 0] > 1)):
        raise ValueError("classification macro_f1 must be a fraction in [0, 1]")
    # Convert all objectives to maximization without combining units.
    objectives = values * np.array([1., -1., -1., -1.])
    frontier = []
    for i, candidate in enumerate(objectives):
        dominates = np.all(objectives >= candidate, axis=1) & np.any(
            objectives > candidate, axis=1
        )
        dominates[i] = False
        frontier.append(not bool(dominates.any()))
    frame["pareto_nondominated"] = frontier
    frame["claim_boundary"] = (
        "Descriptive within-dataset and evidence-type frontier only; "
        "does not prove hardware deployment or select a preferred model."
    )
    return frame
