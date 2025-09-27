"""File discovery utilities."""

from pathlib import Path
from typing import List


def find_files(repo_path: Path) -> List[Path]:
    """Find Python, JS/TS, and Markdown files in a repo."""
    patterns = ["**/*.py", "**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.md"]
    exclude_dirs = {
        ".git",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        "build",
        "dist",
        ".venv",
        "venv",
        ".mypy_cache",
        "coverage",
    }

    files = []
    for pattern in patterns:
        for file_path in repo_path.glob(pattern):
            # Skip if any parent dir is in exclude list
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            if file_path.is_file():
                files.append(file_path)

    return sorted(files)
