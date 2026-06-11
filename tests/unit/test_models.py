from docpulse.models import CodeChunk, DocSection, Index, Link


def make_chunk(**kw) -> CodeChunk:
    base = dict(
        id="src/auth.py::AuthService.login",
        path="src/auth.py",
        language="python",
        kind="method",
        name="AuthService.login",
        signature="def login(self, user: str) -> Token:",
        content="def login(self, user: str) -> Token:\n    ...",
        content_hash="abc123",
        start_line=10,
        end_line=14,
    )
    return CodeChunk(**{**base, **kw})


def test_index_json_round_trip():
    index = Index(
        version=1,
        base_commit="deadbeef",
        chunks=[make_chunk()],
        sections=[
            DocSection(
                id="docs/auth.md#authentication/login-flow",
                path="docs/auth.md",
                heading_path=["Authentication", "Login Flow"],
                content="Call `AuthService.login` to authenticate.",
                content_hash="def456",
                mentions=["AuthService.login"],
                start_line=3,
                end_line=8,
            )
        ],
        links=[
            Link(
                section_id="docs/auth.md#authentication/login-flow",
                chunk_id="src/auth.py::AuthService.login",
                source="heuristic",
                score=1.0,
            )
        ],
    )
    restored = Index.model_validate_json(index.model_dump_json())
    assert restored == index


def test_link_source_is_validated():
    import pytest

    with pytest.raises(ValueError):
        Link(section_id="s", chunk_id="c", source="vibes", score=0.5)


def test_chunk_kind_and_language_are_validated():
    import pytest

    with pytest.raises(ValueError):
        make_chunk(kind="paragraph")
    with pytest.raises(ValueError):
        make_chunk(language="cobol")


def test_suspect_pairs_chunks_with_scores():
    from docpulse.models import DocSection, Suspect, SuspectChunk

    section = DocSection(
        id="docs/auth.md#login", path="docs/auth.md", heading_path=["Login"],
        content="...", content_hash="h", mentions=[], start_line=1, end_line=3,
    )
    suspect = Suspect(
        section=section,
        changed_chunks=[SuspectChunk(chunk=make_chunk(), link_score=1.0, change_size=3)],
        score=3.0,
    )
    assert suspect.changed_chunks[0].link_score == 1.0
    assert suspect.changed_chunks[0].chunk.name == "AuthService.login"
