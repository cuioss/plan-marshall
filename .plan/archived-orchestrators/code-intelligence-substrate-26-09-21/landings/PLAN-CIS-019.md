# Landing Analysis: PLAN-CIS-019 — Manifest cross-check discards the production tree

epic: code-intelligence-substrate
workstream: WS-04
pr: 1288
merge_commit: `eb0124c96`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/320-manifest-cross-check-discards-production-tree/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 6 of 6 deliverables shipped. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

Both private `_BOOKKEEPING_PREFIXES` copies — the originating report named only one; D0's population sweep correctly found two — were replaced with a shared oracle lookup against `build.map`, reproducing the exact 10-of-11-discarded shape in the clone and confirming zero discarded post-fix. The previously-unreachable rule now fires on the composer's real step shape, and an unresolvable diff-file path fails loudly instead of degrading to a skip. **But the sibling rule still reports "no diff data available" over a diff it demonstrably received**, and the routing-decisions check's own summary is not total over the statuses it emits.

## Premise verdict

Confirmed on both fronts — the population really was 2, not the 1 the originating report claimed, and the D1 load-bearing claim was **read from source rather than assumed**, then reproduced by running the pre-fix filter directly.

## Gaps carried out of this landing

**11 total — 2 high, 3 medium, 6 low.** High: G2, G3.

- **Both high gaps are the same shape: a guard that cannot fire in the state it exists to judge.** M4 skips on a resolved-empty diff it has evidence for; the routing-decisions summary silently drops `inconclusive` checks to zero.
- ⛔ **G3 is the identical defect this same run FIXED in the sibling file and left unfixed in the file it was editing.**
- **G11 found a FOURTH private copy** of canonical-verify step-id prefix knowledge that the report's own residue section missed.

## Inconsistencies found, and what was verified

- Report's D5 claimed "25 test functions … re-derived against the delivered tree" | verified with a `def test_` count and `pytest --collect-only` at both the delivering commit and HEAD | **verdict: 31** — correct at verification round 4, never re-derived after the review round added six more. **The report's own residue section warns readers to re-derive any count in it; this is the count that check would have caught.**

## Residue

Five items declared open: the bounded `*Spec.java` exonerating survivor (inert here); a second git-ignored-blanket-premise site; oracle consolidation (deliberately out of scope); the four private prefix copies; and the delivered head never fully re-reviewed after the review-driven fix round.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-019 --status shipped`
- [x] row `pr` stamped `1288` — `orchestrator queue --set-row PLAN-CIS-019 --field pr --value 1288`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-019 --field landing --value landings/PLAN-CIS-019.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G2/G3 route to **PLAN-CIS-051** (`530`). The four-copy consolidation routes to **PLAN-CIS-049** (`510`).
