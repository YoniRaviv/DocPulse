from docpulse.verification.prompts import SYSTEM_PROMPT, build_user_message
from docpulse.verification.verifier import VerifyBundle


def test_system_prompt_forbids_guessing_stale():
    lowered = SYSTEM_PROMPT.lower()
    assert "unverified" in lowered
    assert "stale" in lowered


def test_user_message_includes_all_bundle_parts():
    bundle = VerifyBundle(
        section_id="docs/auth.md#login",
        doc_content="Call AuthService.login(user).",
        old_code="def login(self, user): ...",
        new_code="def login(self, username): ...",
        intent="Rename user -> username for clarity.",
    )
    msg = build_user_message(bundle)
    assert msg["role"] == "user"
    body = msg["content"]
    assert "docs/auth.md#login" in body
    assert "AuthService.login(user)" in body          # doc content
    assert "def login(self, user)" in body            # old code
    assert "def login(self, username)" in body        # new code
    assert "Rename user -> username" in body           # intent


def test_user_message_handles_empty_intent():
    bundle = VerifyBundle(
        section_id="s", doc_content="d", old_code="o", new_code="n", intent=""
    )
    body = build_user_message(bundle)["content"]
    assert "(no intent provided)" in body
