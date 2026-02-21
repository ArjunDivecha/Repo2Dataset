"""
Flask server for the gh-chat-dataset web UI.

Serves the web interface and provides API endpoints for dataset generation.
"""

import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

# Configuration
OUTPUT_ROOT = os.environ.get("REPO2DATASET_OUTPUT_ROOT", "./outputs")
Path(OUTPUT_ROOT).mkdir(parents=True, exist_ok=True)


@app.route("/")
def index():
    """Render the main dataset generator UI."""
    return render_template("index.html")


@app.route("/api/jobs", methods=["POST"])
def create_job():
    """
    Create a new dataset generation job.

    Expected JSON payload:
        {
            "repo_url": "https://github.com/user/repo.git",
            "output_name": "my-dataset",  # optional
            "options": {
                "allow_llm": false,
                "max_tokens": 4096,
                "min_tokens": 48,
                "file_cap": 15,
                "md_max_questions_per_section": 4,
                "md_window_tokens": 800,
                "py_chunking": true,
                "py_chunk_max": 5,
                "py_chunk_min_lines": 6,
                "include_validation": true,
                "include_errors": true,
                "include_config": true,
                "include_logging": true
            }
        }

    Returns:
        {"job_id": "..."}
    """
    from .jobs import create_job

    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    repo_url = data.get("repo_url")
    if not repo_url:
        return jsonify({"error": "repo_url is required"}), 400

    options = data.get("options", {})

    # Generate output directory path
    output_name = data.get("output_name")
    if output_name:
        output_dir = str(Path(OUTPUT_ROOT) / output_name)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        output_dir = str(Path(OUTPUT_ROOT) / f"{repo_name}_{timestamp}")

    # Create job
    job_id = create_job(repo_url, output_dir, options)

    return jsonify({"job_id": job_id, "output_dir": output_dir})


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id: str):
    """
    Get job status and progress.

    Returns:
        {
            "job_id": "...",
            "state": "queued|running|done|error",
            "progress": 0-100,
            "logs": ["..."],
            "result": {...},  # only when done
            "error_message": "...",  # only when error
            "created_at": "...",
            "completed_at": "..."
        }
    """
    from .jobs import get_job

    job = get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)


@app.route("/api/jobs/<job_id>/result", methods=["GET"])
def get_job_result(job_id: str):
    """
    Get job result metadata.

    Returns:
        {
            "sha": "...",
            "counts": {"total": 100, "train": 90, "valid": 10},
            "output_dir": "...",
            "files": {
                "train": "...",
                "valid": "...",
                "stats": "..."
            }
        }
    """
    from .jobs import get_job

    job = get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["state"] != "done":
        return jsonify({"error": "Job not completed"}), 400

    return jsonify(job["result"])


@app.route("/api/jobs/<job_id>/download/<file_name>", methods=["GET"])
def download_job_file(job_id: str, file_name: str):
    """
    Download a file from completed job.

    Valid file names: train, valid, stats

    Returns the file as a download.
    """
    from .jobs import get_job
    from .services import validate_output_path

    job = get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["state"] != "done":
        return jsonify({"error": "Job not completed"}), 400

    # Map file name to actual file
    file_map = {
        "train": "dataset.train.jsonl",
        "valid": "dataset.valid.jsonl",
        "stats": "stats.json",
    }

    if file_name not in file_map:
        return jsonify({"error": f"Invalid file name: {file_name}"}), 400

    actual_file = file_map[file_name]
    file_path = Path(job["result"]["output_dir"]) / actual_file

    # Validate path safety
    if not validate_output_path(str(file_path), OUTPUT_ROOT):
        return jsonify({"error": "Invalid file path"}), 403

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name=actual_file,
        mimetype="application/json",
    )


@app.route("/api/jobs/<job_id>/open-output", methods=["POST"])
def open_job_output(job_id: str):
    """
    Open the output directory in the OS file manager.

    This endpoint triggers the OS file manager to open the output directory
    on the machine running the Flask server (not the client machine).

    Returns:
        {"ok": true, "output_dir": "..."} on success
        {"error": "..."} on failure
    """
    from .jobs import get_job
    from .services import validate_output_path

    job = get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["state"] != "done":
        return jsonify({"error": "Job not completed"}), 400

    output_dir = Path(job["result"]["output_dir"])

    # Validate path safety - ensure the output directory is within OUTPUT_ROOT
    if not validate_output_path(str(output_dir), OUTPUT_ROOT):
        return jsonify({"error": "Invalid output directory"}), 403

    # Check if directory exists
    if not output_dir.exists():
        return jsonify({"error": "Output directory not found", "output_dir": str(output_dir)}), 404

    # Open directory using OS-specific commands
    try:
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", str(output_dir)])
        elif system == "Windows":
            subprocess.Popen(["explorer", str(output_dir)])
        elif system == "Linux":
            # Try xdg-open, which is the standard way to open files/folders on Linux
            subprocess.Popen(["xdg-open", str(output_dir)])
        else:
            return jsonify({"error": "Unsupported operating system", "output_dir": str(output_dir)}), 400

        import logging
        logging.info(f"Opened output directory in file manager: {output_dir}")

        return jsonify({"ok": True, "output_dir": str(output_dir)})
    except Exception as e:
        # Return the path so the user can copy it as a fallback
        return jsonify({
            "error": f"Failed to open folder: {str(e)}",
            "output_dir": str(output_dir),
            "copy_fallback": True
        }), 500


@app.route("/jobs/<job_id>/output/", methods=["GET"])
def browse_job_output(job_id: str):
    """
    Browse the output directory for a completed job.

    Shows a list of files with download links.

    Returns an HTML page with file listings.
    """
    from .jobs import get_job
    from .services import validate_output_path

    job = get_job(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job["state"] != "done":
        return jsonify({"error": "Job not completed"}), 400

    output_dir = Path(job["result"]["output_dir"])

    # Validate path safety
    if not validate_output_path(str(output_dir), OUTPUT_ROOT):
        return jsonify({"error": "Invalid output directory"}), 403

    # List files in the output directory
    files_info = []
    if output_dir.exists():
        for file_path in sorted(output_dir.iterdir()):
            if file_path.is_file():
                # Determine the download URL based on file type
                file_name = file_path.name
                if file_name == "dataset.train.jsonl":
                    download_url = f"/api/jobs/{job_id}/download/train"
                elif file_name == "dataset.valid.jsonl":
                    download_url = f"/api/jobs/{job_id}/download/valid"
                elif file_name == "stats.json":
                    download_url = f"/api/jobs/{job_id}/download/stats"
                else:
                    # For other files, we don't provide a direct download link
                    # (could be extended in the future)
                    download_url = None

                files_info.append({
                    "name": file_name,
                    "download_url": download_url
                })

    return render_template(
        "browse_output.html",
        job_id=job_id,
        output_dir_path=str(output_dir),
        files=files_info
    )


def main():
    """Run the Flask development server."""
    import argparse

    global OUTPUT_ROOT

    parser = argparse.ArgumentParser(description="Run the gh-chat-dataset web server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Port to bind to (default: 5001)",
    )
    parser.add_argument(
        "--output-root",
        default=os.environ.get("REPO2DATASET_OUTPUT_ROOT", "./outputs"),
        help=f"Root directory for output datasets (default: ./outputs)",
    )

    args = parser.parse_args()

    # Update global config
    OUTPUT_ROOT = args.output_root
    os.environ["REPO2DATASET_OUTPUT_ROOT"] = OUTPUT_ROOT
    Path(OUTPUT_ROOT).mkdir(parents=True, exist_ok=True)

    print(f"Starting gh-chat-dataset web server...")
    print(f"Output directory: {OUTPUT_ROOT}")
    print(f"Access at: http://{args.host}:{args.port}")

    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()