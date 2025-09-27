"""JavaScript/TypeScript JSDoc extraction utilities."""

import re
from pathlib import Path
from typing import Dict, List


def extract_js_items(file_path: Path, content: str) -> List[Dict]:
    """Extract JSDoc + function pairs from JS/TS code."""
    items = []

    # Pattern for JSDoc comment followed by function
    jsdoc_func_pattern = re.compile(
        r"/\\*\\*(.*?)\\*/\\s*"  # JSDoc comment
        r"(?:export\\s+)?"  # Optional export
        r"(?:async\\s+)?"   # Optional async
        r"(?:function\\s+([a-zA-Z0-9_$]+)|"  # Named function
        r"(?:const|let|var)\\s+([a-zA-Z0-9_$]+)\\s*=\\s*"  # Arrow function
        r"(?:async\\s+)?\\([^)]*\\)\\s*=>)",
        re.DOTALL | re.MULTILINE
    )

    for match in jsdoc_func_pattern.finditer(content):
        jsdoc = match.group(1).strip()
        func_name = match.group(2) or match.group(3) or "anonymous"

        # Extract function body (naive approach)
        jsdoc_end = match.end()

        # Find the function definition after JSDoc
        func_match = re.search(
            r"(?:export\\s+)?(?:async\\s+)?(?:function\\s+\\w+|"
            r"(?:const|let|var)\\s+\\w+\\s*=\\s*(?:async\\s+)?\\([^)]*\\)\\s*=>)",
            content[jsdoc_end:]
        )

        if func_match:
            # Try to find the complete function (simplified)
            brace_pos = content.find("{", jsdoc_end + func_match.start())
            if brace_pos != -1:
                # Count braces to find function end
                depth = 0
                i = brace_pos
                while i < len(content):
                    if content[i] == "{":
                        depth += 1
                    elif content[i] == "}":
                        depth -= 1
                        if depth == 0:
                            func_code = content[jsdoc_end + func_match.start():i + 1]
                            items.append({
                                "kind": "Function",
                                "name": func_name,
                                "jsdoc": jsdoc,
                                "code": func_code.strip(),
                                "file_path": str(file_path),
                            })
                            break
                    i += 1

    return items
