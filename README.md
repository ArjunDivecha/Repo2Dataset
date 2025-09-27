# gh-chat-dataset

Convert GitHub repositories to Qwen chat JSONL datasets for MLX fine-tuning.

## Features

- **Python AST extraction**: Functions, classes, module docstrings
- **JavaScript/TypeScript**: JSDoc comments and function bodies  
- **Markdown sections**: All `.md` files split by headings
- **Chat/messages format**: Qwen-compatible JSONL output
- **Post-processing**: Length filtering, deduplication
- **Train/valid split**: Configurable ratio (default 90/10)

## Installation

```bash
pip install -e .[dev]
```

## Usage

Convert a public GitHub repo:

```bash
gh-chat-dataset --repo https://github.com/owner/repo.git --out ./output --max-tokens 2048
```

Options:
- `--repo`: GitHub repository URL
- `--out`: Output directory  
- `--max-tokens`: Maximum tokens per sample (approximate)
- `--allow-llm`: Enable LLM-assisted labeling (stubbed)
- `--split-ratio`: Train/validation split ratio (default 0.9)

## Output

- `dataset.train.jsonl`: Training samples
- `dataset.valid.jsonl`: Validation samples  
- `stats.json`: Dataset statistics

### Sample Format

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful Python documentation assistant."},
    {"role": "user", "content": "Write a docstring for this function:\\n\\ndef hello(name): ..."},
    {"role": "assistant", "content": "Say hello to someone."}
  ],
  "meta": {
    "file_path": "src/utils.py",
    "task": "python_docstring",
    "kind": "FunctionDef"
  }
}
```

## Development

```bash
# Install with dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Lint
ruff check .
```