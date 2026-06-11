import json

from docpulse.repair.prompts import REPAIRER_SYSTEM_PROMPT, build_repair_user_message
from docpulse.repair.repairer import RepairBundle, repair


class FakeToolCall:
    def __init__(self, name, args, call_id="c1"):
        self.id = call_id
        self.type = "function"

        class Fn:
            pass

        self.function = Fn()
        self.function.name = name
        self.function.arguments = (
            args if isinstance(args, str) else json.dumps(args)
        )


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeClient:
    def __init__(self, messages):
        self._messages = list(messages)
        self.calls = 0

    def complete(self, messages, tools=None):
        self.calls += 1
        return self._messages.pop(0)


def _bundle():
    return RepairBundle(
        section_id="docs/auth.md#login",
        doc_content="Call `login(user)` to sign in.",
        diagnosis="The parameter `user` was renamed to `username`.",
        evidence=["src/auth.py:10"],
        old_code="def login(self, user): ...",
        new_code="def login(self, username): ...",
        intent="Rename user -> username for clarity.",
    )


def test_system_prompt_demands_preservation_and_citation():
    lowered = REPAIRER_SYSTEM_PROMPT.lower()
    assert "preserve" in lowered
    assert "only" in lowered  # touch only the inaccurate parts
    assert "cite" in lowered or "rationale" in lowered


def test_user_message_includes_all_bundle_parts():
    body = build_repair_user_message(_bundle())["content"]
    assert "docs/auth.md#login" in body
    assert "login(user)" in body                 # original doc content
    assert "renamed to `username`" in body       # diagnosis
    assert "src/auth.py:10" in body              # evidence
    assert "def login(self, username)" in body   # new code
    assert "Rename user -> username" in body     # intent


def test_repair_returns_repair_from_first_call():
    client = FakeClient([
        FakeMessage(tool_calls=[FakeToolCall("submit_repair", {
            "new_content": "Call `login(username)` to sign in.",
            "rationale": "Renamed user -> username (src/auth.py:10).",
            "confidence": 0.9,
        })]),
    ])
    result = repair(client, _bundle())
    assert result.section_id == "docs/auth.md#login"  # injected, not trusted
    assert result.new_content == "Call `login(username)` to sign in."
    assert result.confidence == 0.9
    assert result.validation_passed is False          # not yet validated
    assert "username" in result.rationale
    assert client.calls == 1


def test_repair_confidence_clamped_to_unit_interval():
    client = FakeClient([
        FakeMessage(tool_calls=[FakeToolCall("submit_repair", {
            "new_content": "x", "rationale": "y", "confidence": 5.0,
        })]),
    ])
    assert repair(client, _bundle()).confidence == 1.0


def test_repair_retries_once_on_malformed_then_succeeds():
    bad = FakeToolCall("submit_repair", "{not valid json")
    good = FakeToolCall("submit_repair", {
        "new_content": "fixed", "rationale": "r", "confidence": 0.5,
    })
    client = FakeClient([
        FakeMessage(tool_calls=[bad]),
        FakeMessage(tool_calls=[good]),
    ])
    result = repair(client, _bundle())
    assert result.new_content == "fixed"
    assert client.calls == 2


def test_repair_failure_returns_safe_unchanged_content():
    # Two malformed attempts -> give up; propose NO change (original content),
    # confidence 0, validation_passed False so routing will skip it.
    bad = FakeToolCall("submit_repair", "{still bad")
    client = FakeClient([
        FakeMessage(tool_calls=[bad]),
        FakeMessage(tool_calls=[bad]),
    ])
    result = repair(client, _bundle())
    assert result.new_content == _bundle().doc_content  # unchanged = safe
    assert result.confidence == 0.0
    assert result.validation_passed is False


def test_repair_llm_error_returns_safe_failure():
    from docpulse.llm import LLMError

    class BoomClient:
        def complete(self, messages, tools=None):
            raise LLMError("boom")

    result = repair(BoomClient(), _bundle())
    assert result.confidence == 0.0
    assert result.validation_passed is False
    assert result.new_content == _bundle().doc_content
