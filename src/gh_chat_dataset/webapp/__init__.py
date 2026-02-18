"""
Web application front-end for gh-chat-dataset.

Provides a web UI for generating datasets from GitHub repositories.
"""

from .server import app

__all__ = ["app"]