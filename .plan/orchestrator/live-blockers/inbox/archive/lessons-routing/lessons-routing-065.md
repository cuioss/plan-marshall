envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T10:27:06Z

# The success-criteria parser drops every criterion after a wrapped line, so the frozen snapshot and the functional review grade only part of a deliverable

Severity: **high** (graded at the 2026-11-02 sweep: the review gate grades only some of the frozen criteria and does not say so).
Bundle: `plan-marshall` (`manage-solution-outline` `_criteria_snapshot.py`, used by `phase-6-finalize` review_support).

## Sources (API-Sheriff epic api-sheriff-0-2-0)

- `api-sheriff-api-sheriff-0-2-0-004`: plan-v02-28-validator-limit-rules, PR cuioss/API-Sheriff#467. Five criteria bullets parsed as one criterion; the verdict had to merge them into one row.
- `plan-v02-46-upstream-close-after-early-answer-001`: PR cuioss/API-Sheriff#513 (merge e70743f). `work/criteria-snapshot.json` kept only the first line of the first bullet per deliverable; sealing a verdict that graded C2..Cn was refused with `unknown_criterion_id`.

## Ground truth (c431a8193)

- `_criteria_snapshot.py:72`: `_SUCCESS_CRITERIA_RE = \*\*Success Criteria:\*\*\s*((?:- [^\n]+\n?)+)` captures only an unbroken run of lines beginning with `- `. A wrapped bullet's continuation line, an indented sub-bullet or a `*` bullet ends the run.
- `outline_deliverables` (~`:657-670`) splits that capture into `success_criteria` and is "the one success-criteria parser in the tree"; the finalize attribution module delegates to it.
- Everything after the first line not beginning with `- ` is missing from the frozen snapshot. Because `criteria_drift` and `open_criteria` compare against that snapshot, a dropped criterion is never graded, never open and never reported as drift.
- Not re-run against a fixture here.

## What to consider

- Parse each top-level bullet, with its continuation lines, as one criterion; report a block that cannot be parsed, never drop it.
- Print the parsed count in `snapshot-criteria` and `review_support validate` output so a mismatch with the outline shows.
- Add a regression fixture with several multi-line bullets; check plans already frozen with the old parser for dropped criteria.
