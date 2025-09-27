from gh_chat_dataset.builders import build_chats_from_md_section
from gh_chat_dataset.cli import _chunk_code_by_blanklines


def test_md_multi_questions():
    sec = {
        "title": "Usage",
        "content": "This section explains usage. Inputs: A,B. Outputs: C. Limitations: none.",
    }
    chats = build_chats_from_md_section(sec, {"path": "README.md"}, max_questions=3, window_tokens=50)
    assert 1 <= len(chats) <= 3
    # All chats should include the section content as assistant
    assert all(sec["content"] in r["messages"][1]["content"] for r in chats)


def test_chunk_code_by_blanklines():
    code = (
        "def f(x):\n"
        "    a = x + 1\n\n"
        "    b = a * 2\n\n"
        "    return b\n"
    )
    chunks = _chunk_code_by_blanklines(code, min_lines=1, max_chunks=5)
    assert len(chunks) >= 2
    assert any("return b" in ch for ch in chunks)
