import re
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class FileDiff(BaseModel):
    """Changed line ranges for one file between two refs.

    Ranges are 1-based inclusive (start, end) tuples. A pure insertion has no
    base range; a pure deletion has no head range.
    """

    path: str
    status: Literal["added", "modified", "deleted"]
    base_ranges: list[tuple[int, int]]
    head_ranges: list[tuple[int, int]]


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def show_file(root: Path, ref: str, path: str) -> str | None:
    """Return the file's content at the given ref, or None if absent there."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout if result.returncode == 0 else None


def _range(start: int, count: int | None) -> tuple[int, int] | None:
    """Hunk header side -> inclusive range; count 0 means no lines on that side."""
    n = 1 if count is None else count
    return (start, start + n - 1) if n > 0 else None


def diff_range(root: Path, base: str, head: str = "HEAD") -> list[FileDiff]:
    """Parse `git diff -U0 base..head` into per-file changed line ranges."""
    output = _git(
        root,
        "-c", "core.quotePath=false",
        "diff", "--no-color", "--no-renames", "--unified=0", f"{base}..{head}",
    )
    diffs: list[FileDiff] = []
    old_path: str | None = None
    in_header = False  # True after "diff --git", False once first @@ is seen
    for line in output.splitlines():
        if line.startswith("diff --git "):
            in_header = True
            old_path = None
        elif in_header and line.startswith("--- "):
            target = line[4:].rstrip("\t")
            old_path = None if target == "/dev/null" else target.removeprefix("a/")
        elif in_header and line.startswith("+++ "):
            target = line[4:].rstrip("\t")
            new_path = None if target == "/dev/null" else target.removeprefix("b/")
            if new_path is None:
                status: Literal["added", "modified", "deleted"] = "deleted"
            elif old_path is None:
                status = "added"
            else:
                status = "modified"
            path = new_path or old_path
            assert path is not None  # git always names at least one side
            diffs.append(FileDiff(path=path, status=status, base_ranges=[], head_ranges=[]))
        elif (match := _HUNK.match(line)) and diffs:
            in_header = False  # first @@ clears header mode for this file
            base_count = int(match.group(2)) if match.group(2) else None
            head_count = int(match.group(4)) if match.group(4) else None
            if base_range := _range(int(match.group(1)), base_count):
                diffs[-1].base_ranges.append(base_range)
            if head_range := _range(int(match.group(3)), head_count):
                diffs[-1].head_ranges.append(head_range)
    return diffs
