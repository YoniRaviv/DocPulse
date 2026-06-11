from pathlib import Path

from docpulse.context.git_context import GitContext


def test_intent_from_env_includes_tickets():
    ctx = GitContext(
        Path("."), "base", "head",
        env={"PR_TITLE": "Fix login flow", "PR_BODY": "Closes PROJ-42 and JIRA-7"},
        run_command=lambda args: "",
    )
    intent = ctx.get_intent()
    assert "Fix login flow" in intent
    assert "Closes PROJ-42" in intent
    assert "Tickets: JIRA-7, PROJ-42" in intent  # sorted, de-duped


def test_intent_falls_back_to_commit_messages():
    ctx = GitContext(
        Path("."), "base", "head",
        env={},
        run_command=lambda args: "rename login param\n\ndetailed body\n",
    )
    intent = ctx.get_intent()
    assert "Commits:" in intent
    assert "rename login param" in intent


def test_intent_empty_when_nothing_available():
    ctx = GitContext(Path("."), "b", "h", env={}, run_command=lambda args: "")
    assert ctx.get_intent() == ""


def test_get_intent_satisfies_protocol():
    from docpulse.context.base import ContextProvider

    ctx: ContextProvider = GitContext(Path("."), "b", "h", env={}, run_command=lambda a: "")
    assert isinstance(ctx.get_intent(), str)
