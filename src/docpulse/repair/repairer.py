import json
from dataclasses import dataclass
from typing import Any

from docpulse.llm import LLMError
from docpulse.models import Repair


@dataclass(frozen=True)
class RepairBundle:
    """Everything the repairer needs to rewrite one stale doc section."""

    section_id: str
    doc_content: str       # original (stale) section text
    diagnosis: str         # from the verdict: what is wrong
    evidence: list[str]    # from the verdict: path:line references
    old_code: str
    new_code: str
    intent: str


_MAX_ATTEMPTS = 2

SUBMIT_REPAIR_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "submit_repair",
        "description": "Submit the corrected documentation section.",
        "parameters": {
            "type": "object",
            "properties": {
                "new_content": {"type": "string"},
                "rationale": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["new_content", "rationale", "confidence"],
        },
    },
}


def _failed_repair(bundle: RepairBundle, reason: str) -> Repair:
    """Safe fallback: propose no change so routing skips it."""
    return Repair(
        section_id=bundle.section_id,
        new_content=bundle.doc_content,
        confidence=0.0,
        validation_passed=False,
        rationale=f"repair failed: {reason}",
    )


def _repair_from_args(bundle: RepairBundle, args: dict[str, Any]) -> Repair:
    return Repair(
        section_id=bundle.section_id,            # injected, never trusted from model
        new_content=str(args["new_content"]),
        confidence=max(0.0, min(1.0, float(args.get("confidence", 0.0)))),
        validation_passed=False,                 # validator sets this later
        rationale=str(args.get("rationale", "")),
    )


def repair(client: Any, bundle: RepairBundle) -> Repair:
    """Single-shot structured-output repair with one retry on malformed output.

    `client` must expose `complete(messages, tools) -> message` (see LLMClient).
    Any failure returns a safe Repair that proposes NO change (validation_passed
    False, confidence 0) so confidence routing will skip it.
    """
    # Imported lazily so prompts.py (which imports RepairBundle from this module)
    # has no circular dependency at module load.
    from docpulse.repair.prompts import REPAIRER_SYSTEM_PROMPT, build_repair_user_message

    messages: list[Any] = [
        {"role": "system", "content": REPAIRER_SYSTEM_PROMPT},
        build_repair_user_message(bundle),
    ]
    # NOTE: the prose-nudge path and the malformed-JSON retry both consume from
    # this attempt budget; the fail-safe fallback keeps any exhaustion safe.
    for _ in range(_MAX_ATTEMPTS):
        try:
            message = client.complete(messages, tools=[SUBMIT_REPAIR_SCHEMA])
        except LLMError as exc:
            return _failed_repair(bundle, f"llm error: {exc}")
        except Exception as exc:  # noqa: BLE001 — normalize any client failure
            return _failed_repair(bundle, f"unexpected client error: {exc}")

        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            messages.append({"role": "assistant", "content": message.content or ""})
            messages.append({
                "role": "user",
                "content": "Call submit_repair with the corrected section; no prose.",
            })
            continue

        messages.append(message)  # assistant turn carrying the tool_calls
        call = tool_calls[0]
        try:
            args = json.loads(call.function.arguments or "{}")
            built = _repair_from_args(bundle, args)
            messages.append({
                "role": "tool", "tool_call_id": call.id,
                "name": call.function.name, "content": "repair received",
            })
            return built
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            messages.append({
                "role": "tool", "tool_call_id": call.id,
                "name": call.function.name,
                "content": "error: invalid submit_repair arguments; resend.",
            })
            continue

    return _failed_repair(bundle, "no valid repair after retry")
