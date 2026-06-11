# DocPulse Eval Cases

Each case is one directory:

```
<case-name>/
├── before/        # code BEFORE the change (mirrors a repo subtree)
├── after/         # code AFTER the change
├── doc.md         # the documentation section under test
└── label.yml      # ground truth
```

`label.yml`:

```yaml
status: stale | accurate     # is the doc now wrong because of the change?
intent: "one line: why the code changed (the PR-description equivalent)"
reference_correction: "the corrected doc text (used by Phase 4 repair eval; '' if accurate)"
```

`docpulse eval --cases evals/cases --model <m>` runs the verifier over every case
and reports precision/recall. Positive class = `stale`; `unverified` counts as
"not stale".

**Golden rule:** every real-world false positive becomes a new `accurate` case here.
Cases must be hand-verified — a wrong label silently corrupts the metric.

## Repair eval (Phase 4)

`docpulse eval --cases evals/cases --model <m> --repair` additionally runs the
repairer + validator over every **stale** case and reports repair quality:

- **preservation** — fraction of the original section's paragraph blocks that
  survive byte-identical in the repaired section (deterministic; the exit-gate
  metric is "% of stale cases with preservation ≥ 0.95").
- **tier** — `auto_fix` / `draft` / `skip` from confidence routing.
- **rubric** — an LLM judge scores the repair against `reference_correction`
  on accuracy / completeness / style-fidelity (1–5) and flags cases needing a
  human spot-check.

The repair eval **synthesizes** a stale verdict from each `label.yml` (it does
not run the verifier), so it measures repair quality in isolation. Set
`repair_model:` in `docpulse.yml` to use a different model for repair than for
verify (falls back to `model:`).
