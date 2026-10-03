# Landing Analysis: PLAN-10 — `land`: monitored, never-remove ledger landing

epic: orchestrator-refactor
workstream: WS-05
pr: #1690 (https://github.com/cuioss/plan-marshall/pull/1690)

> Landing record for one shipped plan. Lives at `landings/PLAN-10.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `orchestrator-land-verbs-009.md` (`kind: landing`, `landing-check` `complete: true`, no
missing key). Corroborated on 2026-10-03 against `ci pr view --pr-number 1690` (`state: merged`,
`merge_commit_sha: 7a0af07c5`), `git merge-base --is-ancestor` against fetched `origin/main`, and
`git show --stat 7a0af07c5` (43 files, +4946 / −104). The plan `orchestrator-land-verbs` is no longer in the
live plan store (archived).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — `land`: snapshot, commit, push, serialized | shipped-as-specified | `_orchestrator_land.py` (new, +777) with `land status` / `snapshot` / `bind` / `resync`, wired in `orchestrator.py` (+82); the lock reuses the shared lock core — a held-guard helper exposed from `manage-locks/scripts/_locks_core.py` (+131) and adopted by `_orchestrator_ledger.py`. Tests: `test_orchestrator_land_snapshot.py`, `test_locks_core.py`. |
| D2 — PR create-or-update, epic-native title/body | shipped-as-specified | Driven by the new `plan-orchestrator/workflow/land.md` (+253) over the `ci` primitives, per the PR description. Not exercised against a live PR (see Metrics). |
| D3 — monitor with an explicit post-enqueue settle loop | shipped-as-specified | New `ci pr wait-for-queue-settle` (`_github_pr.py` +367, `github_ops.py` +82), documented in `tools-integration-ci/standards/pr-operations.md` and `api-contract.md`. Tests: `test_pr_wait_for_queue_settle.py`. |
| D4 — resync without losing post-snapshot writes | shipped-as-specified | `land resync`, no blind `reset --hard` per the PR description. Tests: `test_orchestrator_land_resync.py`. |
| D5 — recoverable failure; `dequeued` distinct from `timeout` | shipped-as-specified, **HYPOTHESIS confirmed** | The spec's HYPOTHESIS that no `ci` read verb exposed queue membership held: the plan added `ci pr queue-state` (`test_pr_queue_state.py`). `dequeued` is a terminal outcome of the settle verb. Caveat: merge-group-run-to-PR matching assumes GitHub's `gh-readonly-queue/{base}/pr-{n}-{sha}` naming, unverified against a live queue — if wrong, an ejection reads `timeout`. |
| D6 — harden the PLAN-09 worktree | shipped-as-specified | (a) `orchestrator_worktree.py` refuses a registered `_orchestrator` worktree on another branch (`test_orchestrator_worktree_refusal.py`, `test_orchestrator_worktree_create.py`); (b) `git-workflow.py` (+21) reserved-key refusal on `worktree-remove` (`test_git_workflow_worktree_core.py`). |
| (unplanned) `plan.phase-5-execute.worktree_setup_commands` | added-unplanned, operator-accepted | Operator widened scope at TASK-1 (`(scope-deviation:accept)`): `prepare_execute.py` (+194) runs declared setup commands at phase-5 move-in and re-entry; `.plan/marshal.json` declares the target-tree generate command; documented in `data-model.md` and `marshal-json-reference.md`, defaulted in `_config_defaults.py`. Reason: a fresh plan worktree has no git-ignored `target/` tree, so `test_target_tree_foundational_skill_freshness` failed there. Never got an outline heading, so `deliverables_total=6` undercounts. |

Declared versus realized surface (`inbox landing-check`, `state: expansion_detected`): declared 14, realized 43,
symmetric difference 22.

- Added, never declared (21): the unplanned deliverable (`.plan/marshal.json`, `marshal-json-reference.md`,
  `_config_defaults.py`, `data-model.md`, `prepare_execute.py`, `worktree-handling.md`, `workflow-integration-git/SKILL.md`);
  the new `land` module `_orchestrator_land.py` and `persona-plan-orchestrator/SKILL.md`, `doc/concepts/orchestration.adoc`;
  the D1 lock-core adoption (`manage-status/scripts/_orchestrator_ledger.py` and its test); the D6(a) caller
  `tools-file-ops/scripts/file_ops.py` and `tools-file-ops/SKILL.md`; D3/D5's `github_ops.py`,
  `workflow-integration-github/SKILL.md` and its three test files (`test/plan-marshall/workflow-integration-github/**`
  was never declared); `manage-plan-documents/SKILL.md`; `uv.lock`.
- Declared, untouched (1): `test/plan-marshall/tools-integration-ci/**` — the queue-verb tests landed under
  `workflow-integration-github` instead.

## Metrics and Anomalies

- Tokens: `total_tokens` 8,118,544. 5-execute alone 2.52M for 13 planned tasks (lesson `2026-10-03-18-003`).
- Duration: 76,240 s wall (about 21 h 11 min).
- Anomalies:
  - 5 of 10 execute dispatches ended as `voluntary_checkpoint` hand-backs, each on an orchestrator-tier
    `module-tests`; TASK-8/10/11 were marked done with their new tests unrun until a later batched run.
  - `scope_creep_check` failed on every task (unregistered finding type) and its residual count was inflated
    by upstream history (110–141 files) — recurrence on lessons `2026-10-02-10-003` / `-004`.
  - The phase-transition mailbox probe misreported the plan as `not_orchestrated` throughout (fixed on `main`
    by #1685 mid-run; the running plan used the synced plugin copy). No mail was delivered, so nothing was lost.
  - `pre-submission-self-review` closed by operator decision at diminishing returns — the landing message says
    4 rounds / 17 findings, the PR body says 3 rounds / 13 findings (the PR body predates a later loop-back; not
    reconciled further).
  - No end-to-end `land` against the live merge queue was exercised — the verb's first real run will be its
    own live test.

## Routing and Merge Behavior

- Review: CodeRabbit raised findings; two were accepted as documented residuals rather than fixed (the
  `held_guard` release race window in `_locks_core.py`; the stale-run baseline window in
  `pr wait-for-queue-settle`). `cuioss-review-bot` was left `participated_stale` after a loop-back commit and
  needed an operator-directed re-run plus `--force` on `mark-step-done` (lesson `2026-10-03-18-001`). Sourcery
  (optional) refused on diff size.
- CI/merge: merge queue (`step.branch-cleanup.merge_mechanism=merge_queue`); squash-landed as `7a0af07c5`.
  Baseline rebased over 4 upstream commits. `cleanup_owed=false`.
- Collisions: the emit-time checked overlap with `unified-sync-all-harnesses` on
  `manage-locks/standards/machine-global-config-scope-audit.md` did not materialize — PLAN-10 never touched that
  file (it is absent from the merge commit).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-10 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-10 --field pr --value "#1690"`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-10 --field landing --value landings/PLAN-10.md`
- [x] row `plan_marshall_plan_id` stamped — already `orchestrator-land-verbs` (set at launch)
- [x] epic.md narrative reconciled (PLAN-10 annotation; Vision aspect 5 now shipped; harness-sync watch updated)
- [x] 8 candidate lessons dispositioned (3 promoted, 5 folded as recurrences)
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **WS-05 is complete.** The ledger branch can now be landed with `orchestrator land` instead of by hand —
  once the harness sync makes the new verb and `workflow/land.md` available to orchestrator sessions. Its first
  run is also the first live test of D5's queue-run matching.
- `phase-6-finalize`'s own landing gate is not wired to the new queue verbs (spec non-goal); lesson
  `2026-10-02-10-002` (detect a dequeued PR in the landing gate) can now consume `ci pr queue-state` /
  `wait-for-queue-settle` instead of adding a verb.
- The queue verbs are GitHub-only; no GitLab equivalent.
- No staged plan remains in this epic: only the four PM-MCP-parked rows.
