envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=landing
created=2026-07-29T11:56:14Z

## What landed

PR #1050 (branch `feature/wrong-store-guard-refuses-project-local-lessons`), 2 commits + 1 review-fix commit (`28a1e041d`). Fixes the `wrong_store` guard in `manage-lessons.py` refusing project-local lessons.

## Hypothesis outcome

The spec's HYPOTHESIS was REFUTED at outline: `manage-lessons.py:399` and `:797` do NOT carry two split derivations of the store-ownership check. Both call sites route through one shared `guard_component_store_match` helper — the split exists exactly once. There is no half-live-defect risk from a second, un-synced derivation.

## Ambiguity resolved without an operator round-trip (D1)

`COMPONENT_RE` already admits zero-or-more colon segments, so a prefix-less component string was already well-formed input, not free-form text. That fact alone settled the "should we accept any string" branch the spec had flagged as undecided — no `AskUserQuestion` was needed.

## New defect found at outline

`cmd_from_error` coerces a missing/non-string `component` value to the literal string `'unknown'`, which is prefix-less. In production (no `PLAN_BASE_DIR` test override), that path was refused by the store guard 100% of the time. This was outside the spec's stated hypothesis and became the actual root cause fixed by this plan.

## Contract change (operator-accepted)

`from-error` now REJECTS an explicitly-supplied non-string `component` instead of silently defaulting it to `'unknown'`. Two pre-existing tests pinned the old (silent-default) behavior and were rewritten; a third test was added so the still-valid absent-component default keeps coverage.

## Review-gap accepted

The review-fix commit `28a1e041d` was reviewed by no bot: Sourcery hit `hard_quota`, CodeRabbit's review is timestamped against the first commit only, and pr-agent has no `synchronize` trigger so its check never re-ran. An explicit re-review was requested and awaited 319s with no new review submitted. Operator accepted the gap explicitly.

## Residue for the epic

Six candidate-lesson messages follow this one, covering: (1) the refuted-hypothesis finding itself, (2) a vacuous-guard-introduced-by-a-fix recurrence (with an associated test-pins-the-defect instance), (3) the review-bot green-check-lie recurrence, and three tooling defects found in-flight — a false light-lane routing signal from the change-type/scope-estimate heuristics, a light-lane gap that hard-fails `phase-3-outline` on `pr_title_missing`, and a structurally-impossible self-cwd-pin instruction in `phase-5-execute` Step 2.5.
