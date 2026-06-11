from pathlib import Path

from docpulse.diffing.git_diff import show_file
from docpulse.indexing.code_chunker import chunk_source
from docpulse.models import Suspect
from docpulse.verification.verifier import VerifyBundle


def _seed_code(root: Path, base: str, head: str, suspect: Suspect) -> tuple[str, str]:
    """Best-effort (old_code, new_code) seed for a suspect's changed chunks.

    Re-chunks each changed file at base and head and pairs by chunk id, so the
    verifier is seeded with the before/after of exactly the changed symbols. The
    verifier's read tools can inspect further; this is only the starting evidence.
    """
    base_by_id = {}
    head_by_id = {}
    for path in sorted({sc.chunk.path for sc in suspect.changed_chunks}):
        base_text = show_file(root, base, path)
        head_text = show_file(root, head, path)
        if base_text:
            base_by_id.update({c.id: c for c in chunk_source(path, base_text)})
        if head_text:
            head_by_id.update({c.id: c for c in chunk_source(path, head_text)})
    old_parts: list[str] = []
    new_parts: list[str] = []
    for sc in suspect.changed_chunks:
        old = base_by_id.get(sc.chunk.id)
        new = head_by_id.get(sc.chunk.id)
        old_parts.append(old.content if old else f"(symbol {sc.chunk.name} did not exist before)")
        new_parts.append(new.content if new else f"(symbol {sc.chunk.name} was removed)")
    return "\n\n".join(old_parts), "\n\n".join(new_parts)


def build_verify_bundle(
    root: Path, base: str, head: str, suspect: Suspect, intent: str
) -> VerifyBundle:
    """Assemble the verifier's seed bundle for one suspect section."""
    old_code, new_code = _seed_code(root, base, head, suspect)
    return VerifyBundle(
        section_id=suspect.section.id,
        doc_content=suspect.section.content,
        old_code=old_code,
        new_code=new_code,
        intent=intent,
    )
