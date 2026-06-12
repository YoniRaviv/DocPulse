import subprocess
from pathlib import Path

import pytest

from docpulse.diffing.git_diff import diff_range, show_file


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@test")
    git(tmp_path, "config", "user.name", "test")
    (tmp_path / "a.py").write_text("def f():\n    return 1\n\n\ndef g():\n    return 2\n")
    (tmp_path / "b.py").write_text("X = 1\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "base")
    return tmp_path


def test_modified_file_line_ranges(repo):
    (repo / "a.py").write_text("def f():\n    return 99\n\n\ndef g():\n    return 2\n")
    git(repo, "commit", "-am", "change f")
    diffs = diff_range(repo, "HEAD~1", "HEAD")
    assert len(diffs) == 1
    diff = diffs[0]
    assert diff.path == "a.py" and diff.status == "modified"
    assert diff.head_ranges == [(2, 2)]
    assert diff.base_ranges == [(2, 2)]


def test_added_and_deleted_files(repo):
    (repo / "c.py").write_text("Y = 2\n")
    (repo / "b.py").unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "add c, drop b")
    by_path = {d.path: d for d in diff_range(repo, "HEAD~1", "HEAD")}
    assert by_path["c.py"].status == "added"
    assert by_path["c.py"].head_ranges == [(1, 1)]
    assert by_path["c.py"].base_ranges == []
    assert by_path["b.py"].status == "deleted"
    assert by_path["b.py"].head_ranges == []
    assert by_path["b.py"].base_ranges == [(1, 1)]


def test_pure_insertion_has_empty_base_range(repo):
    (repo / "a.py").write_text(
        "def f():\n    return 1\n\n\ndef g():\n    x = 0\n    return 2\n"
    )
    git(repo, "commit", "-am", "insert line in g")
    diff = diff_range(repo, "HEAD~1", "HEAD")[0]
    assert diff.head_ranges == [(6, 6)]
    assert diff.base_ranges == []


def test_show_file(repo):
    base = git(repo, "rev-parse", "HEAD")
    (repo / "a.py").write_text("changed\n")
    git(repo, "commit", "-am", "change")
    assert "def f():" in show_file(repo, base, "a.py")
    assert show_file(repo, base, "missing.py") is None


def test_bad_ref_raises(repo):
    with pytest.raises(RuntimeError):
        diff_range(repo, "no-such-ref", "HEAD")


def test_path_with_spaces(repo):
    """Paths with spaces must not retain the trailing tab git appends."""
    spaced = repo / "with space.py"
    spaced.write_text("hello\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "add spaced file")

    # Modify it so it shows up in the diff
    spaced.write_text("hello\nworld\n")
    git(repo, "commit", "-am", "modify spaced file")

    diffs = diff_range(repo, "HEAD~1", "HEAD")
    assert len(diffs) == 1
    assert diffs[0].path == "with space.py"

    base = git(repo, "rev-parse", "HEAD~1")
    content = show_file(repo, base, "with space.py")
    assert content is not None
    assert "hello" in content


def test_sql_comment_lines_no_phantom_diffs(repo):
    """Content lines starting with '++' or '--' must not create phantom FileDiff entries."""
    sql_file = repo / "query.sql"
    sql_file.write_text("SELECT 1;\n-- a comment\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "add sql file")

    # Delete the SQL comment line and add a '++ weird' content line
    sql_file.write_text("SELECT 1;\n++ weird added line\n")
    git(repo, "commit", "-am", "replace comment with weird line")

    diffs = diff_range(repo, "HEAD~1", "HEAD")
    assert len(diffs) == 1
    assert diffs[0].path == "query.sql"
    assert diffs[0].status == "modified"


def test_multi_hunk_change_accumulates_ranges(repo):
    """Two separate hunks in one commit must accumulate on the same FileDiff."""
    # a.py already has 6 lines; modify line 2 and line 6
    (repo / "a.py").write_text(
        "def f():\n    return 99\n\n\ndef g():\n    return 99\n"
    )
    git(repo, "commit", "-am", "change lines 2 and 6")

    diffs = diff_range(repo, "HEAD~1", "HEAD")
    assert len(diffs) == 1
    diff = diffs[0]
    assert diff.path == "a.py"
    assert len(diff.head_ranges) == 2
    assert diff.head_ranges[0] == (2, 2)
    assert diff.head_ranges[1] == (6, 6)


def test_three_dot_excludes_upstream_commits(repo):
    default = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    git(repo, "checkout", "-b", "feature")
    (repo / "a.py").write_text("def f():\n    return 99\n\n\ndef g():\n    return 2\n")
    git(repo, "commit", "-am", "feature: change f")
    git(repo, "checkout", default)
    (repo / "b.py").write_text("X = 999\n")
    git(repo, "commit", "-am", "main: change b")
    main = git(repo, "rev-parse", "HEAD")
    three = {d.path for d in diff_range(repo, main, "feature", three_dot=True)}
    assert three == {"a.py"}  # only the PR's own commit
    two = {d.path for d in diff_range(repo, main, "feature", three_dot=False)}
    assert two == {"a.py", "b.py"}  # tree diff blames the upstream b.py change too


def test_default_is_three_dot(repo):
    default = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    git(repo, "checkout", "-b", "feature")
    (repo / "a.py").write_text("def f():\n    return 99\n\n\ndef g():\n    return 2\n")
    git(repo, "commit", "-am", "feature: change f")
    git(repo, "checkout", default)
    (repo / "b.py").write_text("X = 999\n")
    git(repo, "commit", "-am", "main: change b")
    main = git(repo, "rev-parse", "HEAD")
    assert {d.path for d in diff_range(repo, main, "feature")} == {"a.py"}


def test_no_merge_base_falls_back_without_crashing(repo):
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "--orphan", "orphan")
    git(repo, "rm", "-rf", ".")
    (repo / "z.py").write_text("Z = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "orphan root")
    diffs = diff_range(repo, base, "orphan", three_dot=True)  # must not raise
    assert isinstance(diffs, list)
