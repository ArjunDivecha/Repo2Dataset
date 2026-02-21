"""
=============================================================================
SCRIPT NAME: cluster.py
=============================================================================

INPUT FILES:
- Embedding matrices computed by `embedder.OpenAIEmbedder` (in-memory arrays).

OUTPUT FILES:
- None written directly. Returns semantic clusters for downstream LLM synthesis.

VERSION HISTORY:
- v1.0 (2025-09-28): Initial HDBSCAN + FAISS clustering implementation.

LAST UPDATED: 2025-09-28

NOTES:
- Uses FAISS for nearest-neighbor indexing and HDBSCAN for density-based clustering.
- Falls back to singletons when clusters cannot be formed.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import faiss
import numpy as np
from hdbscan import HDBSCAN

from ..semantic_types import Cluster, Span


@dataclass(slots=True)
class ClusteringConfig:
    min_cluster_size: int = 5
    min_samples: int = 3
    metric: str = "euclidean"
    faiss_nprobe: int = 10


class SemanticClusterer:
    def __init__(self, config: ClusteringConfig | None = None) -> None:
        self.config = config or ClusteringConfig()

    def cluster(self, spans: Sequence[Span], embeddings: np.ndarray) -> List[Cluster]:
        if len(spans) != embeddings.shape[0]:
            raise ValueError("Span count must match embedding rows")
        if len(spans) == 0:
            return []

        normalized = self._normalize(embeddings)
        labels = self._run_hdbscan(normalized)

        clusters: Dict[int, List[int]] = {}
        for idx, label in enumerate(labels):
            clusters.setdefault(label, []).append(idx)

        records: List[Cluster] = []
        singleton_counter = 0
        for label, indices in clusters.items():
            cluster_spans = [spans[i] for i in indices]
            centroid = normalized[indices].mean(axis=0).tolist()
            ontology_tags = sorted({tag for span in cluster_spans for tag in (span.metadata.get("tags", []) or [])})
            if label == -1:
                for span_index in indices:
                    singleton_counter += 1
                    span = spans[span_index]
                    records.append(
                        Cluster(
                            cluster_id=f"singleton-{singleton_counter}",
                            spans=[span],
                            ontology_tags=span.metadata.get("tags", []),
                            centroid=normalized[span_index].tolist(),
                        )
                    )
            else:
                records.append(
                    Cluster(
                        cluster_id=f"cluster-{label}",
                        spans=cluster_spans,
                        ontology_tags=ontology_tags,
                        centroid=centroid,
                    )
                )
        return records

    def _normalize(self, embeddings: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return embeddings / norms

    def _run_hdbscan(self, vectors: np.ndarray) -> np.ndarray:
        reducer = HDBSCAN(
            min_cluster_size=self.config.min_cluster_size,
            min_samples=self.config.min_samples,
            metric=self.config.metric,
        )
        return reducer.fit_predict(vectors)
