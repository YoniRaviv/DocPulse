from docpulse.repair.repairer import RepairBundle

REPAIRER_SYSTEM_PROMPT = """\
You are DocPulse's documentation repairer. You are given a documentation section \
that has been confirmed STALE by a verifier, the diagnosis of what is wrong, and \
the code change (OLD and NEW) that caused it. Produce a corrected version of the \
section.

Hard constraints:
- Preserve the section's style, tone, formatting, and structure exactly.
- Touch ONLY the parts made inaccurate by the change. Leave every still-correct \
sentence, code block, and paragraph byte-for-byte identical. Do not reword, \
reorder, or "improve" anything that is already correct.
- Base the fix on what the NEW code actually does. Do not invent behavior.
- Return the FULL corrected section text in `new_content` (not a diff).

Call `submit_repair` exactly once with:
- new_content: the complete corrected section.
- rationale: one or two sentences citing the specific code change that caused the \
fix (include a path:line reference where possible).
- confidence: 0..1 — how sure you are the correction is accurate and complete.
"""


def build_repair_user_message(bundle: RepairBundle) -> dict[str, str]:
    evidence = "\n".join(f"- {e}" for e in bundle.evidence) or "(none)"
    intent = bundle.intent.strip() or "(no intent provided)"
    content = f"""\
## Stale documentation section: {bundle.section_id}

{bundle.doc_content}

## Diagnosis (why it is stale)

{bundle.diagnosis}

## Evidence

{evidence}

## Change intent (why the code changed)

{intent}

## Code BEFORE the change

```
{bundle.old_code}
```

## Code AFTER the change

```
{bundle.new_code}
```

Rewrite the section, changing only what the code change made inaccurate, then \
call submit_repair."""
    return {"role": "user", "content": content}
