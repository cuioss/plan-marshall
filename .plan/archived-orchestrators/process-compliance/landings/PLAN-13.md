# Landing Analysis: PLAN-13 — Finalize-mechanism structural defects

epic: process-compliance
workstream: WS-07
pr: #1651 (https://github.com/cuioss/plan-marshall/pull/1651)

> Landing record for one shipped plan. Written by the `analyze` verb (inbox drain
> 2026-09-28) after verifying the `kind: landing` message
> `plan-13-finalize-mechanism-defects-007` against ground truth: PR state via the CI
> abstraction (`state: merged`, `merge_commit_sha: c56710b36f01…`), the merge commit on
> `origin/main`, and its file list. `inbox landing-check`: `complete: true`, no missing keys.

## Deliverable Fidelity vs Spec

Facts block: `deliverables_total=5`, `deliverables_done=5`. Verdicts below are from the
merge commit's file list (65 files, +1191 / −255), not from the message.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 emit-landing guard ordered before the irreversible archive; epic membership persisted | shipped-as-specified | `phase-6-finalize/standards/emit-landing.md`, `archive-plan.md`, `SKILL.md`; `test_finalize_orchestration_routing_core.py` |
| D2 archive path: doc equals resolver | shipped-as-specified | `archive-plan.md`; new `test/plan-marshall/manage-status/test_archive_path_doc_resolver_parity.py` |
| D3 forked finalize cwd never inside the tree it destroys | shipped-as-specified | new `test/plan-marshall/phase-6-finalize/test_forked_finalize_branch_cleanup_cwd.py`; `dispatch-inline-split.md` |
| D4 `pr_title` re-derived / flagged stale after scope removal | shipped-as-specified | `phase-6-finalize/workflow/create-pr.md`; `test_finalize_bug_regressions.py` |
| D5 session-binding sweep keeps the reserved `by-cwd` index | shipped-as-specified | `platform-runtime/scripts/session_binding.py`; `test_session_binding.py` |
| (unplanned) marketplace-wide stale `.plan/plans/` → `.plan/local/plans/` sweep, ~40 files | added-unplanned, operator-approved scope deviation | recorded in the PR body's "Scope Deviation Accepted"; `.plan/plans/` now appears only in the plugin-doctor rule that detects it (4 files, all legitimate) |

## Metrics and Anomalies

- Tokens: 11,307,577 total (facts block).
- Duration: 93,549 s wall (~26 h, facts block).
- Anomalies:
  - `pre-submission-self-review` spent all 5 loop-back iterations on stale-path drift (every fix moved the
    contradiction one contract hop outward). The operator waived the closing round, and the step was forced
    `done` at `3720898`.
  - The shared loop-back ceiling was already spent when two CodeRabbit fixes (TASK-12/13) arrived. The
    operator overrode it once.
  - The head-dependent re-fires of lessons-housekeeping, simplify and plugin-doctor after the final fix
    commits were waived. plugin-doctor gated only the 8 declared-footprint skills, not the ~12 the sweep
    touched.
  - Six orchestrator-tier module-test runs and five verification-feedback dispatches all re-triaged one
    known failure (inbox `-004` items 1–2).
- All 20 finalize steps are reported `done`, and `record-metrics.any_phase_missing_end_time=false`.

## Routing and Merge Behavior

- Review:
  - CodeRabbit produced 2 fix tasks.
  - cuioss-review-bot reviewed `3720898`, not the two fix commits, so it was stale at merge.
  - Sourcery (optional) refused because the diff exceeds its 150,000-char cap.
  - The merge ran under a `barrier-ask-override` at `6f8e7c0`.
- CI/merge: merged through the merge queue (`step.branch-cleanup.merge_mechanism=merge_queue`) as
  `c56710b`. `cleanup_owed=false`.
- Collisions: none observed. Surface widening from the sweep: realized 65 files against 7 declared
  entries. The sweep ran outside PLAN-13's declared surface under an operator-approved deviation, so this
  is not a declaration error. `inbox landing-check` `surface_delta` is `unmeasured` because no paths were
  supplied.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-13 --status shipped`
- [x] row `pr` stamped — `queue --set-row PLAN-13 --field pr --value 1651`
- [x] row `landing` stamped — `queue --set-row PLAN-13 --field landing --value landings/PLAN-13.md`
- [x] row `plan_marshall_plan_id` stamped — `queue --set-row PLAN-13 --field plan_marshall_plan_id --value plan-13-finalize-mechanism-defects`
- [x] epic.md narrative reconciled (queue annotation for PLAN-13; the "landing will be skipped" Watch retired, because the landing message arrived through the detector)
- [x] process findings `-004` (22 items) and candidate lessons `-005` / `-006` dispositioned in the same drain (see decision log)
- [x] resume anchor updated
