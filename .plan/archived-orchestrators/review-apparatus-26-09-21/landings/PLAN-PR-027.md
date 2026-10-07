# Landing Analysis: PLAN-PR-027 — A failing `ci` call reports success

epic: review-apparatus
workstream: WS-04
pr: #1356 (merged, `26645688b`)

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| Merged as #1356, `26645688` | **corroborated** | `26645688b` at the tip of `origin/main` |
| 41 files, +4043/−450 | **corroborated** | `git show --stat 26645688` |
| 6/6 deliverables, 23/23 steps | **corroborated** | landing message `-011` |
| Landing message complete | ✅ **corroborated** | `landing-check` → `complete: true`, 0 missing |
| Pin gate | ⛔ **CONTRADICTED** | executor `0.1.1561` vs registry `installPath 0.1.1556` — 5 versions |

⭐ **The #1349 landing-facts regression did NOT recur.** This landing carries a complete facts block, so
that defect was run-specific rather than a permanent producer break — narrowing what PLAN-PR-028 D2's
producer-side assertion has to catch (an intermittent omission, not a removed feature).

## Deliverable Fidelity vs Spec

All six shipped. ⭐ **Both 2026-08-25 pre-emit amendments were exercised on their first run and both
held:**

- **Amendment 8, first half** — D2's test clause, widened from `create-pr.md` alone to all three
  widened docs. Shipped as deliverable 2 (the exit-0 non-success disposition) with the guards made
  population-derived (deliverable 5).
- **Amendment 8, second half** — D4's `routing_note` carrying all three of `060 G8`'s fields rather
  than one. Shipped inside deliverable 4/5.
- ✅ **`030 G7`'s ownership settlement held**: no collision with PLAN-PR-025 D3 materialised.

## ⛔ The finding that matters most — a vacuous green in this epic's own component

Three consecutive self-review rounds each found **one** member of the same class and reported
`cohort_size: 1` — **a property of the surfacer's candidate list published as a property of the tree.**
One directed class sweep then found **four**, including `verification-feedback.md`'s pr-state producer
collapsing every `ci pr view` non-success into *"no PR exists"* and returning a clean
*"nothing to triage"*.

⇒ This is the epic's own archetype, inside the instrument the epic uses to police it. Folded onto
PLAN-PR-030, which now owns the self-review cluster.

## ⛔ One live defect filed, NOT fixed

**`5ec6d3`** — `github_re_review`'s `head_sha_verified` misses a SHA embedded in a **commit URL**,
manufacturing a false review-decline that **would block a merge on a bot that did review**. Overridden
this run on the branch's own stated precondition, with the reason recorded. ⇒ Folded onto
**PLAN-PR-025**, which owns `github_re_review.py`.

## Routing and Merge Behavior

- ⛔ **Reviewer coverage was one bot deep, again.** CodeRabbit produced **all 22 comments** while at its
  1/hour ceiling; **pr-agent — the only required bot — was empty on every HEAD**; Sourcery refused
  structurally on diff size and read **none** of a 4493-line diff.
- ⭐ **12 of 19 bot findings were one archetype the in-run self-review had already passed.**
- **A late upstream conflict needed an operator call.** #1359 landed mid-finalize on the same four
  files; the PR went `mergeable: conflicting`; 33 commits replayed, 0 skipped, all four conflicts
  resolved additively. ⚠ **Contract gap**: the merge-queue path documents *skipping* the rebase, but
  the queue cannot accept a conflicting PR — so a conflict-resolving rebase is a **precondition the
  routing section does not name**. Recorded as an Open Defect.

## Metrics and Anomalies

- **11.4M tokens against a 2.0M anchor** — 5.7×. 3 loop-backs, 12 self-review firings, 33h22m.
- ⛔ **2.19M (19% of the run, 34% of finalize spend) went to 8 error-terminated dispatches that
  returned nothing**, four of them clustered in a **14-second window** before a session restart.
  Promoted as a lesson; not this epic's surface.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr`, `landing`, `plan_marshall_plan_id` stamped
- [x] Open Defect: merge-queue routing omits the conflict-rebase precondition
- [x] Open Defect: pin gate re-opened (5 versions)
- [x] inbox drained (12); blocks regenerated

## Follow-Ups

- **`5ec6d3` → PLAN-PR-025** (live, unfixed, merge-blocking class).
- **cohort_size + the 12-of-19 archetype → PLAN-PR-030.**
- **Reviewer coverage n=4 → PLAN-PR-026** (this PR plus #1340, #1349, #1359).
- ✅ **Correction relayed by the run**: the earlier "body-less lesson stubs" claim is **refuted** by the
  retrospective's own census — 6 active lessons, all with full bodies.
