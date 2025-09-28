## gh-chat-dataset — turn any GitHub repo into Qwen/MLX chat training data

This CLI converts public GitHub repositories (Python / JS / TS + Markdown docs) into chat/messages JSONL for fine‑tuning. It produces diverse, deterministic pairs and preserves provenance.

Highlights
- Multi‑Q/A per markdown section with sliding windows
- Python function chunking for long defs
- Deterministic summaries: validation, error handling, config constants, logging flow
- Token budgets and per‑file caps to balance coverage

Quick start
```
pip install -e .[dev]

gh-chat-dataset \
  --repo https://github.com/pallets/itsdangerous.git \
  --out ./out \
  --md-max-questions-per-section 4 \
  --md-window-tokens 800 \
  --py-chunking --py-chunk-max 5 --py-chunk-min-lines 6 \
  --max-tokens 4096 --min-tokens 48 --file-cap 15
```

Key CLI options
- --repo URL: GitHub repo (public)
- --out PATH: output directory
- --allow-llm: optional LLM-assisted labeling (off by default)
- --max-tokens / --min-tokens: sample token bounds
- --file-cap: max samples per source file
- Markdown: --md-max-questions-per-section, --md-window-tokens
- Python: --py-chunking/--no-py-chunking, --py-chunk-max, --py-chunk-min-lines
- Extras: --include-validation/--include-errors/--include-config/--include-logging

Outputs
- out/dataset.train.jsonl
- out/dataset.valid.jsonl
- out/stats.json

What gets extracted
- Python: docstrings, code chunks, validation/error/logging/config summaries
- JS/TS: JSDoc pairs where present
- Markdown: H2–H4 sections, tables, and long sections via windows

Provenance
Each sample carries meta: { repo_path, path, sha, task, source_type [, name/title] }.

Notes
- LLM-assisted is OFF by default; enable with --allow-llm and provide your API key env if used.
- No license filtering by default; ensure downstream use complies with source licenses.
