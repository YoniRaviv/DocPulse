from docpulse.config import Config, DocGlob
from docpulse.diffing.change_filter import file_changed_chunks
from docpulse.diffing.git_diff import FileDiff

BASE_PY = """\
class AuthService:
    def login(self, user):
        return user

    def logout(self, token):
        pass
"""


def modified(path="src/auth.py", base_ranges=(), head_ranges=()):
    return FileDiff(
        path=path, status="modified",
        base_ranges=list(base_ranges), head_ranges=list(head_ranges),
    )


def test_signature_change_is_meaningful():
    head = BASE_PY.replace("def login(self, user):", "def login(self, username):")
    changed = file_changed_chunks(
        modified(base_ranges=[(2, 2)], head_ranges=[(2, 2)]), BASE_PY, head
    )
    ids = {c.chunk.id for c in changed}
    assert "src/auth.py::AuthService.login" in ids
    login = next(c for c in changed if c.chunk.id.endswith("login"))
    assert login.change_size >= 1
    assert "username" in login.chunk.signature  # head version carried


def test_comment_only_change_is_dropped():
    head = BASE_PY.replace("        return user", "        # totally new comment\n        return user")
    changed = file_changed_chunks(
        modified(base_ranges=[], head_ranges=[(3, 3)]), BASE_PY, head
    )
    assert changed == []


def test_whitespace_only_change_is_dropped():
    head = BASE_PY.replace("        return user", "        return  user")
    changed = file_changed_chunks(
        modified(base_ranges=[(3, 3)], head_ranges=[(3, 3)]), BASE_PY, head
    )
    assert changed == []


def test_untouched_overlapping_sibling_is_not_flagged():
    # editing login also overlaps the AuthService class chunk -> class IS flagged,
    # but logout (no overlap) must not be
    head = BASE_PY.replace("return user", "return user.upper()")
    changed = file_changed_chunks(
        modified(base_ranges=[(3, 3)], head_ranges=[(3, 3)]), BASE_PY, head
    )
    ids = {c.chunk.id for c in changed}
    assert "src/auth.py::AuthService.logout" not in ids


def test_deleted_symbol_surfaces_base_chunk():
    head = "class AuthService:\n    def login(self, user):\n        return user\n"
    changed = file_changed_chunks(
        modified(base_ranges=[(4, 6)], head_ranges=[]), BASE_PY, head
    )
    ids = {c.chunk.id for c in changed}
    assert "src/auth.py::AuthService.logout" in ids


def test_deleted_file_surfaces_base_chunks():
    changed = file_changed_chunks(
        FileDiff(path="src/auth.py", status="deleted", base_ranges=[(1, 6)], head_ranges=[]),
        BASE_PY, None,
    )
    assert {c.chunk.id for c in changed} >= {
        "src/auth.py::AuthService", "src/auth.py::AuthService.login",
    }


def test_meaningful_changed_chunks_drops_excluded_paths(tmp_path):
    import subprocess

    from docpulse.diffing.change_filter import meaningful_changed_chunks

    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, check=True)

    git("init")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "auth.py").write_text(BASE_PY)
    (tmp_path / "tests" / "test_auth.py").write_text("def test_a():\n    assert True\n")
    git("add", "-A")
    git("commit", "-m", "base")
    (tmp_path / "src" / "auth.py").write_text(BASE_PY.replace("user)", "username)"))
    (tmp_path / "tests" / "test_auth.py").write_text("def test_a():\n    assert 1 == 1\n")
    git("commit", "-am", "head")

    from docpulse.diffing.git_diff import diff_range

    config = Config(
        docs=[DocGlob(path="docs/**/*.md")],
        code={"include": ["src/**"], "exclude": ["tests/**"]},
    )
    changed = meaningful_changed_chunks(
        tmp_path, diff_range(tmp_path, "HEAD~1", "HEAD"), config, "HEAD~1", "HEAD"
    )
    paths = {c.chunk.path for c in changed}
    assert paths == {"src/auth.py"}
