from docpulse.models import DocSection


def replace_sections(file_text: str, edits: list[tuple[DocSection, str]]) -> str:
    """Apply (section, new_content) replacements to one file's text.

    Each section is replaced by its 1-based inclusive [start_line, end_line] range.
    Edits are applied bottom-up (highest start_line first) so an earlier edit that
    changes line count never shifts a later section's range. Uses str.splitlines()
    to match doc_parser's line model; the file's trailing newline is preserved.
    """
    lines = file_text.splitlines()
    for section, new_content in sorted(edits, key=lambda e: e[0].start_line, reverse=True):
        lines[section.start_line - 1 : section.end_line] = new_content.splitlines()
    trailing = "\n" if file_text.endswith("\n") else ""
    return "\n".join(lines) + trailing
