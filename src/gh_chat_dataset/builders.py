from typing import Dict, Optional


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


def build_chat_from_md_section(section: Dict, meta: Dict, allow_llm: bool) -> Optional[Dict]:
    title = section.get("title", "").strip()
    content = section.get("content", "").strip()
    if not content:
        return None
    prompt = f"Answer based on the documentation section titled: {title or 'Section'}\n\n" + content
    # Deterministic: use the section text as the answer (acts like extractive QA)
    rec = _to_chat(user=prompt, assistant=content, system="You are a documentation assistant.")
    rec["meta"] = {**meta, "task": "md_section_qa", "source_type": "markdown"}
    return rec
