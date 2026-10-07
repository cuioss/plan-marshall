# Landing Analysis: PLAN-12 — Tool defect triage

epic: process-compliance
workstream: WS-05
pr: #1654 (https://github.com/cuioss/plan-marshall/pull/1654) — replaced #1653 (closed, CodeRabbit close-and-reopen recovery)

> Landing record for one shipped plan. Written by the `analyze` verb (inbox drain 2026-09-29) after
> verifying the `kind: landing` message `plan-12-tool-triage-013` against ground truth:
> - PR #1654: `state: merged`, `merge_commit_sha: 26f864b1ee…`, via the CI abstraction;
> - `26f864b` is on `origin/main`;
> - its file list: 50 files, +2394 / −407.
>
> `inbox landing-check`: `complete: true`. ⚠ The facts block's `pr=#1653` is a stale step fact (see the
> Residue section). Ground truth is **#1654**, and #1654 is what this record and the queue row carry.

## Deliverable Fidelity vs Spec

Facts block: `deliverables_total=6`, `deliverables_done=6`.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 `manage-status transition` silent-failure triage | shipped-as-specified | `manage-status/scripts/_cmd_lifecycle.py`; `test_transition_phases_shape_refusal.py`, `test_transition_refusal_halt_call_sites.py`; halt call sites across planning / execution / phase SKILLs |
| D2 retrospective fragment-pipeline triage | shipped-as-specified | `plan-retrospective/scripts/collect-fragments.py`, `compile-report.py`, `check-manifest-consistency.py`; 7 new or changed `plan-retrospective` tests incl. `test_fragment_pipeline_structured_skip.py` |
| D3 `merge_lock --hold-start` type mismatch | shipped-as-specified | `manage-locks/SKILL.md`, `phase-6-finalize/standards/branch-cleanup*.md`; `test_merge_lock_budget_reclaim.py` |
| D4 argparse router-scoping recurrence | shipped-as-specified | `tools-input-validation/scripts/input_validation.py`; `test_router_flag_placement.py`; `tools-integration-ci/standards/pr-review-operations.md` |
| D5 regression tests for all four | shipped-as-specified | as listed per deliverable above |

## Metrics and Anomalies

- Tokens: 18,462,076 (facts block). The candidate lesson `-010` cites 19.85M, with 6-finalize at 59%
  (11.7M).
- Duration: 170,910 s wall (~47 h).
- Anomalies:
  - `pre-submission-self-review` fired 13 times with 10 loop-backs. It ran 12 finalize loop-back
    iterations, 7 beyond `max_iterations=5`, each authorized by the operator, and was closed by
    `may_close=operator_override`. That is the non-convergence PLAN-20 exists to fix, and it
    recurred right after PLAN-13's run.
  - Three `failed → retry → done` steps (sync-baseline, push, automatic-review) needed an undocumented
    `mark-step-done --force`.
  - The push halted on `build_scope_narrow` after all four pre-push arms were green.
  - The automatic-review rate-window recovery could not complete inside its leaf.
  - The scope-creep guard crashed on every task.
- The PR's own review found no defect that survived: post-merge triage moved `63a935` (cuioss-review-bot)
  from `taken_into_account` to `rejected`.

## Routing and Merge Behavior

- Review: CodeRabbit gave no reaction, so the unattended protocol closed #1653 and reopened it as
  #1654. Sourcery hit `hard_quota` (optional).
- Merge: main was merged into the branch (`7c2800c85`) to resolve a path-rename conflict with #1651 in
  `plan-retrospective/SKILL.md`. After that, CI, one review round and the pre-merge barrier re-ran
  clean. It merged through the merge queue as `26f864b`, with `cleanup_owed=false`.
- Collisions: that conflict is a real overlap between PLAN-12 and PLAN-13 (`plan-retrospective/SKILL.md`).
  Neither spec declared the file; both touched it (PLAN-13 through its stale-path sweep, PLAN-12
  through D2). This is recorded for pairing, and no spec correction is owed, because both plans have
  shipped.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` → `1654` (not the stale `#1653` from the facts block)
- [x] row `landing` → `landings/PLAN-12.md`
- [x] row `plan_marshall_plan_id` → `plan-12-tool-triage`
- [x] epic.md narrative reconciled
- [x] 22 further messages from the run (4 candidate lessons, 18 findings) dispositioned in the same drain
- [x] resume anchor updated
