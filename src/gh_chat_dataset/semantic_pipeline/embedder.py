"""
=============================================================================
SCRIPT NAME: embedder.py
=============================================================================

INPUT FILES:
- Parsed and tagged spans (in-memory structures, no direct file IO).

OUTPUT FILES:
- None written directly. Returns embedding vectors for downstream clustering.

VERSION HISTORY:
- v1.0 (2025-09-28): Initial OpenAI + optional cache implementation.

LAST UPDATED: 2025-09-28

NOTES:
- Uses OpenAI text-embedding-3-large by default.
- Supports local caching to minimize repeated API calls.
- Designed for batch operations for efficiency.
=============================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np
from openai import OpenAI

from ..semantic_types import Span


class OpenAIEmbedder:
    def __init__(
        self,
        model: str = "text-embedding-3-large",
        cache_dir: Optional[Path] = None,
    ) -> None:
        self.client = OpenAI()
        self.model = model
        self.cache_dir = cache_dir
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def embed_spans(self, spans: Sequence[Span]) -> np.ndarray:
        texts = [span.content for span in spans]
        if self.cache_dir:
            embeddings, missing_indices = self._load_cached(spans)
        else:
            embeddings = np.zeros((len(spans), 3072), dtype=np.float32)
            missing_indices = list(range(len(spans)))

        if missing_indices:
            batch = [texts[i] for i in missing_indices]
            response = self.client.embeddings.create(model=self.model, input=batch)
            for idx, embedding in zip(missing_indices, response.data):
                embeddings[idx] = np.array(embedding.embedding, dtype=np.float32)
                if self.cache_dir:
                    self._write_cache(spans[idx], embeddings[idx])
        return embeddings

    def _cache_path(self, span: Span) -> Path:
        name = f"{span.source_path.as_posix()}:{span.line_start}-{span.line_end}".replace("/", "_")
        return self.cache_dir / f"{hash(name)}.json"

    def _load_cached(self, spans: Sequence[Span]) -> Tuple[np.ndarray, List[int]]:
        embeddings = np.zeros((len(spans), 3072), dtype=np.float32)
        missing: List[int] = []
        for i, span in enumerate(spans):
            path = self._cache_path(span)
            if path.exists():
                data = json.loads(path.read_text())
                embeddings[i] = np.array(data["embedding"], dtype=np.float32)
            else:
                missing.append(i)
        return embeddings, missing

    def _write_cache(self, span: Span, vector: np.ndarray) -> None:
        path = self._cache_path(span)
        payload = {
            "embedding": vector.tolist(),
            "source": span.source_path.as_posix(),
            "lines": [span.line_start, span.line_end],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
