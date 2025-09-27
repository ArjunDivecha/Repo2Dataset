from pathlib import Path
from typing import Iterable

EXCLUDE_DIRS = {".git", "node_modules", "dist", "build", "venv", ".venv", "__pycache__"}
CODE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".md"}


def discover_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_dir():
            if p.name in EXCLUDE_DIRS:
                # skip walking inside excluded directories
                yield from []
            continue
        if p.suffix in CODE_EXTS:
            yield p
