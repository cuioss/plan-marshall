# Landing Analysis: PLAN-CIS-006 — Validate precision

epic: code-intelligence-substrate
workstream: WS-03
pr: 1254
merge_commit: `3d96e4084`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/230-validate-precision/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 7 of 7 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

A genuine and reproduced precision win: the validator went from 380 unresolved (97.4% false positive, unusable as a gate) to 61. The run also discovered a **live production bug** in execute-task's plan-id injection — 4 of 8 whitelisted notations can never fire — and shipped two regression-test locks that cannot fail against the defects they claim to guard.

## Premise verdict

The plan's own "three distinct detector confusions" framing **did not survive full enumeration**: the largest class (decision-log prefixes, 38.2%) was unnamed by the plan. The "majority of rows are the three named classes" claim held only barely at 52.1%, materially understating the real work.

## Gaps carried out of this landing

**21 total — 1 high, 10 medium, 10 low.** High: G5.

- ⛔ **A live production bug exists TODAY** (G5, high): execute-task's Bucket-B plan-id injection whitelist has 4 of 8 entries inert (two misspelled, further gated by a run-only subcommand check), so silent-wrong-checkout risk is live for `ci` / `sonar` / `pr_doctor` calls lacking `--plan-id`.
- **`SKILL.md`'s claim that "none of the exclusions can hide a real reference" is false** — a genuinely broken reference wearing an excluded shape is still dropped silently; only the adjacent valid-reference case was fixed.
- Two shipped regression locks cannot fail against their own targets.

## Inconsistencies found, and what was verified

- Report's round-1 finding count said "13" | verified by counting the round-1 table's own rows | **verdict: 14** (F2b and S1-S3 were undercounted).

## Residue

27 of 61 unresolved rows sit outside the indexed-bundle namespace and are untriaged — the plan's own reasoning says these owe a fail-closed partition, not a suppression. Five pre-existing unconditional drops remain fail-open (the comment-line skip alone hides nine real resolvable notations).

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-006 --status shipped`
- [x] row `pr` stamped `1254` — `orchestrator queue --set-row PLAN-CIS-006 --field pr --value 1254`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-006 --field landing --value landings/PLAN-CIS-006.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

**G5 is the most urgent single item in batch A** — it is a live production defect, not a measurement gap. Routes to **PLAN-CIS-052** (`540`). The two vacuous locks route to **PLAN-CIS-053** (`550`).
