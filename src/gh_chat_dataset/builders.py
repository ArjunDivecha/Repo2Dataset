from typing import Dict, List, Optional

from .tokenize_util import count_tokens_approx


def _to_chat(user: str, assistant: str, system: Optional[str] = None) -> Dict:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    msgs.append({"role": "assistant", "content": assistant})
    return {"messages": msgs}


def build_chat_from_py_docstring(item: Dict, meta: Dict, allow_llm: bool) -> Optional[Dict]:
    doc = item.get("docstring", "").strip()
    code = item.get("code", "").strip()
    if not doc:
        if allow_llm:
            # Stub: if integrating an LLM, generate docstring; here we skip in OSS-safe mode
            return None
        return None
    rec = _to_chat(
        user="Write a clear, concise docstring for the following Python code.\n\n" + code,
        assistant=doc,
        system="You are a helpful Python assistant.",
    )
    rec["meta"] = {**meta, "task": "py_docstring_from_code", "source_type": "python"}
    return rec


def build_chat_from_js_jsdoc(item: Dict, meta: Dict, allow_llm: bool) -> Optional[Dict]:
    jsdoc = item.get("jsdoc", "").strip()
    code = item.get("code", "").strip()
    if not jsdoc:
        if allow_llm:
            return None
        return None
    rec = _to_chat(
        user="Write a JSDoc comment for the following JavaScript/TypeScript function.\n\n" + code,
        assistant=jsdoc,
        system="You are a helpful JavaScript assistant.",
    )
    rec["meta"] = {**meta, "task": "js_jsdoc_from_code", "source_type": "javascript"}
    return rec


def _window_text_by_tokens(text: str, window_tokens: int, overlap_tokens: int = 120) -> List[str]:
    if not text.strip():
        return []
    words = text.split()
    # approximate: assume ~1 token ≈ 1 word for windowing granularity
    step = max(1, window_tokens - overlap_tokens)
    out: List[str] = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + window_tokens]
        if not chunk_words:
            break
        out.append(" ".join(chunk_words))
        i += step
        if len(out) > 32:  # safety cap
            break
    return out


def build_chats_from_md_section(
    section: Dict,
    meta: Dict,
    max_questions: int = 4,
    window_tokens: int = 800,
) -> List[Dict]:
    title = section.get("title", "").strip() or "Section"
    content = section.get("content", "").strip()
    if not content:
        return []

    # Window long content
    windows = [content]
    if count_tokens_approx(content) > window_tokens:
        windows = _window_text_by_tokens(content, window_tokens)

    q_templates = [
        f"What is {title}? Provide a concise explanation based only on this section.",
        f"What are the key inputs and outputs described in {title}?",
        f"Summarize any policies, caveats, or limitations mentioned in {title}.",
        f"Describe the workflow/steps outlined in {title}.",
    ]
    chats: List[Dict] = []
    for w in windows:
        for q in q_templates[: max_questions or 1]:
            prompt = q + "\n\n" + w
            rec = _to_chat(user=prompt, assistant=w, system="You are a documentation assistant.")
            rec["meta"] = {**meta, "task": "md_section_qa", "source_type": "markdown", "title": title}
            chats.append(rec)
    return chats


def build_chat_from_py_chunk(item: Dict, chunk_code: str, meta: Dict) -> Optional[Dict]:
    name = item.get("name", "function")
    if not chunk_code.strip():
        return None
    user = (
        f"Explain the following Python code chunk from {name}. Focus on what it does and why.\n\n" + chunk_code
    )
    assistant = chunk_code
    rec = _to_chat(user=user, assistant=assistant, system="You are a helpful Python assistant.")
    rec["meta"] = {**meta, "task": "py_chunk_explain", "source_type": "python", "name": name}
    return rec


def build_validation_summary_py(code: str, meta: Dict) -> Optional[Dict]:
    if not code:
        return None
    lines = [
        ln
        for ln in code.splitlines()
        if any(k in ln for k in ["assert ", "raise ", "ValueError", "TypeError", "KeyError"])
    ]
    if not lines:
        return None
    user = "What inputs are validated and how? Summarize from the code (asserts and raises).\n\n" + code
    assistant = "\n".join(lines)
    rec = _to_chat(user=user, assistant=assistant, system="You are a precise Python assistant.")
    rec["meta"] = {**meta, "task": "py_validation_summary", "source_type": "python"}
    return rec


def build_error_handling_summary_py(code: str, meta: Dict) -> Optional[Dict]:
    if not code:
        return None
    lines = [ln for ln in code.splitlines() if ln.strip().startswith("except ") or ln.strip().startswith("try:")]
    if not lines:
        return None
    user = "Explain the error handling in this code. Which exceptions are caught and what happens?\n\n" + code
    assistant = "\n".join(lines)
    rec = _to_chat(user=user, assistant=assistant, system="You are a precise Python assistant.")
    rec["meta"] = {**meta, "task": "py_error_handling_summary", "source_type": "python"}
    return rec


def build_config_constants_summary_py(code: str, meta: Dict) -> Optional[Dict]:
    if not code:
        return None
    const_lines: List[str] = []
    for ln in code.splitlines():
        if "=" in ln and ln.strip() and ln.strip()[0].isalpha():
            left = ln.split("=", 1)[0].strip()
            if left.isupper() and " " not in left and not left.startswith("#"):
                const_lines.append(ln.strip())
    if not const_lines:
        return None
    user = "Summarize the configuration constants defined in this module.\n\n" + "\n".join(const_lines)
    assistant = "\n".join(const_lines)
    rec = _to_chat(user=user, assistant=assistant, system="You are a configuration expert.")
    rec["meta"] = {**meta, "task": "py_config_constants_summary", "source_type": "python"}
    return rec


def build_logging_flow_summary_py(code: str, meta: Dict) -> Optional[Dict]:
    if not code:
        return None
    log_lines = [
        ln.strip()
        for ln in code.splitlines()
        if any(t in ln for t in ["logging.", ".debug(", ".info(", ".warning(", ".error(", ".exception("])
    ]
    if not log_lines:
        return None
    user = "Describe the logging flow: logger names, levels, and key messages.\n\n" + "\n".join(log_lines)
    assistant = "\n".join(log_lines)
    rec = _to_chat(user=user, assistant=assistant, system="You are a logging expert.")
    rec["meta"] = {**meta, "task": "py_logging_flow_summary", "source_type": "python"}
    return rec
