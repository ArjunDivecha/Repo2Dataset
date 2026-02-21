#!/usr/bin/env python3
"""
High-quality multi-format dataset generator for fine-tuning.

Generates SFT, DPO/ORPO, and GRPO datasets from a code repository in one run.
Output is drop-in compatible with the FineTuning project's data/ folder.
"""

import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')
except ImportError:
    pass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from gh_chat_dataset.semantic_pipeline.parser import parse_repository
from gh_chat_dataset.semantic_pipeline.ontology import OntologyTagger

from anthropic import Anthropic

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert software engineer and technical analyst. "
    "Answer questions about code with deep technical precision, using exact variable and function names, "
    "explaining design decisions, tradeoffs, and implementation details clearly."
)


def _make_system_prompt(repo_name: str) -> str:
    return (
        f"You are an expert in the `{repo_name}` codebase. "
        f"Answer questions about its code with deep technical precision, using exact variable and function names, "
        f"explaining design decisions, tradeoffs, and implementation details clearly."
    )

BOILERPLATE_PATTERNS = [
    "this code appears to be",
    "handles financial data processing",
    "financial data processing",
    "code analysis",
    "system component",
]

QUESTION_TEMPLATES = [
    ("explain",    "What does `{name}` do and why is it designed this way?"),
    ("domain",     "What is the domain-specific intuition behind the logic in `{name}`?"),
    ("connect",    "How does `{name}` fit into the broader `{repo}` system?"),
    ("implement",  "Walk through the key implementation decisions in `{name}` and what alternatives were considered."),
    ("debug",      "What are the edge cases or failure modes in `{name}` and how are they handled?"),
    ("compare",    "What are the tradeoffs in the approach taken by `{name}` compared to simpler alternatives?"),
]


def _is_boilerplate(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in BOILERPLATE_PATTERNS) or len(text.strip()) < 150


def _dedup_key(question: str, answer: str) -> str:
    return hashlib.md5(f"{question}|||{answer}".encode()).hexdigest()


def _span_name(span) -> str:
    return span.metadata.get("name") or span.source_path.stem


def _build_context(span) -> str:
    tags = ", ".join(span.metadata.get("tags", [])) or "none"
    return (
        f"File: {span.source_path.name}\n"
        f"Type: {span.kind}\n"
        f"Lines: {span.line_start}-{span.line_end}\n"
        f"Tags: {tags}\n\n"
        f"{span.content[:3500]}"
    )


class DatasetGenerator:
    def __init__(self, system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        self.client = Anthropic()
        self.seen_keys: set = set()
        self.success = 0
        self.skipped = 0
        self.system_prompt = system_prompt

    def _call_claude(self, user_prompt: str, max_tokens: int = 1000) -> Optional[str]:
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=0.4,
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return "".join(b.text for b in response.content if hasattr(b, "text"))
        except Exception as e:
            print(f"    Claude error: {e}")
            return None

    def generate_for_span(self, span, q_type: str, question_template: str, repo_name: str = "") -> Optional[Dict[str, Any]]:
        name = _span_name(span)
        question = question_template.format(name=name, repo=repo_name)
        context = _build_context(span)

        # --- Generate the GOOD answer ---
        good_prompt = (
            f"Answer this question about the following code. Be specific, use exact variable/function names, "
            f"and include financial reasoning where relevant. Write 3-6 paragraphs.\n\n"
            f"Question: {question}\n\n"
            f"Code:\n{context}"
        )
        good_answer = self._call_claude(good_prompt, max_tokens=1200)
        if not good_answer or _is_boilerplate(good_answer):
            self.skipped += 1
            return None

        # --- Generate the BAD answer (for DPO rejected) ---
        bad_prompt = (
            f"Write a deliberately vague, generic, unhelpful answer to this question. "
            f"Use AI-isms like 'it is important to note', 'this function handles', 'various operations'. "
            f"Do NOT mention specific variable names, numbers, or financial concepts. Keep it to 2 sentences.\n\n"
            f"Question: {question}"
        )
        bad_answer = self._call_claude(bad_prompt, max_tokens=200)
        if not bad_answer:
            bad_answer = f"This code handles various operations related to {span.kind.replace('_', ' ')}."

        # Dedup check
        key = _dedup_key(question, good_answer)
        if key in self.seen_keys:
            self.skipped += 1
            return None
        self.seen_keys.add(key)

        meta = {
            "source_file": span.source_path.name,
            "tags": span.metadata.get("tags", []),
            "question_type": q_type,
            "lines": f"{span.line_start}-{span.line_end}",
        }

        # --- SFT record ---
        sft = {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
                {"role": "assistant", "content": good_answer},
            ],
            "metadata": meta,
        }

        # --- DPO record ---
        dpo = {
            "prompt": question,
            "chosen": good_answer,
            "rejected": bad_answer,
            "metadata": meta,
        }

        # --- GRPO record ---
        grpo = {
            "prompt": question,
            "reference": span.content[:3000],
            "metadata": meta,
        }

        self.success += 1
        return {"sft": sft, "dpo": dpo, "grpo": grpo}

    def generate_dataset(
        self,
        repo_path: Path,
        output_dir: Path,
        dataset_name: str = "country_factor",
        max_spans: int = 200,
    ) -> Dict[str, Any]:
        print(f"Parsing repository: {repo_path}")
        documents = parse_repository(repo_path)
        spans = [s for doc in documents for s in doc.spans]

        tagger = OntologyTagger.default()
        tagger.tag(spans)

        # Filter to meaningful spans only
        meaningful = [
            s for s in spans
            if s.kind in ("function_definition", "class_definition", "markdown_section")
            and len(s.content.strip()) >= 400
        ]
        print(f"Found {len(spans)} total spans → {len(meaningful)} meaningful")

        # Build work list: each span gets one question type (rotate through templates)
        work: List[Tuple] = []
        for idx, span in enumerate(meaningful[:max_spans]):
            q_type, template = QUESTION_TEMPLATES[idx % len(QUESTION_TEMPLATES)]
            work.append((span, q_type, template))

        print(f"Generating {len(work)} records across SFT / DPO / GRPO formats...")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Open all output files upfront for incremental writing
        raw_sft_path = output_dir / f"{dataset_name}_sft_raw.jsonl"
        raw_dpo_path = output_dir / f"{dataset_name}_dpo_raw.jsonl"
        raw_grpo_path = output_dir / f"{dataset_name}_grpo_raw.jsonl"

        sft_records: List[Dict] = []
        dpo_records: List[Dict] = []
        grpo_records: List[Dict] = []

        with open(raw_sft_path, "w", encoding="utf-8") as f_sft, \
             open(raw_dpo_path, "w", encoding="utf-8") as f_dpo, \
             open(raw_grpo_path, "w", encoding="utf-8") as f_grpo:

            for i, (span, q_type, template) in enumerate(work):
                print(f"  [{i+1}/{len(work)}] {span.source_path.name} ({q_type})")
                result = self.generate_for_span(span, q_type, template, repo_name=repo_path.name)
                if result:
                    sft_records.append(result["sft"])
                    dpo_records.append(result["dpo"])
                    grpo_records.append(result["grpo"])
                    f_sft.write(json.dumps(result["sft"], ensure_ascii=False) + "\n")
                    f_dpo.write(json.dumps(result["dpo"], ensure_ascii=False) + "\n")
                    f_grpo.write(json.dumps(result["grpo"], ensure_ascii=False) + "\n")
                    f_sft.flush()
                    f_dpo.flush()
                    f_grpo.flush()
                    print(f"    ✓ ({self.success} good, {self.skipped} skipped)")
                else:
                    print(f"    ✗ skipped")
                time.sleep(0.3)

        # Shuffle and split 90/5/5
        def split(records):
            random.shuffle(records)
            n = len(records)
            t = int(n * 0.90)
            v = int(n * 0.95)
            return records[:t], records[t:v], records[v:]

        stats = {}
        for fmt, records in [("sft", sft_records), ("dpo", dpo_records), ("grpo", grpo_records)]:
            train, valid, test = split(list(records))
            for split_name, split_records in [("train", train), ("valid", valid), ("test", test)]:
                fname = output_dir / f"{dataset_name}_{fmt}_{split_name}.jsonl"
                with open(fname, "w", encoding="utf-8") as f:
                    for rec in split_records:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            stats[fmt] = {"total": len(records), "train": len(train), "valid": len(valid), "test": len(test)}

        # Clean up raw files after successful split
        for p in [raw_sft_path, raw_dpo_path, raw_grpo_path]:
            p.unlink(missing_ok=True)

        stats["success"] = self.success
        stats["skipped"] = self.skipped

        with open(output_dir / f"{dataset_name}_stats.json", "w") as f:
            json.dump(stats, f, indent=2)

        return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate fine-tuning datasets from a code repo")
    parser.add_argument("--repo", default="./Country-Factor-Momentum-Strategy", help="Path to repository")
    parser.add_argument("--out", default="./country_factor_output_final2", help="Output directory")
    parser.add_argument("--name", default="country_factor", help="Dataset name prefix")
    parser.add_argument("--max-spans", type=int, default=10000, help="Max spans to process")
    args = parser.parse_args()

    repo_path = Path(args.repo)
    if not repo_path.exists():
        print(f"Error: Repository not found at {repo_path}")
        sys.exit(1)

    system_prompt = _make_system_prompt(repo_path.name)
    gen = DatasetGenerator(system_prompt=system_prompt)
    stats = gen.generate_dataset(
        repo_path=repo_path,
        output_dir=Path(args.out),
        dataset_name=args.name,
        max_spans=args.max_spans,
    )

    print(f"\n✅ Done!")
    for fmt in ("sft", "dpo", "grpo"):
        s = stats[fmt]
        print(f"  {fmt.upper()}: {s['total']} total ({s['train']} train / {s['valid']} valid / {s['test']} test)")
    print(f"  Success: {stats['success']}, Skipped: {stats['skipped']}")
    print(f"  Output: {args.out}")
