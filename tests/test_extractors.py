from gh_chat_dataset.extract_js import extract_js_items
from gh_chat_dataset.extract_md import split_markdown_sections
from gh_chat_dataset.extract_py import extract_python_items


def test_extract_python_items_docstring():
    text = (
        "\n"
        "def add(x, y):\n"
        "    \"\"\"Add two numbers.\"\"\"\n"
        "    return x + y\n"
    )
    items = list(extract_python_items("a.py", text))
    funcs = [i for i in items if i.get("kind") in {"FunctionDef", "AsyncFunctionDef"}]
    assert any(i.get("docstring") == "Add two numbers." for i in funcs)


def test_split_markdown_sections():
    md = (
        "\n"
        "# Title\n\n"
        "Intro\n\n"
        "## Details\n\n"
        "More info\n"
    )
    secs = split_markdown_sections(md)
    assert len(secs) == 2
    assert secs[0]["title"] == "Title"
    assert "Intro" in secs[0]["content"]


def test_extract_js_items_jsdoc():
    js = (
        "\n"
        "/**\n"
        " * Multiply two numbers.\n"
        " */\n"
        "export function mul(a, b) {\n"
        "  return a * b;\n"
        "}\n"
    )
    items = list(extract_js_items("a.js", js))
    assert any("Multiply two numbers." in i.get("jsdoc", "") for i in items)
