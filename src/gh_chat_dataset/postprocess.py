from typing import Callable, Dict, List, Tuple


def redact_secrets(record: Dict) -> Dict:
    # Placeholder: implement redaction patterns as needed.
    return record


def within_budget(record: Dict, max_tokens: int, tokenizer: Callable[[str], int]) -> bool:
    total = 0
    for m in record.get("messages", []):
        c = m.get("content", "")
        if isinstance(c, str):
            total += tokenizer(c)
    return total <= max_tokens


def dedupe_records(records: List[Dict]) -> List[Dict]:
    seen = set()
    out: List[Dict] = []
    for r in records:
        msgs = r.get("messages", [])
        key: Tuple = tuple(
            (m.get("role"), m.get("content"))
            for m in msgs
            if isinstance(m, dict)
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
