# DocPulse

## Status

Phase 2 complete — `docpulse check --base <ref>` diffs base..head, filters comment/whitespace-only changes via tree-sitter token comparison, and prints linked doc sections ranked by link score × change size (capped by `budget.max_suspects_per_run`, honest "N of M" reporting). Still fully deterministic and keyless with `--heuristics-only` indexing.

## Usage

```bash
docpulse index --root .                              # build the code<->docs link index
docpulse check --base origin/main                    # verify docs vs the PR diff (exit 1 on drift)
docpulse check --base origin/main --suspects-only    # keyless: list suspect sections only
docpulse repair --base origin/main                   # print proposed doc fixes + dry-run PR plan
docpulse repair --base origin/main --write           # also apply fixes to doc files locally (no push)
```

`check` exits 0 (clean), 1 (a doc section is stale above the confidence threshold),
or 2 (setup/tool error). Live branch push + PR creation arrive in Phase 6.
