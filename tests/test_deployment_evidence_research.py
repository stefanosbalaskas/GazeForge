import pandas as pd
import pytest

from gazeforge.deployment_evidence_research import deployment_evidence_frontier


def _table():
    return pd.DataFrame({
        "model_id": ["small", "medium", "large"],
        "dataset_id": ["study1"] * 3,
        "split_scope": ["participant_disjoint"] * 3,
        "evidence_type": ["hardware_measured"] * 3,
        "macro_f1": [.75, .82, .81],
        "latency_ms": [4., 9., 12.],
        "memory_mb": [5., 9., 10.],
        "energy_mj": [.05, .09, .12],
    })


def test_pareto_frontier_does_not_automatically_pick_winner():
    out = deployment_evidence_frontier(_table())
    assert out["pareto_nondominated"].tolist() == [True, True, False]


def test_cannot_compare_hardware_measurement_to_analytic_estimate():
    records = _table()
    records.loc[0, "evidence_type"] = "analytical_estimate"
    with pytest.raises(ValueError, match="common"):
        deployment_evidence_frontier(records)
    records = _table()
    records.loc[0, "dataset_id"] = "study2"
    with pytest.raises(ValueError, match="common"):
        deployment_evidence_frontier(records)
