from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageRules:
    language: str                      # value stored on CodeChunk.language
    grammars: dict[str, str]           # file extension -> tree-sitter grammar name
    node_kinds: dict[str, str]         # tree-sitter node type -> chunk kind


RULES: list[LanguageRules] = [
    LanguageRules(
        language="python",
        grammars={".py": "python"},
        node_kinds={"function_definition": "function", "class_definition": "class"},
    ),
    LanguageRules(
        language="typescript",
        grammars={".ts": "typescript", ".tsx": "tsx"},
        node_kinds={
            "function_declaration": "function",
            "class_declaration": "class",
            "method_definition": "method",
            "interface_declaration": "interface",
            "enum_declaration": "enum",
        },
    ),
    LanguageRules(
        language="csharp",
        grammars={".cs": "csharp"},
        node_kinds={
            "class_declaration": "class",
            "interface_declaration": "interface",
            "method_declaration": "method",
            "enum_declaration": "enum",
        },
    ),
]


def rules_for_path(path: str) -> tuple[LanguageRules, str] | None:
    """Return (rules, grammar_name) for a file path, or None if unsupported."""
    for rules in RULES:
        for ext, grammar in rules.grammars.items():
            if path.endswith(ext):
                return rules, grammar
    return None
