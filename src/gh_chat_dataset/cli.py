import json
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, DefaultDict, Dict, Iterable, List, Optional, Tuple

import click

from .builders import (
    build_chat_from_js_jsdoc,
    build_chat_from_py_chunk,
    build_chat_from_py_docstring,
    build_chats_from_md_section,
    build_config_constants_summary_py,
    build_error_handling_summary_py,
    build_logging_flow_summary_py,
    build_validation_summary_py,
)
from .discover import discover_files
from .extract_js import extract_js_items
from .extract_md import split_markdown_sections
from .extract_py import extract_python_items
from .postprocess import dedupe_records, redact_secrets
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


def _chunk_code_by_blanklines(code: str, min_lines: int, max_chunks: int) -> List[str]:
    lines = code.splitlines()
    chunks: List[List[str]] = [[]]
    for ln in lines:
        if ln.strip() == "" and len(chunks[-1]) >= min_lines:
            if chunks[-1]:
                chunks.append([])
            continue
        chunks[-1].append(ln)
    # finalize
    parts = ["\n".join(c).strip() for c in chunks if len(c) >= min_lines]
    if len(parts) > max_chunks:
        parts = parts[:max_chunks]
    return [p for p in parts if p]


def build_records_for_repo(
    repo_path: Path,
    sha: str,
    allow_llm: bool,
    md_max_questions: int,
    md_window_tokens: int,
    py_chunking: bool,
    py_chunk_max: int,
    py_chunk_min_lines: int,
    include_validation: bool,
    include_errors: bool,
    include_config: bool,
    include_logging: bool,
) -> Iterable[Dict]:
    for path in discover_files(repo_path):
        rel = path.relative_to(repo_path).as_posix()
        meta = {"repo_path": str(repo_path), "path": rel, "sha": sha}
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix == ".py":
            for item in extract_python_items(rel, text):
                # Primary docstring task
                rec = build_chat_from_py_docstring(item, meta, allow_llm=allow_llm)
                if rec:
                    yield rec
                # Optional chunked explanations
                if py_chunking and item.get("code"):
                    chunks = _chunk_code_by_blanklines(item["code"], py_chunk_min_lines, py_chunk_max)
                    for ch in chunks:
                        crec = build_chat_from_py_chunk(item, ch, meta)
                        if crec:
                            yield crec
                # Additional deterministic tasks
                code = item.get("code", "")
                if include_validation:
                    v = build_validation_summary_py(code, meta)
                    if v:
                        yield v
                if include_errors:
                    e = build_error_handling_summary_py(code, meta)
                    if e:
                        yield e
                if include_logging:
                    log_rec = build_logging_flow_summary_py(code, meta)
                    if log_rec:
                        yield log_rec
        elif path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
            for item in extract_js_items(rel, text):
                rec = build_chat_from_js_jsdoc(item, meta, allow_llm=allow_llm)
                if rec:
                    yield rec
        elif path.suffix.lower() == ".md":
            for sec in split_markdown_sections(text):
                for rec in build_chats_from_md_section(
                    sec,
                    meta,
                    max_questions=md_max_questions,
                    window_tokens=md_window_tokens,
                ):
                    yield rec
        # Module-level constants summary (once per file for .py)
        if path.suffix == ".py" and include_config:
            c = build_config_constants_summary_py(text, meta)
            if c:
                yield c


def apply_filters(
    records: Iterable[Dict],
    max_tokens: int,
    min_tokens: int,
    file_cap: int,
) -> List[Dict]:
    out: List[Dict] = []
    per_file: DefaultDict[str, int] = DefaultDict(int)
    for r in records:
        r = redact_secrets(r)
        total = 0
        for m in r.get("messages", []):
            c = m.get("content", "")
            if isinstance(c, str):
                total += count_tokens_approx(c)
        if total < min_tokens:
            continue
        if total > max_tokens:
            continue
        p = r.get("meta", {}).get("path", "")
        if per_file[p] >= file_cap:
            continue
        per_file[p] += 1
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


def generate_dataset(
    repo: str,
    out_dir: str,
    allow_llm: bool,
    max_tokens: int,
    min_tokens: int,
    file_cap: int,
    md_max_questions_per_section: int,
    md_window_tokens: int,
    py_chunking: bool,
    py_chunk_max: int,
    py_chunk_min_lines: int,
    include_validation: bool,
    include_errors: bool,
    include_config: bool,
    include_logging: bool,
    progress_cb: Optional[Callable[[str, int], None]] = None,
) -> Dict:
    """
    Generate a dataset from a GitHub repository.

    Args:
        repo: GitHub repo URL
        out_dir: Output directory path
        allow_llm: Enable model-assisted labeling
        max_tokens: Maximum tokens per sample
        min_tokens: Minimum tokens per sample
        file_cap: Maximum samples per file
        md_max_questions_per_section: Max Q/A per MD section
        md_window_tokens: Window size for MD sections
        py_chunking: Enable Python chunking
        py_chunk_max: Max chunks per function
        py_chunk_min_lines: Min lines per chunk
        include_validation: Include validation summaries
        include_errors: Include error handling summaries
        include_config: Include config summaries
        include_logging: Include logging summaries
        progress_cb: Optional callback(message, progress_percent)

    Returns:
        Dict with 'sha' and 'counts' keys
    """
    if progress_cb:
        progress_cb("Starting dataset generation...", 0)

    tmp = tempfile.mkdtemp(prefix="gh-chat-ds-")
    repo_dir = Path(tmp) / "repo"
    try:
        if progress_cb:
            progress_cb(f"Cloning repository: {repo}", 5)

        cloned, sha = shallow_clone(repo, str(repo_dir))

        if progress_cb:
            progress_cb(f"Cloned successfully (SHA: {sha[:8]})", 10)

        if progress_cb:
            progress_cb("Building records from repository...", 20)

        records_iter = build_records_for_repo(
            Path(cloned),
            sha,
            allow_llm=allow_llm,
            md_max_questions=md_max_questions_per_section,
            md_window_tokens=md_window_tokens,
            py_chunking=py_chunking,
            py_chunk_max=py_chunk_max,
            py_chunk_min_lines=py_chunk_min_lines,
            include_validation=include_validation,
            include_errors=include_errors,
            include_config=include_config,
            include_logging=include_logging,
        )

        if progress_cb:
            progress_cb("Filtering records...", 60)

        filtered = apply_filters(
            records_iter,
            max_tokens=max_tokens,
            min_tokens=min_tokens,
            file_cap=file_cap,
        )

        if progress_cb:
            progress_cb(f"Found {len(filtered)} records. Splitting train/valid...", 70)

        train, valid = train_valid_split(filtered)

        if progress_cb:
            progress_cb(f"Writing output files ({len(train)} train, {len(valid)} valid)...", 90)

        outp = Path(out_dir)
        write_jsonl(outp / "dataset.train.jsonl", train)
        write_jsonl(outp / "dataset.valid.jsonl", valid)

        stats = {
            "total": len(filtered),
            "train": len(train),
            "valid": len(valid),
        }
        (outp / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

        if progress_cb:
            progress_cb("Dataset generation complete!", 100)

        return {"sha": sha, "counts": stats}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@click.command()
@click.option("--repo", required=True, help="GitHub repo URL (public)")
@click.option("--out", "out_dir", required=True, type=click.Path(), help="Output directory")
@click.option("--allow-llm", is_flag=True, default=False, help="Enable model-assisted labeling")
@click.option("--max-tokens", default=4096, show_default=True, help="Max tokens per sample")
@click.option("--min-tokens", default=48, show_default=True, help="Min tokens per sample")
@click.option("--file-cap", default=15, show_default=True, help="Max samples per file")
@click.option("--md-max-questions-per-section", default=4, show_default=True, help="Max Q/A per MD section")
@click.option("--md-window-tokens", default=800, show_default=True, help="Window size for long MD sections")
@click.option("--py-chunking/--no-py-chunking", default=True, help="Enable chunking long Python functions")
@click.option("--py-chunk-max", default=5, show_default=True, help="Max chunks per function")
@click.option("--py-chunk-min-lines", default=6, show_default=True, help="Min lines per chunk")
@click.option("--include-validation/--no-include-validation", default=True, help="Add input validation summaries")
@click.option("--include-errors/--no-include-errors", default=True, help="Add error handling summaries")
@click.option("--include-config/--no-include-config", default=True, help="Add config constants summaries")
@click.option("--include-logging/--no-include-logging", default=True, help="Add logging flow summaries")
def main(
    repo: str,
    out_dir: str,
    allow_llm: bool,
    max_tokens: int,
    min_tokens: int,
    file_cap: int,
    md_max_questions_per_section: int,
    md_window_tokens: int,
    py_chunking: bool,
    py_chunk_max: int,
    py_chunk_min_lines: int,
    include_validation: bool,
    include_errors: bool,
    include_config: bool,
    include_logging: bool,
) -> None:
    result = generate_dataset(
        repo=repo,
        out_dir=out_dir,
        allow_llm=allow_llm,
        max_tokens=max_tokens,
        min_tokens=min_tokens,
        file_cap=file_cap,
        md_max_questions_per_section=md_max_questions_per_section,
        md_window_tokens=md_window_tokens,
        py_chunking=py_chunking,
        py_chunk_max=py_chunk_max,
        py_chunk_min_lines=py_chunk_min_lines,
        include_validation=include_validation,
        include_errors=include_errors,
        include_config=include_config,
        include_logging=include_logging,
        progress_cb=lambda msg, pct: None,  # No progress callback for CLI
    )
    click.echo(json.dumps(result))


if __name__ == "__main__":  # pragma: no cover
    main()
