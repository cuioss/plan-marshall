envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:21Z

# A success criterion operationalized as a content sweep can disagree with the rosters it is meant to police

**Signal**: Q-Gate finding (`3-outline`, hash `98e7f3`, severity `error`, resolution `taken_into_account`)
**Component**: `plan-marshall:phase-3-outline`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## What was observed

Deliverable 1's success criterion — "7 recorded D3 verdicts; `NON_CLI_LIBRARY` carries exactly `effort_presets.py` and `manage_terminal_title.py`" — was operationalized as a content sweep over the worktree. The sweep's population (entry-point scripts, `architecture search --content --literal 'if __name__ ==' --category script` → `count: 118`, `files_scanned: 432`, `unreadable: 0`) is by construction incapable of producing the deliverable's own FOURTH class, "publishes no top-level CLI script at all" — every member of the swept set IS a CLI entry point.

The consequence was a roster asymmetry: `SEAM_EXEMPT` was tree-derived and asserted bidirectionally, while `NON_CLI_LIBRARY` was a hand-transcribed closed 2-row roster with no derived population behind it. A verified unenumerated member existed at outline time (`tools-input-validation/input_validation.py` and `schema_validation.py` — a skill directory shipping two scripts, neither in the 118-entry-point set). Deriving the class properly yielded **5** modules across 4 skills, not the 2 transcribed.

## Why it is candidate-lesson material

The defect is not the wrong number; it is that the criterion's operationalization silently narrowed the population it claimed to cover, and the narrowing was invisible from the criterion's own text. A criterion whose check cannot in principle observe one of its own declared classes reads as satisfied while that class goes unpoliced — the same un-re-derived-census staleness the plan existed to close, reintroduced one deliverable down.

## Proposed rule (for orchestrator judgement)

When a success criterion names a closed roster, require the roster to be **derived from the same tree walk** that produces the population and asserted equal in **both** directions — or require an explicit recorded rationale for the excluded class. A hand-transcribed roster beside a derived sibling in the same deliverable is the detectable shape.

## Related already-active lessons

- `2026-09-03-07-005` — "A success criterion must be operationalizable from the outline alone" (`plan-marshall:phase-3-outline`)
- `2026-08-25-09-011` — `search --content` patterns are regexes, so a metacharacter-bearing query can return a false zero
