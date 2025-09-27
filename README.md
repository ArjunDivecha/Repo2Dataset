## gh-chat-dataset

One-shot CLI to convert a public GitHub repository (Python/JS/TS + Markdown docs) into chat/messages JSONL suitable for Qwen fine-tuning with MLX.

Usage:

```
gh-chat-dataset --repo https://github.com/owner/repo.git --out ./out --allow-llm false
```

Outputs:
- out/dataset.train.jsonl
- out/dataset.valid.jsonl
- out/stats.json

Notes:
- LLM-assisted labeling is optional and OFF by default. Enable with `--allow-llm true` and implement a provider via environment variables (left as a stub).
- This tool stores basic provenance metadata (repo, path, sha, task, source_type). No license filtering is applied by default.
