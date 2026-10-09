"""Research-only multimodal pairing, independent split axes and QC-weighted fusion.

These structural audits do not establish physical clock accuracy, predictor
calibration, label validity, or external generalization.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


def _identity_pairs(frame: pd.DataFrame, cols: Sequence[str]) -> set[tuple]:
    if not all(c in frame.columns for c in cols):
        raise ValueError(f"missing identity columns: {set(cols) - set(frame.columns)}")
    if frame[list(cols)].isna().any().any():
        raise ValueError("identity columns cannot contain missing values")
    return set(map(tuple, frame.loc[:, list(cols)].itertuples(index=False, name=None)))


def audit_temporal_session_separation(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    participant_col: str = "participant_id",
    session_col: str = "session_id",
    block_col: str = "temporal_block_id",
) -> dict:
    """Audit three independent split overlaps using exact supplied identities."""
    if train.empty or test.empty:
        raise ValueError("train and test must both contain observations")
    p = (participant_col,)
    s = (participant_col, session_col)
    b = (participant_col, session_col, block_col)
    overlaps = {
        "participant_overlap": len(_identity_pairs(train, p) & _identity_pairs(test, p)),
        "session_overlap": len(_identity_pairs(train, s) & _identity_pairs(test, s)),
        "temporal_block_overlap": len(_identity_pairs(train, b) & _identity_pairs(test, b)),
    }
    overlaps.update({
        "participant_disjoint": overlaps["participant_overlap"] == 0,
        "session_disjoint": overlaps["session_overlap"] == 0,
        "temporal_block_disjoint": overlaps["temporal_block_overlap"] == 0,
        "claim_boundary": (
            "Identity-disjointness only. Block naming does not establish "
            "independence of adjacent time windows."
        ),
    })
    return overlaps


def audit_multimodal_pairing(
    streams: Mapping[str, pd.DataFrame],
    *,
    participant_col: str = "participant_id",
    trial_col: str = "trial_id",
) -> dict:
    """Classify person/trial pairing without equating it with clock alignment."""
    if len(streams) < 2:
        raise ValueError("at least two named modalities are required")
    participant_sets, trial_sets = [], []
    counts = {}
    for name, frame in streams.items():
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(frame, pd.DataFrame)
            or frame.empty
        ):
            raise ValueError("each modality requires a nonempty name and DataFrame")
        p = _identity_pairs(frame, (participant_col,))
        trial = _identity_pairs(frame, (participant_col, trial_col))
        participant_sets.append(p)
        trial_sets.append(trial)
        counts[name] = {"participants": len(p), "participant_trials": len(trial)}
    common_participants = set.intersection(*participant_sets)
    common_trials = set.intersection(*trial_sets)
    if common_trials:
        classification = "paired_within_trial_not_time_certified"
    elif common_participants:
        classification = "paired_within_person_not_trial"
    else:
        classification = "unpaired_cross_source"
    return {
        "classification": classification,
        "common_participants": len(common_participants),
        "common_participant_trials": len(common_trials),
        "per_modality": counts,
        "clock_alignment_certified": False,
        "claim_boundary": (
            "Identity pairing only; synchronization and fusion validity "
            "require separate evidence."
        ),
    }


def reliability_weighted_fusion(
    aligned: pd.DataFrame,
    *,
    value_cols: Sequence[str],
    weight_cols: Sequence[str],
    values_are_commensurate: bool = False,
) -> pd.DataFrame:
    """Compute a descriptive weighted mean of explicitly commensurate aligned channels.

    QC weights must be declared on [0, 1]; missing weights contribute nothing.
    No quality detector, clock synchronization or learned multimodal model is run.
    """
    if not values_are_commensurate:
        raise ValueError("explicitly confirm prespecified commensurate channel scales")
    if not isinstance(aligned, pd.DataFrame) or aligned.empty:
        raise ValueError("aligned must be a nonempty DataFrame")
    if len(value_cols) < 2 or len(value_cols) != len(weight_cols):
        raise ValueError("supply at least two matched value and weight columns")
    if not set([*value_cols, *weight_cols]).issubset(aligned.columns):
        raise ValueError("declared channel columns are missing")
    x = aligned[list(value_cols)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    w = aligned[list(weight_cols)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    if np.isinf(w).any() or np.any((np.isfinite(w)) & ((w < 0) | (w > 1))):
        raise ValueError("finite QC weights must be in [0, 1]")
    usable = np.isfinite(x) & np.isfinite(w) & (w > 0)
    effective = np.where(usable, w, 0.0)
    weight_sum = effective.sum(axis=1)
    fused = np.divide(
        np.sum(np.where(usable, x, 0.0) * effective, axis=1),
        weight_sum,
        out=np.full(len(aligned), np.nan),
        where=weight_sum > 0,
    )
    return pd.DataFrame({
        "fused_value": fused,
        "effective_weight_sum": weight_sum,
        "n_contributing_modalities": usable.sum(axis=1),
    }, index=aligned.index)
