import re
from typing import Dict, Iterable, List

JSDOC_RE = re.compile(r"/\*\*([\s\S]*?)\*/\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(", re.MULTILINE)
FUNC_RE = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\([^)]*\)\s*{", re.MULTILINE)


def extract_js_items(path: str, text: str) -> Iterable[Dict]:
    items: List[Dict] = []
    for m in JSDOC_RE.finditer(text):
        jsdoc = m.group(1).strip()
        name = m.group(2)
        func_start = FUNC_RE.search(text, pos=m.start())
        if not func_start:
            continue
        body_start = func_start.end() - 1
        depth = 0
        i = body_start
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        code = text[func_start.start():i]
        items.append({
            "kind": "Function",
            "name": name,
            "jsdoc": jsdoc,
            "code": code,
            "path": path,
        })
    return items
