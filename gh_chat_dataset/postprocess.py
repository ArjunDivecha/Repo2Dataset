"""Post-processing utilities for samples."""

import hashlib
from typing import Dict, List


def filter_samples(samples: List[Dict], max_tokens: int = 2048) -> List[Dict]:
    """Filter and deduplicate samples."""
    # Approximate token counting (replace with real tokenizer)
    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4)  # Rough approximation

    # Filter by length
    filtered = []
    for sample in samples:
        total_tokens = 0
        for msg in sample.get("messages", []):
            total_tokens += count_tokens(msg.get("content", ""))

        if total_tokens <= max_tokens:
            filtered.append(sample)

    # Deduplicate by message content hash
    seen = set()
    deduplicated = []

    for sample in filtered:
        # Create hash from all message contents
        content_parts = []
        for msg in sample.get("messages", []):
            content_parts.append(f"{msg.get('role', '')}:{msg.get('content', '')}")

        content_hash = hashlib.sha256(
            "\n".join(content_parts).encode("utf-8")
        ).hexdigest()

        if content_hash not in seen:
            seen.add(content_hash)
            deduplicated.append(sample)

    return deduplicated
