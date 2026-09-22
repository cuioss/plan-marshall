# Landing Analysis: PLAN-TRUTH-088 — metrics-ledger-readers-and-timestamp-provenance

epic: truthful-signals
workstream: WS-01
pr: 1342 (https://github.com/cuioss/plan-marshall/pull/1342), merged as `91bbe7470`

> Landing record for one shipped plan. Every material claim in the operator paste and in the
> plan's own landing message was treated as a lead and corroborated first-party.

## Deliverable Fidelity vs Spec

Spec declares nine (D1–D9); the landing reports 9/9. The counts agree — but **D1's content
narrowed from three populations to two**, which the paste states plainly ("the two surviving
scoping populations") and which needed checking, because the spec's own D1 mandates marking the
plan **partial** if a population cannot be derived.

**Verdict: shipped-modified with a recorded rationale, not a silent drop.** The outline retires
**D1(c)** — the `--plan-id`-declaring script census — as *orphaned*: "Its only consumer was D8(d).
With that deliverable moot, the derivation has no reader; deriving it anyway would produce a
population nothing consumes." D8(d) was itself dropped under the request's RULING 1 (a run report is
a dated record, so a deliverable whose target is a run report is dropped at outline; no live surface
restates the claim). That is the spec's discipline followed, not evaded — the plan declined to derive
a population no reader consumes rather than deriving one to satisfy a count.

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 — derive the scoping populations, or stop the dependents | shipped-modified | 2 of 3 derived; D1(c) retired as orphaned with its consumer named in the outline |
| D2 — display-timezone guards observe the defect they name | shipped-as-specified | red-first required and satisfied; closes 150/G1 + 150/G5, both vacuous-guard |
| D3 — `audit.py` stops reading an absence or gate-exclusion as a measurement | shipped-as-specified | the plan's headline surface |
| D4 — every build-status surface accounts for the undetermined build | shipped-as-specified | |
| D5 — the ledger build-status consumer set and its three contracts | shipped-as-specified | rests on D1(b), which WAS derived |
| D6 — the dispatch-boundary contract stops describing a reader that does not exist | shipped-as-specified | |
| D7 — the two dispatch-boundary readers resolve columns the same way | shipped-as-specified | |
| D8 — population, inventory and documentation corrections | shipped-modified | D8(d) moot under RULING 1; the rest shipped |
| D9 — re-base the `CHECK_ERA` boundary for the checks this plan changes | shipped-as-specified | `era-stamp-fill` resolved PR-PENDING → #1342 at 2 sites |

⭐ **Second count-mismatch this session that resolved to a scoping artifact rather than a defect**
(the first was `-096`'s 9-vs-7). Both were traceable in the outline. Standing practice: a
deliverable-count mismatch between the paste and the spec is a numbering-or-scoping artifact until
the outline says otherwise — read the outline before filing.

## Metrics and Anomalies

- Tokens: **7,003,398**; **billing-weighted 94,666,978**; worked 26,841 s (7h27m) against
  126,004 s wall. Cost ≈ **3.3× the error anchor**.
- ⭐ **The self-review loop cost ~1.4M across 7 rounds and found 9 real defects with zero false
  positives.** That is the first measured instance where the settle band's cost is defensible on
  yield, and it **cuts against** a naive reading of R22: the band's cost is not automatically waste.
  R22's claim was about the *re-fire amplification*, not about self-review's yield — both can hold,
  and `-097` DB must not use this landing as licence to collapse the band.
- ⛔ **Nine findings ship unfixed** (recorded, out of footprint). Three are this epic's own theme and
  two of them corroborate existing entries: the routed build reporting `tests_run: 0` on every green
  run (R6 / `-087` DA, still RUNNING); **the circular CI skip that verified nothing for most of this
  PR's life** (independent confirmation of the R95 `D-CI` family); and `scope_creep_check` rendering
  an unmeasured comparison as a clean zero (`-104` family).

## Routing and Merge Behavior

- Review: `automatic-review` reported 0 comments at final head; `review-retrospective` measured 2 of
  3 reviewers, **sourcery refused**. A refusing reviewer is `review-apparatus`'s standing subject.
- CI/merge: green, merged **via the merge queue** as `91bbe7470`; sync-baseline rebased over 5
  upstream commits and the branch was **force-pushed** to `dd55c6f8e`.
- ⛔ **`branch-cleanup` did NOT complete: the worktree was retained.** `git worktree remove` timed out
  twice on its fixed 60 s budget — `.plan/temp/pytest-basetemp` is large enough that listing it alone
  is 11.3 MB, much of it nested git repos from fixtures. Deleting the scratch was declined and
  `git clean -ffdx` is improvisation the step forbids, so the step stopped rather than improvise.
  **That was the correct call.** Verified first-party: the worktree is still present at `dd55c6f8e`
  holding `feature/metrics-ledger-readers-and-timestamp-provenance`.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr`, `landing`, `plan_marshall_plan_id` all stamped
- [x] `-015` recorded `superseded` **through `inbox supersede`** — the paste declared it superseded in
      prose only, so the envelope still read `live`
- [x] 16 inbox messages drained (14 candidate-lessons + 2 landings)
- [x] epic.md narrative reconciled; both GENERATED blocks regenerated
- [x] resume_anchor updated

## Follow-Ups

| Item | Disposition |
|---|---|
| A stale served skill body is indistinguishable from a live contract (msg 001) | folded → PLAN-TRUTH-111 + Watch |
| Record a step's partial failure in structured facts (msg 002) | folded → PLAN-TRUTH-106 |
| Derive declared files from structured deliverables (msg 003) | folded → PLAN-TRUTH-098 |
| Validate a footprint ledger by symmetric difference, never cardinality (msg 004) | folded → PLAN-TRUTH-098 |
| Two token ledgers disagree by 2.09× over one declared population (msg 005) | forwarded → `code-intelligence-substrate` |
| Build oracle attributes every build to NO_PLAN and double-records (msg 006) | folded → PLAN-TRUTH-105 |
| Wire the per-dispatch context-load fields (msg 007) | folded → PLAN-TRUTH-097 F2 — **recurrence** |
| A detector reporting non-ambiguity must have measured it (msg 008) | folded → PLAN-TRUTH-104 |
| Prefer stderr over stdout when `exit_code` is 2 (msg 009) | folded → PLAN-TRUTH-111 |
| Emit `[ARTIFACT]` from the task-completion path (msg 010) | folded → PLAN-TRUTH-089 DC — **recurrence, now with a remedy** |
| `mark-step-done` accepts a `head_at_completion` SHA it never resolves (msg 011) | folded → PLAN-TRUTH-097 |
| Convergent remedy for an over-claiming sentence is deletion (msg 012) | folded → PLAN-TRUTH-108 |
| A defect class closed by instance count left a third copy (msg 013) | folded → PLAN-TRUTH-108 |
| Verify a review finding before ACTING on it (msg 014) | forwarded → `review-apparatus` |
| Duplicate landing from a 0.1.1240-era body (msg 015) | retired by successor `-016` |
