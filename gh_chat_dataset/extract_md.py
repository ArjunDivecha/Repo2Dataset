"""Markdown section extraction utilities."""

import re
from pathlib import Path
from typing import Dict, List


def extract_markdown_sections(file_path: Path, content: str) -> List[Dict]:
    """Extract sections from Markdown files based on headings."""
    sections = []
    current_section = {"title": "", "content": []}

    for line in content.splitlines():
        # Check if line is a heading (# ## ### etc.)
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

        if heading_match:
            # Save previous section if it has content
            if current_section["content"]:
                content_text = "\n".join(current_section["content"]).strip()
                if content_text:
                    sections.append({
                        "kind": "Section",
                        "title": current_section["title"],
                        "content": content_text,
                        "file_path": str(file_path),
                        "level": len(heading_match.group(1)),
                    })

            # Start new section
            current_section = {
                "title": heading_match.group(2).strip(),
                "content": []
            }
        else:
            # Add line to current section
            current_section["content"].append(line)

    # Don't forget the last section
    if current_section["content"]:
        content_text = "\n".join(current_section["content"]).strip()
        if content_text:
            sections.append({
                "kind": "Section",
                "title": current_section["title"],
                "content": content_text,
                "file_path": str(file_path),
                "level": 1,  # Default level for last section
            })

    return sections
