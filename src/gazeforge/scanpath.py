"""Semantic scanpaths, motifs, learned embeddings, similarity, and clustering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .exceptions import SchemaError


def _sequence_text(sequence: Sequence[str]) -> str:
    return " ".join(str(token).replace(" ", "_") for token in sequence)


def to_semantic_scanpaths(
    fixations: pd.DataFrame,
    *,
    label_col: str = "aoi_label",
    duration_col: str | None = "duration_ms",
    group_cols: tuple[str, ...] = ("participant_id", "trial_id"),
    collapse_repeats: bool = True,
    drop_unassigned: bool = True,
) -> pd.DataFrame:
    """Convert ordered fixation rows into one semantic sequence per trial."""
    required = [*group_cols, label_col]
    missing = [c for c in required if c not in fixations.columns]
    if missing:
        raise SchemaError(f"Missing columns for semantic scanpaths: {missing}")

    rows: list[dict[str, object]] = []
    for keys, part in fixations.groupby(list(group_cols), sort=False, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        labels: list[str] = []
        durations: list[float] = []

        for _, row in part.iterrows():
            label = row[label_col]
            if pd.isna(label):
                if drop_unassigned:
                    continue
                label = "UNASSIGNED"
            label = str(label)
            duration = (
                float(row[duration_col])
                if duration_col and duration_col in part and pd.notna(row[duration_col])
                else np.nan
            )

            if collapse_repeats and labels and labels[-1] == label:
                if np.isfinite(duration):
                    prior = durations[-1]
                    durations[-1] = duration if not np.isfinite(prior) else prior + duration
            else:
                labels.append(label)
                durations.append(duration)

        row = {col: value for col, value in zip(group_cols, keys, strict=True)}
        row.update(
            sequence=tuple(labels),
            sequence_text=_sequence_text(labels),
            durations_ms=tuple(durations),
            n_steps=len(labels),
            total_duration_ms=float(np.nansum(durations)) if durations else 0.0,
        )
        rows.append(row)
    return pd.DataFrame(rows)


def find_scanpath_motifs(
    scanpaths: pd.DataFrame,
    *,
    sequence_col: str = "sequence",
    ngram_range: tuple[int, int] = (2, 3),
    min_count: int = 2,
) -> pd.DataFrame:
    """Count recurrent contiguous AOI n-grams."""
    if sequence_col not in scanpaths:
        raise SchemaError(f"Missing sequence column: {sequence_col}")
    counts: dict[tuple[str, ...], int] = {}
    for seq in scanpaths[sequence_col]:
        tokens = tuple(str(x) for x in seq)
        for n in range(ngram_range[0], ngram_range[1] + 1):
            for i in range(max(0, len(tokens) - n + 1)):
                motif = tokens[i : i + n]
                counts[motif] = counts.get(motif, 0) + 1
    rows = [
        {"motif": motif, "motif_text": " → ".join(motif), "n": len(motif), "count": count}
        for motif, count in counts.items()
        if count >= min_count
    ]
    return pd.DataFrame(rows).sort_values(["count", "n"], ascending=[False, True], ignore_index=True)


@dataclass(slots=True)
class ScanpathEmbeddingModel:
    """TF-IDF n-gram encoder with optional learned SVD compression."""

    vectorizer: TfidfVectorizer
    reducer: TruncatedSVD | None
    n_features_out: int
    model_name: str = "SemanticNgramSVD"
    model_version: str = "0.1"


def fit_scanpath_embedder(
    scanpaths: pd.DataFrame,
    *,
    text_col: str = "sequence_text",
    n_components: int = 16,
    ngram_range: tuple[int, int] = (1, 3),
    random_state: int = 42,
) -> ScanpathEmbeddingModel:
    """Fit a learned semantic scanpath representation."""
    if text_col not in scanpaths:
        raise SchemaError(f"Missing scanpath text column: {text_col}")
    texts = scanpaths[text_col].fillna("").astype(str).tolist()
    if not texts or not any(text.strip() for text in texts):
        raise SchemaError("Cannot fit scanpath embeddings on empty sequences.")

    vectorizer = TfidfVectorizer(
        analyzer="word",
        token_pattern=r"(?u)\b\S+\b",
        ngram_range=ngram_range,
        lowercase=False,
    )
    matrix = vectorizer.fit_transform(texts)
    max_components = min(matrix.shape[0] - 1, matrix.shape[1] - 1)
    if max_components >= 1 and n_components >= 1:
        k = min(int(n_components), int(max_components))
        reducer = TruncatedSVD(n_components=k, random_state=random_state)
        reducer.fit(matrix)
        n_out = k
    else:
        reducer = None
        n_out = matrix.shape[1]

    return ScanpathEmbeddingModel(
        vectorizer=vectorizer,
        reducer=reducer,
        n_features_out=int(n_out),
    )


def embed_scanpaths(
    scanpaths: pd.DataFrame,
    model: ScanpathEmbeddingModel,
    *,
    text_col: str = "sequence_text",
    id_cols: tuple[str, ...] = ("participant_id", "trial_id"),
) -> pd.DataFrame:
    """Transform scanpaths into numeric embeddings."""
    if text_col not in scanpaths:
        raise SchemaError(f"Missing scanpath text column: {text_col}")
    matrix = model.vectorizer.transform(scanpaths[text_col].fillna("").astype(str))
    if model.reducer is not None:
        dense = model.reducer.transform(matrix)
    else:
        dense = matrix.toarray()

    result = pd.DataFrame(
        dense,
        columns=[f"embedding_{i:03d}" for i in range(dense.shape[1])],
        index=scanpaths.index,
    )
    for col in reversed(id_cols):
        if col in scanpaths:
            result.insert(0, col, scanpaths[col].to_numpy())
    return result.reset_index(drop=True)


def scanpath_similarity(
    embeddings: pd.DataFrame,
    *,
    embedding_prefix: str = "embedding_",
) -> np.ndarray:
    """Return pairwise cosine similarity for learned embeddings."""
    cols = [c for c in embeddings.columns if c.startswith(embedding_prefix)]
    if not cols:
        raise SchemaError("No embedding columns found.")
    return cosine_similarity(embeddings[cols].to_numpy(float))


def cluster_scanpaths_ai(
    embeddings: pd.DataFrame,
    *,
    n_clusters: int,
    embedding_prefix: str = "embedding_",
    random_state: int = 42,
) -> pd.DataFrame:
    """Cluster learned scanpath embeddings with K-means."""
    cols = [c for c in embeddings.columns if c.startswith(embedding_prefix)]
    if not cols:
        raise SchemaError("No embedding columns found.")
    if n_clusters < 2 or n_clusters > len(embeddings):
        raise ValueError("n_clusters must be between 2 and the number of scanpaths.")
    model = KMeans(n_clusters=n_clusters, n_init="auto", random_state=random_state)
    labels = model.fit_predict(embeddings[cols].to_numpy(float))
    out = embeddings.copy()
    out["scanpath_cluster"] = labels
    return out
