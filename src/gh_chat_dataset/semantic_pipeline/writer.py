"""
=============================================================================
SCRIPT NAME: writer.py
=============================================================================

INPUT FILES:
- Parsed and clustered conversation records (in-memory structures).

OUTPUT FILES:
- semantic.train.jsonl: Training conversations.
- semantic.valid.jsonl: Validation conversations.
- semantic.stats.json: Dataset summary statistics.

VERSION HISTORY:
- v1.0 (2025-09-28): Initial serializer for semantic dataset output.

LAST UPDATED: 2025-09-28

NOTES:
- Responsible for train/valid split and JSONL serialization.
- Maintains evidence metadata for transparency.
=============================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence

from ..semantic_types import ConversationRecord, Span


class SemanticWriter:
    """Serialize semantic conversations to JSON Lines."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, conversations: Sequence[ConversationRecord]) -> None:
        train_path = self.output_dir / "semantic.train.jsonl"
        valid_path = self.output_dir / "semantic.valid.jsonl"
        stats_path = self.output_dir / "semantic.stats.json"

        records = list(conversations)
        train, valid = self._split(records)

        self._write_jsonl(train_path, train)
        self._write_jsonl(valid_path, valid)
        stats = {
            "total": len(records),
            "train": len(train),
            "valid": len(valid),
        }
        stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    def _write_jsonl(self, path: Path, records: Sequence[ConversationRecord]) -> None:
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(self._to_dict(record), ensure_ascii=False) + "\n")

    def _split(
        self, records: Sequence[ConversationRecord], valid_ratio: float = 0.1
    ) -> tuple[List[ConversationRecord], List[ConversationRecord]]:
        size = int(len(records) * valid_ratio)
        return list(records[size:]), list(records[:size])

    def _to_dict(self, record: ConversationRecord) -> Dict:
        return {
            "conversation_id": record.conversation_id,
            "source_files": list(record.source_files),
            "ontology_tags": list(record.ontology_tags),
            "turns": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "evidence": list(turn.evidence),
                    "metadata": turn.metadata,
                }
                for turn in record.turns
            ],
            "summary": record.summary,
            "critique": record.critique,
        }


class SpanCollector:
    def __init__(self) -> None:
        self._spans_by_file: Dict[Path, List[Span]] = defaultdict(list)

    def add(self, span: Span) -> None:
        self._spans_by_file[span.source_path].append(span)

    def iter_spans(self) -> Iterator[Span]:
        for spans in self._spans_by_file.values():
            yield from spans

    def group_by_file(self) -> Dict[Path, List[Span]]:
        return self._spans_by_file
