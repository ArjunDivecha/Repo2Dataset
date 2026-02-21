"""
=============================================================================
SCRIPT NAME: synthesizer.py
=============================================================================

INPUT FILES:
- Semantic clusters produced by `cluster.SemanticClusterer` (in-memory objects).

OUTPUT FILES:
- None written directly. Generates `ConversationRecord` instances for serialization.

VERSION HISTORY:
- v1.0 (2025-09-28): Initial Anthropic + OpenAI synthesis implementation.

LAST UPDATED: 2025-09-28

NOTES:
- Uses Anthropic Claude for primary conversation generation.
- Uses OpenAI GPT for critique/quality review.
- Requires `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` environment variables.
=============================================================================
"""

from __future__ import annotations

import json
import uuid
from typing import Iterable, List, Sequence

from anthropic import Anthropic
from openai import OpenAI

from ..semantic_types import ConversationRecord, ConversationTurn, Span


class SemanticSynthesizer:
    def __init__(
        self,
        claude_model: str = "anthropic.claude-opus-4-6-v1",
        openai_model: str = "gpt-4.1-mini",
        max_tokens: int = 1800,
    ) -> None:
        self.anthropic = Anthropic()
        self.openai = OpenAI()
        self.claude_model = claude_model
        self.openai_model = openai_model
        self.max_tokens = max_tokens

    def generate(self, clusters: Sequence["Cluster"]) -> List[ConversationRecord]:
        conversations: List[ConversationRecord] = []
        for cluster in clusters:
            try:
                record = self._generate_for_cluster(cluster)
                if record:
                    conversations.append(record)
            except Exception as exc:  # pragma: no cover - resilience for API noise
                # In production we would log and continue; here we skip on failure
                continue
        return conversations

    def _generate_for_cluster(self, cluster: "Cluster") -> ConversationRecord | None:
        context = self._build_context(cluster.spans)
        system_prompt = (
            "You are a finance-focused AI documentation expert. "
            "Given source excerpts, produce a multi-turn conversation that explains the code, "
            "highlights validation/logging, and summarizes key financial insights. "
            "Always cite evidence using file paths and line ranges."
        )
        user_prompt = (
            "Create a JSON object with keys: conversation_id, turns (list of {role, content, evidence, metadata}), "
            "summary (with keys bullet_points, data_quality, risk_notes). Use the provided context strictly.\n\n"
            f"Context:\n{context}"
        )
        response = self.anthropic.messages.create(
            model=self.claude_model,
            max_tokens=self.max_tokens,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        data = self._parse_json(text)
        if not data:
            return None

        conversation_id = data.get("conversation_id") or f"cluster-{uuid.uuid4()}"
        turns_payload = data.get("turns", [])
        summary_payload = data.get("summary", {})
        turns: List[ConversationTurn] = []
        for turn in turns_payload:
            turns.append(
                ConversationTurn(
                    role=turn.get("role", "assistant"),
                    content=turn.get("content", ""),
                    evidence=turn.get("evidence", []),
                    metadata=turn.get("metadata", {}),
                )
            )

        critique = self._critique_conversation(text)

        source_files = sorted({span.source_path.as_posix() for span in cluster.spans})
        ontology_tags = list(cluster.ontology_tags)
        record = ConversationRecord(
            conversation_id=conversation_id,
            source_files=source_files,
            ontology_tags=ontology_tags,
            turns=turns,
            summary=summary_payload,
            critique=critique,
        )
        return record

    def _build_context(self, spans: Sequence[Span]) -> str:
        pieces: List[str] = []
        for idx, span in enumerate(spans, start=1):
            tags = ", ".join(span.metadata.get("tags", [])) or "none"
            piece = (
                f"Span {idx}:\n"
                f"Path: {span.source_path.as_posix()}\n"
                f"Lines: {span.line_start}-{span.line_end}\n"
                f"Tags: {tags}\n"
                f"Content:\n{span.content.strip()}\n"
            )
            pieces.append(piece)
        return "\n".join(pieces)

    def _parse_json(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                start = text.index("{")
                end = text.rindex("}") + 1
                return json.loads(text[start:end])
            except Exception:
                return None

    def _critique_conversation(self, conversation_json: str) -> str:
        prompt = (
            "Review the following JSON conversation for factual accuracy and clarity. "
            "Respond with concise critique (or 'OK' if solid).\n\n"
            f"{conversation_json}"
        )
        response = self.openai.chat.completions.create(
            model=self.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
        )
        return response.choices[0].message.content or ""
