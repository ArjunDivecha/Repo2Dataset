"""
=============================================================================
MODULE NAME: semantic_types.py
=============================================================================

INPUT FILES:
- None (utility dataclasses only).

OUTPUT FILES:
- None written directly; structures feed downstream serialization.

VERSION HISTORY:
- v1.0 (2025-09-28): Initial introduction of semantic dataset dataclasses.

LAST UPDATED: 2025-09-28

NOTES:
- Provides strongly typed containers used across the semantic pipeline.
- Assumes downstream components populate metadata and summaries per conversation.
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence


@dataclass(slots=True)
class Span:
    """Represents a contiguous region of source material."""

    source_path: Path
    kind: str
    content: str
    line_start: int
    line_end: int
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    """Collection of spans extracted from a single file."""

    path: Path
    spans: List[Span]


@dataclass(slots=True)
class Cluster:
    """Grouping of semantically related spans."""

    cluster_id: str
    spans: Sequence[Span]
    ontology_tags: Sequence[str]
    centroid: Optional[List[float]] = None


@dataclass(slots=True)
class ConversationTurn:
    role: str
    content: str
    evidence: Sequence[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ConversationRecord:
    conversation_id: str
    source_files: Sequence[str]
    ontology_tags: Sequence[str]
    turns: Sequence[ConversationTurn]
    summary: Dict[str, str]
    critique: Optional[str] = None


__all__ = [
    "Span",
    "ParsedDocument",
    "Cluster",
    "ConversationTurn",
    "ConversationRecord",
]
