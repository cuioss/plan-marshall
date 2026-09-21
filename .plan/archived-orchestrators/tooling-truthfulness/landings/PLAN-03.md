# Landing Analysis: PLAN-03 — Build-path evidence

epic: tooling-truthfulness
workstream: WS-03
pr: 1469 (https://github.com/cuioss/plan-marshall/pull/1469, merged as ca84fe7e7a)

> Landing record for one shipped plan. Claims verified against ground truth
> (PR state via CI abstraction, HEAD, merged code, worktree list, working tree,
> archived plan artifacts) — the paste was a lead, never a fact.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — gate-route ledger record (`in_process` + daemon `kind=build` rows) | shipped-as-specified | `_build_execute_factory.py:434` defines `_append_gate_build_row`, called at `:1129` and `:1202`; PR #1469 diff adds seam + red-first tests in `test_pyproject_execute.py`; daemon route covered by matched control |
| D2 — self-heal depth re-derived, pinned | shipped-as-specified | `test_generate_executor.py:3014` `test_surface_derivation_depth_covers_deepest_executor_verb_chain` asserts `max_depth == 6` with deepest observed chain 4 (margin 2, fail-closed cap); recorded as already-fixed positive account per spec |

Corroboration: PR state `merged`, `merge_commit_sha ca84fe7e7a…` == main HEAD (`git log`);
`git status` clean on main (behind `origin/main` by 2 unrelated dependabot commits
#1470/#1471 — noted, not defected); plan worktree removed (`git worktree list` shows
main + PLAN-04 worktree + unrelated detached session); archived plan present at
`.plan/local/archived-plans/2026-09-12-build-path-evidence/`. No drops, no unplanned additions.

## Metrics and Anomalies

- Tokens: 0 (untracked for this run — recorded as absent, not as zero)
- Duration: `total_wall_seconds=19044.0` (~5h17m) per landing-facts
- Review: coderabbit 6 actionable (4 fixed, 2 taken_into_account with design justification);
  sourcery 3 actionable (1 real bug-risk fixed via TASK-5, 2 taken_into_account); 2 ci_timeout
  findings taken_into_account (transient, verify still IN_PROGRESS) — per archived triage.jsonl
- Anomalies: `emit-landing:n/a, archive-plan:n/a` in landing-facts steps while both observably
  happened (inbox message exists; archive dir exists) — `n/a` at optional step keys, recorded
  as imprecise rather than blocking; landing-check reports `complete: true`

## Routing and Merge Behavior

- Review: 5 pr-comment findings remediated via fix tasks TASK-005..TASK-008 (slipped-then-caught:
  ledger outcome missing tests_run/tests_population, status vocabulary mirror, payload field loss,
  daemon-child double-append) — per inbox lesson -001
- CI/merge: queue-merged; no rebase conflicts and no re-verify signals against
  concurrently-running PLAN-04 (disjoint surfaces held — no collision to record)

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-03 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-03 --field pr --value 1469`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-03 --field landing --value landings/PLAN-03.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-03 --field plan_marshall_plan_id --value build-path-evidence`
- [x] epic.md queue reconciled from status.json
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] inbox drained: 4 messages (1 landing reconciled, 1 candidate-lesson promoted,
  1 folded as recurrence into corpus `2026-09-11-19-001`, 1 discarded as recurrence), all archived

## Follow-Ups

- PLAN-03's `corpus_spec` rows remain true of the declaration but no longer gate concurrency —
  landed plans leave the live set
- `origin/main` 2 ahead with unrelated dependabot commits (#1470 types-pyyaml, #1471 ruff) —
  no epic action; next baseline sync absorbs them
