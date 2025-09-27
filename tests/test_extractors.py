"""Tests for extraction modules."""

from pathlib import Path

from gh_chat_dataset import extract_md, extract_py


def test_python_extraction():
    """Test Python AST extraction."""
    code = '''"""Module docstring."""

def hello(name: str) -> str:
    """Say hello to someone.

    Args:
        name: The person's name.

    Returns:
        A greeting message.
    """
    return f"Hello, {name}!"

class Greeter:
    """A class for greeting people."""

    def greet(self, name: str) -> str:
        """Greet someone."""
        return f"Hi, {name}!"
'''

    items = extract_py.extract_python_items(Path("test.py"), code)
    assert len(items) >= 3  # module, function, class (may include method)

    # Check module docstring
    module_item = next(item for item in items if item["kind"] == "Module")
    assert module_item["docstring"] == "Module docstring."

    # Check function
    func_item = next(item for item in items if item["name"] == "hello")
    assert "Say hello to someone." in func_item["docstring"]


def test_markdown_extraction():
    """Test Markdown section extraction."""
    content = '''# Introduction

This is the intro.

## Getting Started

Here's how to start.

### Installation

Run pip install.

## Advanced Usage

More complex examples.
'''

    sections = extract_md.extract_markdown_sections(Path("README.md"), content)
    assert len(sections) >= 3

    # Check first section
    intro_section = next(s for s in sections if s["title"] == "Introduction")
    assert "This is the intro." in intro_section["content"]


def test_empty_inputs():
    """Test handling of empty/invalid inputs."""
    # Empty Python code
    assert extract_py.extract_python_items(Path("empty.py"), "") == []

    # Invalid Python syntax
    assert extract_py.extract_python_items(Path("bad.py"), "def broken(") == []

    # Empty Markdown
    assert extract_md.extract_markdown_sections(Path("empty.md"), "") == []
