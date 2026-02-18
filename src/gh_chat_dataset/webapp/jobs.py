"""
In-memory job manager for dataset generation jobs.

Manages background execution, progress tracking, and result storage.
"""

import threading
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, TypedDict


class JobState(TypedDict):
    """Job state information."""
    job_id: str
    state: str  # queued, running, done, error
    progress: int  # 0-100
    logs: List[str]
    result: Optional[Dict]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]


# In-memory job storage
_jobs: Dict[str, JobState] = {}
_jobs_lock = threading.Lock()
_MAX_LOGS = 200


def create_job(repo_url: str, output_dir: str, options: Dict) -> str:
    """
    Create a new dataset generation job.

    Args:
        repo_url: GitHub repository URL
        output_dir: Output directory path
        options: Dataset generation options

    Returns:
        Job ID string
    """
    job_id = str(uuid.uuid4())

    job = JobState(
        job_id=job_id,
        state="queued",
        progress=0,
        logs=[f"Job {job_id} queued for repository: {repo_url}"],
        result=None,
        error_message=None,
        created_at=datetime.utcnow().isoformat(),
        completed_at=None,
    )

    with _jobs_lock:
        _jobs[job_id] = job

    # Start job in background thread
    thread = threading.Thread(
        target=_run_job,
        args=(job_id, repo_url, output_dir, options),
        daemon=True,
    )
    thread.start()

    return job_id


def get_job(job_id: str) -> Optional[JobState]:
    """
    Get job status and progress.

    Args:
        job_id: Job identifier

    Returns:
        Job state dict or None if not found
    """
    with _jobs_lock:
        return _jobs.get(job_id)


def list_jobs() -> List[JobState]:
    """
    List all jobs.

    Returns:
        List of job states
    """
    with _jobs_lock:
        return list(_jobs.values())


def _run_job(
    job_id: str,
    repo_url: str,
    output_dir: str,
    options: Dict,
):
    """Execute the dataset generation job in a background thread."""
    from .services import generate_dataset_with_progress

    job = get_job(job_id)
    if not job:
        return

    # Update state to running
    with _jobs_lock:
        _jobs[job_id]["state"] = "running"

    def progress_callback(message: str, percent: int):
        """Update job progress."""
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]["progress"] = percent
                _jobs[job_id]["logs"].append(
                    f"[{datetime.utcnow().strftime('%H:%M:%S')}] {message}"
                )
                # Keep only recent logs
                if len(_jobs[job_id]["logs"]) > _MAX_LOGS:
                    _jobs[job_id]["logs"] = list(_jobs[job_id]["logs"])[-_MAX_LOGS:]

    try:
        result = generate_dataset_with_progress(
            repo_url=repo_url,
            output_dir=output_dir,
            options=options,
            progress_cb=progress_callback,
        )

        with _jobs_lock:
            _jobs[job_id]["state"] = "done"
            _jobs[job_id]["progress"] = 100
            _jobs[job_id]["result"] = result
            _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            _jobs[job_id]["logs"].append("Job completed successfully!")

    except Exception as e:
        with _jobs_lock:
            _jobs[job_id]["state"] = "error"
            _jobs[job_id]["error_message"] = str(e)
            _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            _jobs[job_id]["logs"].append(f"Job failed: {str(e)}")