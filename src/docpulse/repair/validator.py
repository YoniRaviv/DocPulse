import re
from collections import Counter

_BLANK_LINE = re.compile(r"\n[ \t]*\n")


def _blocks(text: str) -> list[str]:
    """Split text into paragraph blocks on blank lines (whitespace-only allowed)."""
    return [b for b in (p.strip("\n") for p in _BLANK_LINE.split(text)) if b.strip()]


def preservation_ratio(original: str, new: str) -> float:
    """Fraction of original paragraph blocks surviving byte-identical in `new`.

    Deterministic, no LLM. Counts with multiplicity: if the original has a block
    twice and the new text has it once, only one is counted as preserved.
    Returns 1.0 when the original has no blocks.
    """
    original_blocks = _blocks(original)
    if not original_blocks:
        return 1.0
    available = Counter(_blocks(new))
    kept = 0
    for block in original_blocks:
        if available[block] > 0:
            available[block] -= 1
            kept += 1
    return kept / len(original_blocks)
