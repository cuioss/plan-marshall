# Landing: PLAN-10 — end-phase-replace-not-accumulate

plan: PLAN-10
workstream: WS-04
plan_marshall_plan_id: end-phase-replace-not-accumulate
pr: 1059
merge_commit: dfe7fde0b
landed: 2026-07-29

## What landed

`fix(manage-metrics): accumulate phase attribution on loop-back`. A loop-back re-ran `end-phase`,
which **replaced** rather than accumulated a phase's token attribution. Three deliverables:

1. Accumulate-on-re-entry write path, plus a `metrics.md` re-entry annotation and contract docs.
2. An end-to-end loop-back re-entry regression test.
3. Archived-corpus damage assessment.

⭐ **The fix instrumented itself**: `end-phase` closed `6-finalize` with `close_count: 1` and `generate`
emitted `re_entered_phases[0]` — the new accounting is observable on the run that shipped it.

## Orchestrator corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1059 merged | **corroborated** | `origin/main` carries `dfe7fde0b fix(manage-metrics): accumulate phase attribution on loop-back (#1059)` |
| CI green before merge | **corroborated** | Checked directly while the PR was open: 12 checks, `overall_status: success` |
| No bot reviewed the final diff | **corroborated by the plan's own record**, and consistent with what this orchestrator observed on the sibling PRs the same day | `review_completeness` on the rebased HEAD: coderabbit `refused_awaitable`, pr-agent `absent`, sourcery `refused_hard` |
| Corpus damage assessment (2 of 27 archived plans affected) | **accepted as first-party measurement**, not re-derived | Reported at D3; the earlier ledger note already carried the same two named plans |

⛔ **A prior landing message for this plan was REFUSED at the previous drain.** Message
`end-phase-replace-not-accumulate-002.md` announced "PR #1059 — shipped" while #1059 was still open;
it was deliberately left un-archived and no queue transition was made. **That refusal was correct and
is now resolved by a real merge** — the message's substance is folded into this record and the message
is archived at this drain. The episode is retained as a standing Open Defect (a `kind=landing` message
can be written pre-merge; second occurrence across the two epics).

## Deliverable fidelity vs spec

Full fidelity on all three staged deliverables. ⭐ **The spec's implied fix was wrong and the deep lane
caught it**: `_resolve_token_field` returns either a per-close delta *or* an already-cumulative value,
so the blanket `+=` the spec implied would have introduced a **new double-counting bug**. Deliverable 3
also honoured the spec's explicit instruction to report the affected count separately from the number
of plans examined — the volume-read-as-coverage guard held.

## Gate record and honesty signals

- ⚠ **Two steps self-marked `[~~]` rather than `[OK]`** — `automatic-review` (proceeded unreviewed) and
  `branch-cleanup` (merge barrier overridden). Both recorded at WARNING as **operator authority, not
  earned review**. ⭐ This distinction being drawn *by the plan itself*, in its own report, is the
  behaviour the epic's whole theme argues for.
- ⭐ **A self-correction the orchestrator accepted and acted on**: the plan retracted its own
  dispatch-boundary under-reporting finding, identifying the missing rows as **its own omission of
  three `record-dispatch-boundary` calls to conserve context**, not a tool defect, and repaired the
  trail (9 rows now reconcile). ⛔ This orchestrator therefore did **not** record axis 1 of message 007
  as a defect. Only axis 2 (the producerless context-load columns) was folded forward.
- `pre-push-quality-gate`, `plugin-doctor` (30 rules), `pre-submission-self-review` (75 candidates),
  `ci-verify` at `acbdcecf3`: all green. `finalize-step-simplify` made 3 edits.
- ⛔ **`[BUDGET] error`: 3.4 M tokens / 5h38m for a `single_module` `bug_fix` — 2.4× the anchor**, with
  `6-finalize` alone at 1.43 M (42 %). Note the interaction with PLAN-01's landing: that run had **no**
  applicable anchor at all (`multi_module` has no row). Here the anchor existed and was breached. The
  two together are the evidence base for PLAN-CIS-008.

## Reconciliation actions

- `PLAN-10` transitioned `running` → `shipped`; row stamped `pr=1059`, `landing=landings/PLAN-10.md`,
  `plan_marshall_plan_id=end-phase-replace-not-accumulate`.
- The `manage-metrics` serialization class is released. ⚠ Cross-epic note: `truthful-signals` PLAN-96
  carried a deferral for `manage-metrics/scripts/manage-metrics.py` *while #1059 was open* — that
  constraint is now **lifted**, and they should be told at their next drain.
- Ten inbox messages drained (1 deferred landing now reconciled, 9 candidate-lessons).

## Signals this landing produced

Five of nine candidate-lessons are defects in **the instruments that grade plans**, not in the plan:

1. Retrospective footprint graded after `branch-cleanup` deleted the worktree — `recall 0%` where truth
   is 100% (declared 6, found 6 in `dfe7fde0b`). **Second independent instance in one day.** → PLAN-CIS-012.
2. `lessons-capture` dispatched but emitted no `[DISPATCH]`, so the detector concluded the opposite of
   the truth — a fabricated discipline violation. → PLAN-CIS-010.
3. The `shape_violation` check is vacuous (zero `effort resolve-target` entries across 17 dispatches),
   and two report sections have no producer at all. → PLAN-CIS-010.
4. A test fixture wrote into the **live plan's** `work.log`, and the leak detector reported `0` because
   it does not scan `work.log`. → PLAN-CIS-017.
5. `manage-metrics/SKILL.md` documents 6 of 11 `termination_cause` values while asserting the rest are
   rejected — and 7 of this plan's 10 boundary rows carry undocumented values. → staged as PLAN-CIS-009.
6. First entry into 5-execute logs `Re-entering`, so `RE_ENTRY_COVERAGE` mismatches systematically.
   → PLAN-CIS-010.
7. A 4.3 %-confidence `request_aspect` recorded as settled fact, and `scope_estimate` derived from the
   **epic pointer artifact** rather than any real target. → PLAN-CIS-015.

## Parallelization note

No collision. PLAN-10 ran concurrently with PLAN-01 on disjoint surfaces throughout and rebased cleanly
onto four upstream commits. Both concurrent pairings this epic has attempted were correct.
