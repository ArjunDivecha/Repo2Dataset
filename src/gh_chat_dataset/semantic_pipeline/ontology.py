"""
=============================================================================
SCRIPT NAME: ontology.py
=============================================================================

INPUT FILES:
- Parsed documents produced by `parser.parse_repository()`.

OUTPUT FILES:
- None written directly. Provides ontology tagging utilities.

VERSION HISTORY:
- v1.0 (2025-09-28): Initial heuristic tagging rules for financial contexts.

LAST UPDATED: 2025-09-28

NOTES:
- Lightweight heuristics identify domain-specific themes (factor timing, regimes).
- Future work can replace heuristics with ML classifiers.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Set

from ..semantic_types import Span


@dataclass(slots=True)
class OntologyTagger:
    """Assign ontology tags to spans based on keyword heuristics."""

    keyword_map: Dict[str, Set[str]]

    @classmethod
    def default(cls) -> "OntologyTagger":
        mapping: Dict[str, Set[str]] = {
            "factor": {"factor", "alpha", "exposure", "top20"},
            "regime": {"regime", "volatility", "dispersion", "momentum"},
            "optimizer": {"optimization", "target", "constraint", "solver"},
            "logging": {"logging.", "info(", "warning(", "error("},
            "validation": {"raise ", "ValueError", "assert "},
            "report": {"heatmap", "quilt", "chart", "report"},
        }
        return cls(keyword_map=mapping)

    def tag(self, spans: Iterable[Span]) -> List[List[str]]:
        tagged_results: List[List[str]] = []
        for span in spans:
            tags: Set[str] = set()
            content_lower = span.content.lower()
            for tag, keywords in self.keyword_map.items():
                if any(keyword.lower() in content_lower for keyword in keywords):
                    tags.add(tag)
            if span.kind == "logging_call":
                tags.add("logging")
            if span.kind == "module_constant":
                tags.add("config")
            tagged_tags = sorted(tags)
            span.metadata.setdefault("tags", [])
            for tag in tagged_tags:
                if tag not in span.metadata["tags"]:
                    span.metadata["tags"].append(tag)
            tagged_results.append(tagged_tags)
        return tagged_results
