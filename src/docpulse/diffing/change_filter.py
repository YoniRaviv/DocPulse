from pathlib import Path

from pydantic import BaseModel
from tree_sitter_language_pack import get_parser

from docpulse.config import Config
from docpulse.diffing.git_diff import FileDiff, show_file
from docpulse.indexing.chunk_rules import rules_for_path
from docpulse.indexing.code_chunker import chunk_source
from docpulse.models import CodeChunk

# All shipped grammars (py/ts/csharp) use "comment"; extras future-proof other grammars.
_COMMENT_KINDS = {"comment", "line_comment", "block_comment"}


class ChangedChunk(BaseModel):
    """A code chunk whose content meaningfully changed between base and head."""

    chunk: CodeChunk  # head version (base version for deleted symbols)
    change_size: int  # changed lines overlapping the chunk


def _tokens(path: str, content: str) -> list[str]:
    """Non-comment leaf token texts; whitespace never appears in the tree."""
    resolved = rules_for_path(path)
    if resolved is None:
        return [content]
    _, grammar = resolved
    src = content.encode()
    tree = get_parser(grammar).parse_bytes(src)
    tokens: list[str] = []

    def visit(node) -> None:  # noqa: ANN001 - pyo3 node type
        if node.kind() in _COMMENT_KINDS:
            return
        if node.child_count() == 0:
            br = node.byte_range()
            tokens.append(src[br.start : br.end].decode())
            return
        for i in range(node.child_count()):
            visit(node.child(i))

    visit(tree.root_node())
    return tokens


def _overlap(chunk: CodeChunk, ranges: list[tuple[int, int]]) -> int:
    """Number of changed lines falling inside the chunk (0 = no overlap)."""
    return sum(
        max(0, min(chunk.end_line, end) - max(chunk.start_line, start) + 1)
        for start, end in ranges
    )


def file_changed_chunks(
    diff: FileDiff, base_text: str | None, head_text: str | None
) -> list[ChangedChunk]:
    """Chunks meaningfully changed in one file, pairing base/head versions by id."""
    base_chunks = chunk_source(diff.path, base_text) if base_text else []
    head_chunks = chunk_source(diff.path, head_text) if head_text else []
    base_by_id = {c.id: c for c in base_chunks}
    head_ids = {c.id for c in head_chunks}
    changed: dict[str, ChangedChunk] = {}

    def is_meaningful(base: CodeChunk | None, head: CodeChunk) -> bool:
        if base is None:
            return True  # new symbol
        if base.content_hash == head.content_hash:
            return False  # neighbor edit merely overlapped this chunk
        return _tokens(head.path, base.content) != _tokens(head.path, head.content)

    for head_chunk in head_chunks:
        base_chunk = base_by_id.get(head_chunk.id)
        size = _overlap(head_chunk, diff.head_ranges)
        if not size and base_chunk is not None:
            # Pure deletion inside a surviving symbol: the hunk has no head_ranges
            # overlap, but the base version's lines were changed — fall back to the
            # base-side overlap so the deletion is not silently dropped.
            size = _overlap(base_chunk, diff.base_ranges)
        if size and is_meaningful(base_chunk, head_chunk):
            changed[head_chunk.id] = ChangedChunk(chunk=head_chunk, change_size=size)

    # Base-side pass catches symbols deleted (or emptied) in head.
    for base_chunk in base_chunks:
        if base_chunk.id in head_ids or base_chunk.id in changed:
            continue
        size = _overlap(base_chunk, diff.base_ranges)
        if size:
            changed[base_chunk.id] = ChangedChunk(chunk=base_chunk, change_size=size)

    return list(changed.values())


def meaningful_changed_chunks(
    root: Path, diffs: list[FileDiff], config: Config, base: str, head: str
) -> list[ChangedChunk]:
    """All meaningfully changed chunks across a diff, excluding non-code paths."""
    changed: list[ChangedChunk] = []
    for diff in diffs:
        if not config.code.matches(diff.path) or rules_for_path(diff.path) is None:
            continue
        base_text = show_file(root, base, diff.path) if diff.status != "added" else None
        head_text = show_file(root, head, diff.path) if diff.status != "deleted" else None
        changed.extend(file_changed_chunks(diff, base_text, head_text))
    return changed
