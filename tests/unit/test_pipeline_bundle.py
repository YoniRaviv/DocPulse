import subprocess
from pathlib import Path

import pytest

from docpulse.indexing.code_chunker import chunk_source
from docpulse.models import DocSection, Suspect, SuspectChunk
from docpulse.pipeline import _seed_code


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "auth.py").write_text("def login(user):\n    return user\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "base")
    return tmp_path


def _suspect_for(head_chunk):
    section = DocSection(
        id="docs/auth.md#login", path="docs/auth.md", heading_path=["login"],
        content="Call login(user).", content_hash="h", mentions=["login"],
        start_line=1, end_line=1,
    )
    return Suspect(
        section=section,
        changed_chunks=[SuspectChunk(chunk=head_chunk, link_score=1.0, change_size=1)],
        score=1.0,
    )


def test_seed_code_pairs_base_and_head_versions(repo):
    base = git(repo, "rev-parse", "HEAD")
    (repo / "auth.py").write_text("def login(username):\n    return username\n")
    git(repo, "commit", "-am", "rename param")
    head_chunk = chunk_source("auth.py", (repo / "auth.py").read_text())[0]
    old_code, new_code = _seed_code(repo, base, "HEAD", _suspect_for(head_chunk))
    assert "def login(user)" in old_code
    assert "def login(username)" in new_code


def test_seed_code_marks_added_symbol(repo):
    base = git(repo, "rev-parse", "HEAD")
    (repo / "auth.py").write_text(
        "def login(user):\n    return user\n\n\ndef logout():\n    return None\n"
    )
    git(repo, "commit", "-am", "add logout")
    logout = next(c for c in chunk_source("auth.py", (repo / "auth.py").read_text())
                  if c.name == "logout")
    old_code, new_code = _seed_code(repo, base, "HEAD", _suspect_for(logout))
    assert "did not exist before" in old_code
    assert "def logout()" in new_code
