import json
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import click

from .builders import (
    build_chat_from_js_jsdoc,
    build_chat_from_md_section,
    build_chat_from_py_docstring,
)
from .discover import discover_files
from .extract_js import extract_js_items
from .extract_md import split_markdown_sections
from .extract_py import extract_python_items
from .postprocess import dedupe_records, redact_secrets, within_budget
from .tokenize_util import count_tokens_approx


def run(cmd: List[str], cwd: Optional[str] = None) -> Tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)


def shallow_clone(repo_url: str, dest_dir: str) -> Tuple[str, str]:
    code, out = run(["git", "clone", "--depth=1", repo_url, dest_dir])
    if code != 0:
        raise RuntimeError(f"git clone failed: {out}")
    code, sha = run(["git", "rev-parse", "HEAD"], cwd=dest_dir)
    if code != 0:
        raise RuntimeError(f"git rev-parse HEAD failed: {sha}")
    return dest_dir, sha.strip()


def to_messages(user: str, assistant: str, system: Optional[str] = None) -> Dict:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    msgs.append({"role": "assistant", "content": assistant})
    return {"messages": msgs}


def build_records_for_repo(repo_path: Path, sha: str, allow_llm: bool) -> Iterable[Dict]:
    for path in discover_files(repo_path):
        rel = path.relative_to(repo_path).as_posix()
        meta = {"repo_path": str(repo_path), "path": rel, "sha": sha}
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix == ".py":
            for item in extract_python_items(rel, text):
                rec = build_chat_from_py_docstring(item, meta, allow_llm=allow_llm)
                if rec:
                    yield rec
        elif path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
            for item in extract_js_items(rel, text):
                rec = build_chat_from_js_jsdoc(item, meta, allow_llm=allow_llm)
                if rec:
                    yield rec
        elif path.suffix.lower() == ".md":
            for sec in split_markdown_sections(text):
                rec = build_chat_from_md_section(sec, meta, allow_llm=allow_llm)
                if rec:
                    yield rec


def apply_filters(records: Iterable[Dict], max_tokens: int) -> List[Dict]:
    out: List[Dict] = []
    for r in records:
        r = redact_secrets(r)
        if within_budget(r, max_tokens=max_tokens, tokenizer=count_tokens_approx):
            out.append(r)
    return dedupe_records(out)


def train_valid_split(
    records: List[Dict], valid_ratio: float = 0.1, seed: int = 17
) -> Tuple[List[Dict], List[Dict]]:
    rnd = random.Random(seed)
    perm = records[:]
    rnd.shuffle(perm)
    n_valid = max(1, int(len(perm) * valid_ratio)) if perm else 0
    return perm[n_valid:], perm[:n_valid]


def write_jsonl(path: Path, rows: Iterable[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


@click.command()
@click.option("--repo", required=True, help="GitHub repo URL (public)")
@click.option("--out", "out_dir", required=True, type=click.Path(), help="Output directory")
@click.option("--allow-llm", is_flag=True, default=False, help="Enable model-assisted labeling")
@click.option(
    "--max-tokens", default=2048, show_default=True, help="Max tokens (prompt+completion)"
)
def main(repo: str, out_dir: str, allow_llm: bool, max_tokens: int) -> None:
    tmp = tempfile.mkdtemp(prefix="gh-chat-ds-")
    repo_dir = Path(tmp) / "repo"
    try:
        cloned, sha = shallow_clone(repo, str(repo_dir))
        records_iter = build_records_for_repo(Path(cloned), sha, allow_llm=allow_llm)
        filtered = apply_filters(records_iter, max_tokens=max_tokens)
        train, valid = train_valid_split(filtered)
        outp = Path(out_dir)
        write_jsonl(outp / "dataset.train.jsonl", train)
        write_jsonl(outp / "dataset.valid.jsonl", valid)
        stats = {
            "total": len(filtered),
            "train": len(train),
            "valid": len(valid),
        }
        (outp / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
        click.echo(json.dumps({"sha": sha, "counts": stats}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":  # pragma: no cover
    main()
