import numpy as np
import pandas as pd

from gazeforge import (
    cluster_scanpaths_ai,
    embed_scanpaths,
    find_scanpath_motifs,
    fit_scanpath_embedder,
    scanpath_similarity,
    to_semantic_scanpaths,
)


def _fixations():
    rows = []
    sequences = {
        ("p1", "t1"): ["logo", "claim", "claim", "evidence", "claim"],
        ("p2", "t1"): ["logo", "claim", "evidence", "evidence", "claim"],
        ("p3", "t1"): ["image", "price", "image", "price"],
        ("p4", "t1"): ["image", "price", "price", "image"],
    }
    for (p, t), seq in sequences.items():
        for i, label in enumerate(seq):
            rows.append(
                {
                    "participant_id": p,
                    "trial_id": t,
                    "fixation_index": i,
                    "aoi_label": label,
                    "duration_ms": 100 + i * 10,
                }
            )
    return pd.DataFrame(rows)


def test_scanpath_pipeline():
    scanpaths = to_semantic_scanpaths(_fixations())
    assert len(scanpaths) == 4
    assert scanpaths.loc[0, "sequence"] == ("logo", "claim", "evidence", "claim")

    motifs = find_scanpath_motifs(scanpaths, min_count=2)
    assert not motifs.empty

    model = fit_scanpath_embedder(scanpaths, n_components=2)
    embedded = embed_scanpaths(scanpaths, model)
    cols = [c for c in embedded if c.startswith("embedding_")]
    assert len(cols) == 2

    similarity = scanpath_similarity(embedded)
    assert similarity.shape == (4, 4)
    assert np.allclose(np.diag(similarity), 1.0)

    clustered = cluster_scanpaths_ai(embedded, n_clusters=2)
    assert clustered["scanpath_cluster"].nunique() == 2
