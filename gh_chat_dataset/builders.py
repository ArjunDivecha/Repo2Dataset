"""Chat message builders for different content types."""

from pathlib import Path
from typing import Dict, List

from . import extract_js, extract_md, extract_py


def build_samples_from_file(
    file_path: Path, repo_path: Path, allow_llm: bool = False
) -> List[Dict]:
    """Build chat samples from a single file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return []

    rel_path = file_path.relative_to(repo_path)
    samples = []

    if file_path.suffix == ".py":
        items = extract_py.extract_python_items(rel_path, content)
        for item in items:
            sample = build_python_docstring_sample(item)
            if sample:
                samples.append(sample)

    elif file_path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
        items = extract_js.extract_js_items(rel_path, content)
        for item in items:
            sample = build_js_jsdoc_sample(item)
            if sample:
                samples.append(sample)

    elif file_path.suffix == ".md":
        sections = extract_md.extract_markdown_sections(rel_path, content)
        for section in sections:
            sample = build_markdown_qa_sample(section)
            if sample:
                samples.append(sample)

    # TODO: LLM-assisted labeling when allow_llm=True
    if allow_llm:
        pass  # Stub for model-assisted sample generation

    return samples


def build_python_docstring_sample(item: Dict) -> Dict:
    """Build chat sample for Python docstring task."""
    if not item.get("docstring") or not item.get("code"):
        return None

    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful Python code documentation assistant.",
            },
            {
                "role": "user",
                "content": (
                    f"Write a clear, concise docstring for this "
                    f"{item['kind'].lower()}:\n\n{item['code']}"
                ),
            },
            {"role": "assistant", "content": item["docstring"]},
        ],
        "meta": {
            "file_path": item["file_path"],
            "kind": item["kind"],
            "name": item.get("name"),
            "task": "python_docstring",
        },
    }


def build_js_jsdoc_sample(item: Dict) -> Dict:
    """Build chat sample for JSDoc task."""
    if not item.get("jsdoc") or not item.get("code"):
        return None

    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful JavaScript/TypeScript documentation "
                    "assistant."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Write a JSDoc comment for this function:\n\n{item['code']}"
                ),
            },
            {"role": "assistant", "content": item["jsdoc"]},
        ],
        "meta": {
            "file_path": item["file_path"],
            "kind": item["kind"],
            "name": item.get("name"),
            "task": "js_jsdoc",
        },
    }


def build_markdown_qa_sample(section: Dict) -> Dict:
    """Build chat sample for Markdown Q&A task."""
    if not section.get("title") or not section.get("content"):
        return None

    # Skip very short sections
    if len(section["content"]) < 50:
        return None

    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful documentation assistant.",
            },
            {
                "role": "user",
                "content": f"Explain the section titled '{section['title']}'.",
            },
            {"role": "assistant", "content": section["content"]},
        ],
        "meta": {
            "file_path": section["file_path"],
            "kind": section["kind"],
            "title": section["title"],
            "task": "markdown_qa",
        },
    }
