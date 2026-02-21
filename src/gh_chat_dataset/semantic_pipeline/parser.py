"""
=============================================================================
SCRIPT NAME: parser.py
=============================================================================

INPUT FILES:
- Repository source files under analysis (Python `.py`, Markdown `.md`).

OUTPUT FILES:
- None written directly. Returns `ParsedDocument` collections for downstream stages.

VERSION HISTORY:
- v1.0 (2025-09-28): Initial extraction utilities for semantic pipeline.

LAST UPDATED: 2025-09-28

NOTES:
- Uses tree-sitter grammars for structural parsing of Python modules.
- Markdown parsing relies on `markdown-it-py` for section-level segmentation.
=============================================================================
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List

from markdown_it import MarkdownIt

from ..semantic_types import ParsedDocument, Span

# Simplified parser without tree-sitter for now
_PY_PARSER = None

_MD = MarkdownIt()


def parse_repository(repo_path: Path) -> List[ParsedDocument]:
    documents: List[ParsedDocument] = []
    for path in sorted(repo_path.rglob("*")):
        if path.suffix == ".py":
            documents.append(_parse_python(path))
        elif path.suffix.lower() == ".md":
            documents.append(_parse_markdown(path))
    return documents


def _get_module_docstring(text: str) -> str:
    """Extract the module-level docstring from a Python file."""
    stripped = text.lstrip()
    if stripped.startswith('"""'):
        end = stripped.find('"""', 3)
        if end != -1:
            return stripped[: end + 3].strip()
    elif stripped.startswith("'''"):
        end = stripped.find("'''", 3)
        if end != -1:
            return stripped[: end + 3].strip()
    return ""


def _get_indent_level(line: str) -> int:
    """Return the number of leading spaces/tabs (tabs count as 4)."""
    count = 0
    for ch in line:
        if ch == " ":
            count += 1
        elif ch == "\t":
            count += 4
        else:
            break
    return count


def _find_block_end(lines: List[str], start_idx: int) -> int:
    """Find the last line index (0-based) of an indented block starting at start_idx."""
    if start_idx >= len(lines):
        return start_idx
    base_indent = _get_indent_level(lines[start_idx])
    end_idx = start_idx
    for j in range(start_idx + 1, len(lines)):
        line = lines[j]
        stripped = line.strip()
        if not stripped:
            continue
        if _get_indent_level(line) > base_indent:
            end_idx = j
        else:
            break
    return end_idx


def _parse_python(path: Path) -> ParsedDocument:
    text = path.read_text(encoding="utf-8", errors="ignore")
    spans: List[Span] = []
    lines = text.splitlines()

    module_docstring = _get_module_docstring(text)

    MIN_CONTENT_CHARS = 400

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Function definitions (top-level or class methods)
        if re.match(r"^[ \t]*def ", line) and "(" in stripped:
            end_idx = _find_block_end(lines, i)
            content = "\n".join(lines[i : end_idx + 1])
            if len(content.strip()) >= MIN_CONTENT_CHARS:
                full_content = content
                if module_docstring:
                    full_content = f"# File: {path.name}\n# Context: {module_docstring[:300]}\n\n{content}"
                spans.append(
                    Span(
                        source_path=path,
                        kind="function_definition",
                        content=full_content,
                        line_start=i + 1,
                        line_end=end_idx + 1,
                        metadata={"name": stripped.split("(")[0].replace("def ", "").strip()},
                    )
                )
            i = end_idx + 1
            continue

        # Class definitions
        elif re.match(r"^[ \t]*class ", line) and ":" in stripped:
            end_idx = _find_block_end(lines, i)
            content = "\n".join(lines[i : end_idx + 1])
            if len(content.strip()) >= MIN_CONTENT_CHARS:
                full_content = content
                if module_docstring:
                    full_content = f"# File: {path.name}\n# Context: {module_docstring[:300]}\n\n{content}"
                spans.append(
                    Span(
                        source_path=path,
                        kind="class_definition",
                        content=full_content,
                        line_start=i + 1,
                        line_end=end_idx + 1,
                        metadata={"name": stripped.split("(")[0].replace("class ", "").rstrip(":").strip()},
                    )
                )
            i = end_idx + 1
            continue

        i += 1

    return ParsedDocument(path=path, spans=spans)


def _parse_markdown(path: Path) -> ParsedDocument:
    text = path.read_text(encoding="utf-8", errors="ignore")
    tokens = _MD.parse(text)
    spans: List[Span] = []
    stack: List[str] = []
    section_start: int = 1
    current_title: str = "Document"

    lines = text.splitlines()
    for token in tokens:
        if token.type == "heading_open":
            level = int(token.tag.lstrip("h"))
            # Close existing section when encountering same or higher level
            if stack and level <= len(stack):
                section_text, section_end = _extract_section(lines, section_start, token.map[0])
                spans.append(
                    Span(
                        source_path=path,
                        kind="markdown_section",
                        content=section_text,
                        line_start=section_start,
                        line_end=section_end,
                        metadata={"title": current_title},
                    )
                )
            stack = stack[: level - 1]
            stack.append(token.tag)
            current_title = lines[token.map[0]].lstrip("# ") if token.map else "Section"
            section_start = token.map[0] + 1 if token.map else section_start
    # Capture trailing section
    section_text, section_end = _extract_section(lines, section_start, len(lines))
    spans.append(
        Span(
            source_path=path,
            kind="markdown_section",
            content=section_text,
            line_start=section_start,
            line_end=section_end,
            metadata={"title": current_title},
        )
    )

    return ParsedDocument(path=path, spans=spans)


def _extract_section(lines: List[str], start: int, end: int) -> tuple[str, int]:
    slice_lines = lines[start - 1 : end]
    return ("\n".join(slice_lines).strip(), end)
