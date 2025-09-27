def count_tokens_approx(s: str) -> int:
    # Approximate: 1 token ~ 4 chars. Replace with your tokenizer for accuracy.
    return max(1, len(s) // 4)
