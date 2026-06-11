import subprocess
from pathlib import Path

import pytest

from docpulse.config import CodeGlobs, Config, DocGlob
from docpulse.indexing.index_store import build_index
from docpulse.models import Verdict
from docpulse import pipeline


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


class FakeContext:
    def __init__(self, intent: str) -> None:
        self._intent = intent

    def get_intent(self) -> str:
        return self._intent


def _config() -> Config:
    return Config(
        docs=[DocGlob(path="**/*.md")],
        code=CodeGlobs(include=["**"], exclude=[]),
    )


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "auth.py").write_text(
        "class AuthService:\n    def login(self, user):\n        return user\n"
    )
    (tmp_path / "auth.md").write_text(
        "# Login\n\nCall `AuthService.login` with a user.\n"
    )
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "base")
    base = git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "auth.py").write_text(
        "class AuthService:\n    def login(self, username):\n        return username\n"
    )
    git(tmp_path, "commit", "-am", "rename param")
    return tmp_path, base


def test_check_mode_collects_verdicts_and_exit_code(repo, monkeypatch):
    root, base = repo
    config = _config()
    index = build_index(root, config, embedder=None, base_commit=git(root, "rev-parse", "HEAD"))
    monkeypatch.setattr(
        pipeline, "verify",
        lambda client, r, idx, bundle, n: Verdict(
            section_id=bundle.section_id, status="stale", confidence=0.9,
            diagnosis="param renamed", evidence=["auth.py:2"],
        ),
    )
    result = pipeline.run_pipeline(
        root, base, "HEAD", config, client=object(), index=index,
        context=FakeContext("rename"), mode="check",
    )
    assert result.suspects_checked >= 1
    assert any(v.status == "stale" for v in result.verdicts)
    assert result.exit_code == 1
    assert result.repairs == []


def test_stale_index_warns_when_head_differs(repo, monkeypatch):
    root, base = repo
    config = _config()
    index = build_index(root, config, embedder=None, base_commit=base)  # built at OLD commit
    monkeypatch.setattr(
        pipeline, "verify",
        lambda *a, **k: Verdict(section_id="x", status="accurate", confidence=0.0,
                                diagnosis="", evidence=[]),
    )
    warnings: list[str] = []
    pipeline.run_pipeline(
        root, base, "HEAD", config, client=object(), index=index,
        context=FakeContext(""), mode="check", warn=warnings.append,
    )
    assert any("re-run `docpulse index`" in w for w in warnings)


def test_repair_mode_repairs_high_confidence_stale(repo, monkeypatch):
    root, base = repo
    config = _config()
    index = build_index(root, config, embedder=None, base_commit=git(root, "rev-parse", "HEAD"))
    monkeypatch.setattr(
        pipeline, "verify",
        lambda client, r, idx, bundle, n: Verdict(
            section_id=bundle.section_id, status="stale", confidence=0.9,
            diagnosis="param renamed", evidence=["auth.py:2"],
        ),
    )
    from docpulse.models import Repair

    def fake_repair(client, bundle):
        return Repair(section_id=bundle.section_id, new_content="fixed",
                      confidence=0.9, validation_passed=False, rationale="renamed user->username")

    def fake_validate(client, repair_obj, bundle, min_preservation=0.5):
        return repair_obj.model_copy(update={"validation_passed": True})

    monkeypatch.setattr("docpulse.repair.repairer.repair", fake_repair)
    monkeypatch.setattr("docpulse.repair.validator.validate", fake_validate)

    result = pipeline.run_pipeline(
        root, base, "HEAD", config, client=object(), index=index,
        context=FakeContext("rename"), mode="repair",
    )
    assert len(result.repairs) == 1
    assert result.repairs[0].validation_passed is True
    assert result.repairs[0].rationale == "renamed user->username"


def test_repair_mode_skips_low_confidence_stale(repo, monkeypatch):
    root, base = repo
    config = _config()
    index = build_index(root, config, embedder=None, base_commit=git(root, "rev-parse", "HEAD"))
    monkeypatch.setattr(
        pipeline, "verify",
        lambda client, r, idx, bundle, n: Verdict(
            section_id=bundle.section_id, status="stale", confidence=0.2,
            diagnosis="maybe", evidence=[],
        ),
    )
    result = pipeline.run_pipeline(
        root, base, "HEAD", config, client=object(), index=index,
        context=FakeContext(""), mode="repair",
    )
    assert result.repairs == []  # below flag_threshold -> not repaired
