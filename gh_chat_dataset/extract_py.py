"""Python AST extraction utilities."""

import ast
from pathlib import Path
from typing import Dict, List


def extract_python_items(file_path: Path, content: str) -> List[Dict]:
    """Extract functions, classes, and module docstrings from Python code."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    lines = content.splitlines()
    items = []

    def get_source_segment(node):
        """Get source code for an AST node."""
        start = node.lineno - 1
        end = getattr(node, "end_lineno", start + 1)
        return "\n".join(lines[start:end])

    # Module docstring
    module_doc = ast.get_docstring(tree)
    if module_doc and module_doc.strip():
        items.append({
            "kind": "Module",
            "name": file_path.name,
            "docstring": module_doc.strip(),
            "code": content,
            "file_path": str(file_path),
        })

    # Functions and classes
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node)
            if docstring and docstring.strip():
                code = get_source_segment(node)
                items.append({
                    "kind": type(node).__name__,
                    "name": getattr(node, "name", None),
                    "docstring": docstring.strip(),
                    "code": code,
                    "file_path": str(file_path),
                })

    return items
