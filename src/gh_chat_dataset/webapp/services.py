"""
Orchestration layer for dataset generation.

Wraps the core CLI logic with progress reporting for web UI.
"""

from pathlib import Path
from typing import Callable, Dict, Optional

from ..cli import generate_dataset


def generate_dataset_with_progress(
    repo_url: str,
    output_dir: str,
    options: Dict,
    progress_cb: Optional[Callable[[str, int], None]] = None,
) -> Dict:
    """
    Generate a dataset with progress callbacks.

    Args:
        repo_url: GitHub repository URL
        output_dir: Output directory path
        options: Dictionary of dataset generation options
        progress_cb: Optional callback function(message, progress_percent)

    Returns:
        Dict with 'sha' and 'counts' keys, plus output paths

    Raises:
        RuntimeError: If generation fails
    """
    # Ensure output directory exists
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Map options to CLI parameters
    result = generate_dataset(
        repo=repo_url,
        out_dir=output_dir,
        allow_llm=options.get("allow_llm", False),
        max_tokens=options.get("max_tokens", 4096),
        min_tokens=options.get("min_tokens", 48),
        file_cap=options.get("file_cap", 15),
        md_max_questions_per_section=options.get("md_max_questions_per_section", 4),
        md_window_tokens=options.get("md_window_tokens", 800),
        py_chunking=options.get("py_chunking", True),
        py_chunk_max=options.get("py_chunk_max", 5),
        py_chunk_min_lines=options.get("py_chunk_min_lines", 6),
        include_validation=options.get("include_validation", True),
        include_errors=options.get("include_errors", True),
        include_config=options.get("include_config", True),
        include_logging=options.get("include_logging", True),
        progress_cb=progress_cb,
    )

    # Add output file paths to result
    result["output_dir"] = str(out_path.resolve())
    result["files"] = {
        "train": str(out_path / "dataset.train.jsonl"),
        "valid": str(out_path / "dataset.valid.jsonl"),
        "stats": str(out_path / "stats.json"),
    }

    return result


def validate_output_path(path: str, output_root: str) -> bool:
    """
    Validate that a file path is safe for download (within output root).

    Args:
        path: File path to validate
        output_root: Root directory that contains all outputs

    Returns:
        True if path is safe, False otherwise
    """
    try:
        requested = Path(path).resolve()
        root = Path(output_root).resolve()

        # Check if requested path is within the root
        requested.relative_to(root)
        return True
    except (ValueError, RuntimeError):
        return False