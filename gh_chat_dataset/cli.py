"""CLI interface for gh-chat-dataset."""

import json
import tempfile
from pathlib import Path

import click
from git import Repo

from . import builders, discover, postprocess


@click.command()
@click.option(
    "--repo", required=True, help="GitHub repo URL (https://github.com/owner/repo.git)"
)
@click.option("--out", required=True, help="Output directory")
@click.option(
    "--max-tokens", default=2048, help="Max tokens per sample (approx)", type=int
)
@click.option(
    "--allow-llm", is_flag=True, help="Enable LLM-assisted labeling (stubbed)"
)
@click.option("--split-ratio", default=0.9, help="Train/valid split ratio", type=float)
def main(repo, out, max_tokens, allow_llm, split_ratio):
    """Convert GitHub repo to Qwen chat JSONL for MLX fine-tuning."""
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Clone repo
        click.echo(f"Cloning {repo}...")
        repo_obj = Repo.clone_from(repo, tmp_dir, depth=1)
        sha = repo_obj.head.commit.hexsha
        click.echo(f"SHA: {sha}")

        # Discover files
        repo_path = Path(tmp_dir)
        files = discover.find_files(repo_path)
        click.echo(f"Found {len(files)} files")

        # Extract and build samples
        samples = []
        for file_path in files:
            file_samples = builders.build_samples_from_file(
                file_path, repo_path, allow_llm=allow_llm
            )
            samples.extend(file_samples)

        click.echo(f"Extracted {len(samples)} raw samples")

        # Post-process
        samples = postprocess.filter_samples(samples, max_tokens=max_tokens)
        click.echo(f"After filtering: {len(samples)} samples")

        # Split train/valid
        import random

        random.shuffle(samples)
        split_idx = int(len(samples) * split_ratio)
        train_samples = samples[:split_idx]
        valid_samples = samples[split_idx:]

        # Export
        train_path = out_path / "dataset.train.jsonl"
        valid_path = out_path / "dataset.valid.jsonl"
        stats_path = out_path / "stats.json"

        _write_jsonl(train_path, train_samples)
        _write_jsonl(valid_path, valid_samples)

        stats = {
            "sha": sha,
            "counts": {
                "total": len(samples),
                "train": len(train_samples),
                "valid": len(valid_samples),
            },
        }

        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)

        click.echo(json.dumps(stats))


def _write_jsonl(path, samples):
    """Write samples to JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
