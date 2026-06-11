from dataclasses import dataclass


@dataclass(frozen=True)
class VerifyBundle:
    """Everything the verifier needs to judge one doc section."""

    section_id: str
    doc_content: str
    old_code: str
    new_code: str
    intent: str
