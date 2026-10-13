# Landing Analysis: PLAN-LB-33 — Leaf test scope and the main executor

epic: live-blockers
workstream: WS-02
pr: #1745 (https://github.com/cuioss/plan-marshall/pull/1745)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-33.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-33-leaf-test-scope-and-executor-008.md` (kind `landing`,
`landing-check` `complete: true`; surface delta `unmeasured`). Checked against:

- `ci pr queue-state --pr-number 1745`: `pr_state: merged`,
  `merge_commit_sha: 370f4237981c128d0d030c13141b65ba545c1ca2`, merge-group run `success`
  (after one re-enqueue; the first run failed on an unrelated flaky test).
- The merge as it fast-forwarded into the ledger worktree: 65 files, 6045 insertions, 997
  deletions (together with #1749, a two-file pm-dev-java doc change).
- A read-only review of commit 370f42379 against the spec by a delegated agent that ran nothing.
- `scope_creep_check.py` read here for the declared-set source (lines 341-351).

Not read by that review: full diffs of the freshness scripts, `pre-push-quality-gate.md`,
manage-tasks `SKILL.md`, the manage-architecture docs, most new test bodies, the rewired
executor tests.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 test trees outside bundles are targets | shipped, with a deviation | `_test_scope_targets.py` `resolve_registered_targets` names top-level `test/` trees; `_test_scope_divergence.py:489-498` still forces divergence for them and never recommends them, so a change under `test/sync-harnesses/` still runs whole-tree |
| 2 source mapping outside bundles | shipped, with a deviation | `SOURCE_TO_TEST_TARGET` maps `marketplace/targets/` (`_test_scope_divergence.py:116`); a mapped path is named only, `divergence_possible` stays true — still whole-tree. The PLAN-LB-29 case that motivated the plan is not narrowed |
| 3 narrow units | shipped | `narrow_units`, `narrow_units_unresolved`, `narrow_unit_module`; offered only for a footprint in exactly one bundle |
| 4 unmeasured narrow tier | shipped, small deviation | `architecture resolve --narrow-unit`; `bound_source` measured / module_bound / narrow_default; a timed-out run reports its own timeout source |
| 5 step documents | shipped | `execute-task/SKILL.md` Step 5(b), `phase-5-execute/SKILL.md:224`; doc-contract test |
| 6 gates not loosened | shipped | `test_pre_commit_verify_freshness_narrow_unit_control.py`; coverage table in the PR body |
| 7 cross-checkout refusal | shipped | `generate_executor.py` `cross_checkout_refusal` from `cmd_generate`; main's executor stays byte-identical |
| 8 bootstrap recovery | shipped | template walks versioned and flat cache layouts and the checkout's sources; template format 4 → 5, so every existing executor reads stale until regenerated |
| 9 empty argument value | shipped | `_drop_stray_empty_args` keeps `""` after an option |
| 10 plugin-doctor step document | shipped | symlink wording gone; runs with `{worktree_path}` as working directory |
| 11-12 (added at execute by the operator) scope-creep guard | shipped, outside the spec | finding type `triage` with rule `scope_creep_warning`; no re-filing of an accepted residual; base is merge-base(HEAD, `origin/{base_branch}`); threshold flag → `plan.phase-5-execute.scope_creep_threshold` → 5 with `threshold_source`; `plan_creation_sha` capture removed from manage-references |

Realized surface against the declared one: outside the declaration — `scope_creep_check.py`
and four scope-creep tests, `phase-5-execute/SKILL.md` Step 6.5, manage-references
`_references_core.py`/`_references_crud.py`, prose in `branch-cleanup.md`,
`automatic-review/SKILL.md`, `review_completeness.py`, manage-architecture docs and parser,
`marshal-json-reference.md`. Declared, not touched: `build.py`, `canonical_verify.md`,
manage-references `SKILL.md`, `test_generate_executor_template_bootstrap.py`.

## What the plan achieved against its objective

- **Executor half: met.** The cross-checkout refusal and the bootstrap recovery sit on the live
  path.
- **Test-scope half: partly met.** Narrow runs happen only for a single-bundle footprint. The
  targets and harness trees, and every multi-module footprint, still hand back a whole-tree run.
  The path is prose-driven: no script calls `--narrow-unit`.

## Metrics and Anomalies

- Tokens: 12,123,381. Wall time 128,833 s (about 36 hours).
- **Fail-open introduced by D9:** `resolve-test-scope --changed-paths ""` now reads as an empty
  footprint (`divergence_possible: false`); before D9 the executor stripped `""` and argparse
  failed loudly. An empty `{changed_paths}` in Step 5(b) means no pytest runs.
- Empty `--narrow-unit ""` falls back to the module-wide resolve; `scope_creep_threshold` is
  not registered in manage-config defaults (both advisory, both real).
- CodeRabbit's review of the final head was refused on quota; the operator merged without it.
- Flaky test `test_decision_rules_early.py::...::test_falls_through_when_task_queue_in_progress`
  (FileNotFoundError on a temp-file rename in a shared scratch dir), unfixed.
- Dispatch-boundary rows stop hours before the last dispatches and are all keyless.
- A CodeRabbit false positive filed `accepted` instead of `rejected` — second time in a row.

## Collisions with plans in flight

- PLAN-LB-27 (staged): deliverables 1, 2 and 4 (scope-creep type, measured base, threshold
  source) are done by D11-D12. Deliverable 3 is not: `_collect_declared_files` still globs
  `TASK-*.json` in the plan directory (`scope_creep_check.py:346`). Re-scoped in the spec.
- PLAN-LB-26 (staged) declares `scope_creep_check.py` and `test_scope_creep_check.py`; its
  re-ground must read the new guard.
- PLAN-LB-25 (running) declares `branch-cleanup.md` and `automatic-review` is near it; the
  changes there are prose only.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` 1745; `landing`; `plan_marshall_plan_id`
  lb-33-leaf-test-scope-and-executor
- [x] PLAN-LB-27 re-scoped in place
- [x] epic.md queue annotation, Open Defects, Watches updated
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- Narrow the non-bundle test trees for real (the PLAN-LB-29 case).
- Close the `--changed-paths ""` fail-open.
- Existing executors read stale after the template bump: regenerate on each machine.
