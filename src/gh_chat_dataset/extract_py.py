import ast
from typing import Dict, Iterable, List


def extract_python_items(path: str, text: str) -> Iterable[Dict]:
    items: List[Dict] = []
    try:
        tree = ast.parse(text)
    except Exception:
        return items
    lines = text.splitlines()

    def segment(node: ast.AST) -> str:
        start = getattr(node, "lineno", 1) - 1
        end = getattr(node, "end_lineno", start + 1)
        return "\n".join(lines[start:end])

    # module docstring
    mod_doc = ast.get_docstring(tree) or ""
    if mod_doc:
        items.append({
            "kind": "Module",
            "name": None,
            "docstring": mod_doc.strip(),
            "code": text,
            "path": path,
        })

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node) or ""
            code = segment(node)
            name = getattr(node, "name", None)
            items.append({
                "kind": type(node).__name__,
                "name": name,
                "docstring": doc.strip(),
                "code": code,
                "path": path,
            })
    return items
