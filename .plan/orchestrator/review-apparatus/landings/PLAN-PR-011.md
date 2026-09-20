# Landing: PLAN-PR-011 — Review bots catch what in-house gates cannot

epic: review-apparatus · workstream: WS-03 · shipped 2026-08-15
cloud run: `cloud-runs/130-review-bots-catch-what-in-house-gates-cannot/`
PR #1239 (`622f44843`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `partially-implemented`.**

## The pre-run drop was honoured, and its residue handled correctly

The epic spec's D2 — a checks-status presence probe distinguishing a structurally-absent bot from an
in-progress one — was confirmed already shipped and dropped before the run. The run did **not**
silently re-absorb it. Instead it produced *retirement evidence*: it re-derived the closure against
current main (`STATE_ABSENT` / `STATE_IN_PROGRESS` are distinct members with distinct `classify_bot`
branches; `not_triggered` refines `absent` further — verification: **accurate**) and added
`TestAbsentVersusInProgressDistinction` as a regression pin, **explicitly labelled as a pin that
cannot fail pre-fix**, with mutation discrimination supplied instead. That labelling is the correct
handling of a dropped deliverable's residue.

**Deliverables: 4 executed (+1 dropped pre-run) — 1 done (D1), 1 verified-with-gaps (D3), 2 partial
(D0, D2).**

## ⛔ The metric CAN produce the exact inversion the plan said must not ship

`130 G1`, severity **blocker**. `structural_share: 100.0` at `reviewer_coverage: 1/1` the moment the
caller-supplied roster shrinks — same escapes, same partition, same SHAs. The guarantee is stated
absolutely at four sites, none of them true, and the same overstatement sits in
`review_gate_delta.py:52-60` and `bot-participation-contract.md:601-611`.

Claimed by **PLAN-PR-030** (ex-`560`) D1.

## Report claims the verification found false

- "The share is emitted only at full reviewer coverage, so a collapse can only move the metric from a
  number to no number, never to a better one" — **false**, probe above.
- "on the current step ordering the only measurable PRs are those where **neither** post-gate mutating
  step committed anything" — overstated; the quality gate declares no `verdict_inputs`, so every HEAD
  advance re-fires it. (The pessimistic conclusion survives via the mixed-SHA exclusion; the stated
  mechanism and the word "ONLY" are wrong.)
- Finding #19's rationale — "keyed on `author` while the sibling keyed on `bot_kind` → divergence on
  every GitLab finding" — **false as to the rationale**: `gitlab_pr.py:274-282` passes no selector at
  all, and on GitHub the fallback is dead too.
- "100 tests added across six files" — **91** across **eight**. "5 production scripts, 7 test files" —
  **six** production `.py`, **eight** test files.
- "Final `./pw verify`: 19748 passed" — the squash commit message of the same run says **19752**.
- Finding #13's parity obligation is now **stale**: `review_retrospective._is_status_summary` delegates
  to `review_gate_delta.is_status_summary`, so the parity test compares a function with itself.

## Gaps: 18 — 16 full, 2 partial, 0 uncovered

- **partial**: G4 (PLAN-PR-030 D3 corrects five of the six sites the gap names; the sixth —
  `report-01.md` § D2's selection-effect restatement — fell between PLAN-PR-030 and PLAN-PR-031
  silently, because 560's out-of-scope names only the tallies and verify totals), G18 (PLAN-PR-031 D4.8
  records the obligation with a re-derived scope and explicitly declines the mutation pass; the
  ~80-test sweep over four suites remains work nobody is scheduled to do)

## ⛔ A fourth editor of the shared Consumers table exists that the README does not name

The README warns about PLAN-PR-030 vs PLAN-PR-024/025 on `bot-participation-contract.md`'s § Consumers
table. But **PLAN-PR-026 D2's three-valued `participation` change invalidates the
`finalize-step-review-retrospective` row** (verified in the tree: it states "each carrying
`participation: measured` / `unmeasurable`"), while PLAN-PR-026's own § Expected surface names that
document only for "the verdict-vocabulary restatement". Resolve before scheduling 026 and 030 near each
other.

## Standing facts

- **The archetype relocates one argument to the left.** Plan 050's fix closed "benign no-op on an empty
  store" and left `measured` earned by META records and `vacuous` asserted from an omitted argument.
  Both were found by reading argparse defaults and the raw-vs-filtered operand against the legend
  string — neither by testing.
- **`130 G7` is live at HEAD** — re-verified by reading the Consumers table: the
  `review_gate_delta assess` row still reads *"the two implement the same rule independently … so a
  change to the rule must land in both"*, false since the retrospective imports the predicate.
