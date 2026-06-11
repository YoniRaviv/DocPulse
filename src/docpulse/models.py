from typing import Literal

from pydantic import BaseModel

Language = Literal["python", "typescript", "csharp"]
ChunkKind = Literal["function", "class", "method", "interface", "enum"]


class CodeChunk(BaseModel):
    """Represents a code element extracted from source code."""

    id: str  # "src/auth.py::AuthService.login"
    path: str
    language: Language
    kind: ChunkKind
    name: str  # qualified: "AuthService.login"
    signature: str  # first line, e.g. "def login(self, user: str) -> Token:"
    content: str  # full node text
    content_hash: str  # sha256(content)
    start_line: int
    end_line: int


class DocSection(BaseModel):
    """Represents a documentation section extracted from markdown."""

    id: str  # "docs/auth.md#authentication/login-flow"
    path: str
    heading_path: list[str]  # ["Authentication", "Login Flow"]
    content: str
    content_hash: str
    mentions: list[str]  # code-like tokens found in the section
    start_line: int
    end_line: int


class Link(BaseModel):
    """Represents a link between a documentation section and a code chunk."""

    section_id: str
    chunk_id: str
    source: Literal["heuristic", "embedding"]
    score: float  # 1.0 for heuristic; cosine similarity for embedding


class Index(BaseModel):
    """Root schema for a documentation index snapshot."""

    version: int  # schema version, starts at 1
    base_commit: str
    chunks: list[CodeChunk]
    sections: list[DocSection]
    links: list[Link]


class SuspectChunk(BaseModel):
    """A changed code chunk linked to a suspect section."""

    chunk: CodeChunk  # head version (base version for deleted symbols)
    link_score: float  # strongest link tying this chunk to the section
    change_size: int  # changed lines overlapping the chunk


class Suspect(BaseModel):
    """Phase 2: Documentation section that might be stale due to code changes."""

    section: DocSection
    changed_chunks: list[SuspectChunk]
    score: float  # ranking value: sum(link_score * change_size)


class Verdict(BaseModel):
    """Phase 3: Analysis result for whether a documentation section is stale."""

    section_id: str
    status: Literal["stale", "accurate", "unverified"]
    confidence: float  # 0..1; meaningful only for "stale"
    diagnosis: str  # what specifically is wrong
    evidence: list[str]  # file:line references


class Repair(BaseModel):
    """Phase 4: Proposed fix for a stale documentation section."""

    section_id: str
    new_content: str
    confidence: float
    validation_passed: bool
    rationale: str  # cited code change that caused the fix


class RunResult(BaseModel):
    """Phase 5: Final result of a full DocPulse analysis run."""

    verdicts: list[Verdict]
    repairs: list[Repair]
    suspects_checked: int
    suspects_total: int  # for "checked N of M" honest reporting
    tokens_used: int
    exit_code: int  # 0 clean / 1 drift / 2 tool error
