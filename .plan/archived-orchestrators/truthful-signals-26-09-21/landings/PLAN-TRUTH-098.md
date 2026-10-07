# Landing analysis — PLAN-TRUTH-098

**Plan:** `plan-footprint-is-unknowable-to-its-own-graders` · **WS-01**
**PR:** [#1359](https://github.com/cuioss/plan-marshall/pull/1359) · **merged** as `841f90939711def1857178cbb041e4756385c4fb`
**Analyzed:** 2026-08-27, mode `paste` + `inbox` landing message `-011` (`landing-check: complete: true`)

## Corroboration

⭐ **Every load-bearing claim was checked first-party before this record was written.**

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1359 merged | **corroborated** | `ci pr view --pr-number 1359` → `state: merged` |
| Merge commit `841f9093` on main | **corroborated** | `git merge-base --is-ancestor 841f9093… origin/main` → true |
| Landing payload complete | **corroborated** | `inbox landing-check` → `complete: true`, `missing_keys[0]` |
| "main at 841f9093" | ⚠ **true when written, already superseded** | `origin/main` is now `26645688b`; #1356 and #1360 landed after. Not a defect — a landing describes a merge, not a current HEAD. |

## Deliverable fidelity

7 of 7 shipped. 22 of 22 finalize steps `done`, except two structurally-unknowable ones (below).

⭐⭐ **The epic's goal was met and can be stated precisely: this is the first run on this repository
with a resolvable post-merge footprint.** That is the thing `-098` existed to produce.

⛔ **But the tier that answered is NOT the tier this plan added.** Tier 2 (`realized_capture`) answered,
because `branch-cleanup` wrote the capture before removing the worktree, so the fall-through never
reached D1's new tier 4 (`pr_landing`). `references.merge_commit_sha` is populated, which is exactly the
condition under which tier 4 is not consulted. ⇒ **D1's tier is shipped and controlled-tested but
UNEXERCISED IN THE WILD.** The plan says so itself rather than letting the landing read as
self-validation — that is the honest form and is why this record repeats it.

⭐ **Tier 3 independently reproduced tier 2 exactly** — same 33 paths, symmetric difference 0
(`git diff --name-only 841f9093^1 841f9093`). ⚠ **Done by hand; no aspect or script performs that
cross-check.** Mechanisable, not mechanised.

## The measurement that mattered — Arm 2, and the matched-length trap fired for real

**33 declared vs 33 realized, equal cardinality, NON-IDENTICAL membership.** `collect-fragments.py` was
recorded and never changed; `logging-gap-analysis.md` was changed and never recorded. ⛔ **A count
comparison reports perfect agreement over a set that disagrees** — precisely the trap the epic recorded
twice before (13-vs-15, 52-vs-54, where the errors nearly cancelled) and the reason D4's verb compares by
symmetric difference rather than by size. Recall **97% (32/33)** against the spec's 81.25% baseline;
`read_intent_excluded: 4` shows D3's partition working; D6's aggregate correctly did not fire (all four
roster members resolved) — **its matched negative control passing.**

## ⛔ Two live defects shipped into main — neither fixed by #1359

1. **Documented capture commands name a file no step creates.** `references/routing-decision-verification.md`
   (aspect 13) and the newly-shipped `references/outline-vs-shipped.md` (aspect 15) both instruct capture
   into `work/footprint.txt`. **Run verbatim, both exit 1**; they produced fragments only because the
   retrospective agent deviated from the documented command. ⭐⭐ **The new file copied its broken
   sibling's reference — a defect propagated by imitation into the very deliverable meant to close the
   gap.**
2. **"Phase Dispatch Boundaries" is a permanently dead report section.** `compile-report.py` reads a
   top-level `dispatch_boundaries` key; `analyze-logs.py` nests it inside its log-analysis fragment; no
   aspect registers it. **The omission classifies as benign (`sections_omitted`), so the loud half never
   fires.** Test fixtures hand-construct the key ⇒ **a green suite proving a contract production does not
   satisfy.**

## Producer gaps

- **`record-metrics` recorded no typed facts.** Totals ride `display_detail` prose; `phase_steps` carries
  no `facts` sub-dict, so `total_tokens` / `total_wall_seconds` are not readable from where the landing
  spec points. The landing read them from the metrics store instead. ⭐ **Named rather than degraded to
  `unknown`** — the figures are true, the routing is not mechanised.
- **Billing-weighted total has no schema key.** 185.4M is not carried as a required fact.
- **Two `steps` elements are `unknown` BY CONSTRUCTION.** `emit-landing` cannot observe its own terminal
  outcome and `archive-plan` (order 1100) has not run when the landing is written. ⇒ **`steps` can never
  be complete for the last two composed slots.** Structural, not a producer defect — and writing `done`
  there would fabricate an unobserved state.

## Reconciliation actions

- Queue row `PLAN-TRUTH-098` → `shipped`; `pr` = 1359; `landing` = this file.
- Defects 1 and 2 recorded as epic Open Defects (D-098-a, D-098-b).
- Review-participation and cost observations carried to the epic; routed per the three-way rule.
- 10 candidate-lesson messages (`-001`…`-010`) drained separately.

## Parallelization

⚠ **`-098` and `PLAN-TRUTH-114` ran concurrently under the operator's R=2 override, across a declared
surface the gate could not see** (`-098` declared globs; `-114` edits a file inside one). **No collision
materialised** — no rebase conflict and no re-verify signal is reported in this landing. ⇒ Recorded as a
**successful** pairing across the known blind spot, which is evidence for `-113` but NOT a licence to
treat glob-silence as disjointness.
