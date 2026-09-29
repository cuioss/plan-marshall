# Landing Analysis: PLAN-09 — One fixed, shared worktree for all epic changes

epic: orchestrator-refactor
workstream: WS-05
pr: #1652 (squash `438a0a71f`, merged via the platform merge queue)

> Landing record for one shipped plan, written by `analyze` (inbox scan of
> `orchestrator-worktree-substrate-005.md`). The message was a lead: PR state was read from
> `ci pr view --pr-number 1652` (`state: merged`, `merge_commit_sha: 438a0a71f…`, head
> `feature/orchestrator-worktree-substrate`), and the deliverables from the squash commit's diff.
> `landing-check`: `complete: true`, no missing keys.

## Deliverable Fidelity vs Spec

Spec as re-scoped 2026-09-26: one shared worktree, not one per epic.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 `orchestrator.use_worktree` repository-wide knob | shipped-as-specified | `manage-config/standards/data-model.md`, `_config_defaults.py`, `_cmd_orchestrator.py`; this checkout reads `use_worktree: false` (default off, opt-in) |
| D2 one fixed worktree, key outside the plan-id grammar | shipped-as-specified | new `tools-file-ops/scripts/orchestrator_worktree.py` (370 lines); reserved key `_orchestrator`; `git-workflow.py` worktree-create guard |
| D3 idempotent, never-removed lifecycle | shipped-modified | create-once/reuse ships; `worktree-remove --plan-id _orchestrator` is refused only incidentally by the move-back guard, with no dedicated reserved-key check (landing residue) |
| D4 one resolver seam for both store roots, plan-side consumers included | shipped-as-specified, surface expanded | `file_ops.py`, `marketplace_paths.py`, plus undeclared consumers `manage-logging`, `manage-plan-documents` (`_cmd_request.py`), `manage-status` (`_status_query.py`), `plan-doctor`, `phase-1-init/SKILL.md` |
| D5 cutover guard | shipped-as-specified | `_cmd_orchestrator._cutover_refusal`; simplify flagged its base-branch resolution as a near-duplicate of `orchestrator_worktree._default_base_branch()` (advisory) |

## Metrics and Anomalies

- Tokens: 12,966,861 total. Wall time 104,820 s (about 29 h, spanning operator idle time).
- Surface: 64 files, +3,784 / −226. That is far wider than the 14 declared entries: the retrospective counted 9 undeclared test modules, and one declared test (`test_orchestrator_scope.py`) was never modified.
- Anomalies:
  - pre-submission-self-review looped back 5/5 and was closed by operator override (finding `5f65bb`). The dispatched leaf had no Grep, so it could not complete the full-surface sweep (263 candidates). See lesson message 003.
  - All 35 dispatch-boundary rows lacked a `step_id`, and all 11 execute rows recorded 0 tokens (lesson message 002).
  - The retrospective's chat-history aspect ran on 69 of 236,070 reduced bytes (lesson message 001).

## Routing and Merge Behavior

- Review: CodeRabbit raised two inferred Medium security notes, filtered as noise: a reused `_orchestrator` worktree is not checked to be on the ledger branch, and an unreadable main-checkout config silently falls back to the primary checkout. Sourcery refused on size (150,000-char cap; 4,010 changed lines); it is optional and did not gate.
- CI/merge: green; merged through the merge queue. `ci checks pull-request-runs` reported `run_count=0` although pull_request checks exist (possible observability defect, review-apparatus territory).
- Landing fact defect: branch-cleanup's "rev-parse HEAD" recorded the squash commit, but main had meanwhile advanced (#1655). The instruction is wrong whenever another PR lands before switch-and-pull.
- Collision: none with PLAN-10/-11, which did not run concurrently. The overlap waiver was not exercised.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `#1652`
- [x] row `landing` = `landings/PLAN-09.md`
- [x] row `plan_marshall_plan_id` = `orchestrator-worktree-substrate` (already stamped at launch)
- [x] epic.md: the #1641 ledger regression was restored from `88fcfc9ef` first (process-compliance-001); Watches added for the PLAN-09 residue
- [x] 4 candidate-lesson messages dispositioned (see epic.md / decision log)
- [x] resume anchor updated
