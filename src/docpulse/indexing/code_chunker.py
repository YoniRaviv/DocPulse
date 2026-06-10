import hashlib

from tree_sitter_language_pack import get_parser

from docpulse.indexing.chunk_rules import rules_for_path
from docpulse.models import CodeChunk


def chunk_source(path: str, source: str) -> list[CodeChunk]:
    resolved = rules_for_path(path)
    if resolved is None:
        return []
    rules, grammar = resolved
    src_bytes = source.encode()
    tree = get_parser(grammar).parse_bytes(src_bytes)
    chunks: list[CodeChunk] = []

    def visit(node, name_stack: list[str]) -> None:  # type: ignore[type-arg]
        kind = rules.node_kinds.get(node.kind())
        next_stack = name_stack
        if kind is not None:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name_br = name_node.byte_range()
                name = src_bytes[name_br.start:name_br.end].decode()
                if kind == "function" and name_stack:
                    kind = "method"
                qualified = ".".join([*name_stack, name])
                node_br = node.byte_range()
                content = src_bytes[node_br.start:node_br.end].decode()
                chunks.append(
                    CodeChunk(
                        id=f"{path}::{qualified}",
                        path=path,
                        language=rules.language,
                        kind=kind,
                        name=qualified,
                        signature=content.splitlines()[0].strip(),
                        content=content,
                        content_hash=hashlib.sha256(content.encode()).hexdigest(),
                        start_line=node.start_position().row + 1,
                        end_line=node.end_position().row + 1,
                    )
                )
                next_stack = [*name_stack, name]
        for i in range(node.child_count()):
            visit(node.child(i), next_stack)

    visit(tree.root_node(), [])
    return chunks
