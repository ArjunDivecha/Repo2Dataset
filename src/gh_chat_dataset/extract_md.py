import re
from typing import Dict, List


def split_markdown_sections(text: str) -> List[Dict]:
    sections: List[Dict] = []
    current = {"title": "", "content": []}
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s", line):
            if current["content"]:
                sections.append({
                    "title": current["title"],
                    "content": "\n".join(current["content"]).strip(),
                })
            current = {"title": line.lstrip("# ").strip(), "content": []}
        else:
            current["content"].append(line)
    if current["content"]:
        sections.append({
            "title": current["title"],
            "content": "\n".join(current["content"]).strip(),
        })
    return [s for s in sections if s["content"]]
