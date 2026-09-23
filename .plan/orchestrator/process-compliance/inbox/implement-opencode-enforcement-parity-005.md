envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-23T07:47:41Z

envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-23T07:40:00Z

# Finding: phase-5-execute scope-creep guard is unsatisfiable — worktree plan diffs against a stale plan_creation_sha and its emission type (scope_creep_warning) is not a member of FINDING_TYPES

Epic: process-compliance
Plan: implement-opencode-enforcement-parity
Phase observed: phase-5-execute, TASK-001 Step 6.5 scope-creep guard

## Summary

The pre-task scope-creep guard (`phase-5-execute/scripts/scope_creep_check.py`, invoked at SKILL.md Step 6.5) returned `status: error, error: finding_persist_failed` with `residual_count: 49` / `threshold: 5` at the very first task of phase 5. Two independent structural defects make the guard unfinishable for worktree plans that execute against a mainline that has moved since plan creation.

## Facet A — Baseline geometry is wrong for worktree plans

`scope_creep_check.py` reads `plan_creation_sha` from `references.json` and computes `git diff --name-only {plan_creation_sha}..HEAD` against the worktree, then subtracts the union of all deliverables' `affected_files`. `plan_creation_sha` is written once at phase-1-init (`_references_crud.py:113`). For a plan executed under `use_worktree: true`, the executing worktree is materialized at `prepare_execute` time from current main — its base (`feature/implement-opencode-enforcement-parity`) is the main tip THEN, which is always later than or equal to `plan_creation_sha`.

Observed here: `plan_creation_sha = 1a9a672` (PR #1582); worktree base `HEAD = 1bd5c6a` (PR #1586); between them lie the merged PRs #1583–#1586 (7 commits). The 49-file residual is 100% that upstream drift — orchestrator ledger files, other plans' archives, marketplace skills, and tests touched by those PRs. Not one residual file is an edit this plan made; the only worktree mutation is the TASK-001 edit to `_manifest_core.py`, which IS declared in `affected_files` and therefore correctly subtracted.

Consequence: any worktree plan whose `plan_creation_sha` predates the materialization base will trip the guard as soon as upstream main has moved, with a residual proportional to upstream activity — a false positive by construction. The correct base for the diff is where this plan's execution actually began (the worktree branch point / merge-base), not the phase-1-init sha.

## Facet B — The emission type does not exist, so a genuine over-threshold hit can never be recorded

SKILL.md:635 documents the persist path as `manage-findings qgate add --type scope_creep_warning`. `FINDING_TYPES` (`tools-file-ops/scripts/constants.py:96`) has no `scope_creep_warning` member, and both the CLI accept-set (`manage-findings.py:456`, `choices=FINDING_TYPES`) and the in-process primitive (`_findings_core.py:1051-1052`) reject it. `_emit_finding` therefore always gets a rejection whenever `residual_count > threshold`, and the guard must report `finding_persist_failed` (exit 1) instead of persisting a triage-able finding. The guard can never emit; it can only fail. Even a genuine scope-creep hit cannot reach the Step 11 triage loop.

## Suggested fixes

1. Facet A: compute the diff base as the worktree branch point — `git merge-base {plan_creation_sha} HEAD` (or the materialized worktree base captured at prepare) — so upstream merges between init and materialization are not measured as this plan's residual. Semantic of the check ("files modified since the plan was created") should read over the plan's own execution window.
2. Facet B: either register `scope_creep_warning` in `FINDING_TYPES` (and the `qgate add --type` accept-set) so the documented emission path works, or change the guard to emit an existing type and update SKILL.md:635/`_emit_finding` in lock-step.
3. Until fixed, the documented plan-scoped knobs are the only unblocks: re-anchor `references.json:plan_creation_sha` to the worksstand worktree base (orchestrator-owned), or set `phase_5.scope_creep_threshold` in marshal.json (0 disables the guard → `could_not_look` / `guard_disabled`).

## Evidence

- Worktree `git status --short`: single modification `M marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py` (= TASK-001 step_target, declared in affected_files).
- `git merge-base 1a9a672 HEAD` = `1a9a672`; `git rev-list 1a9a672..HEAD` = 7 upstream commits (PRs #1583–#1589), none this plan's work.
- `after` dispatch log: `residual_count: 49`, `threshold: 5`, `finding_persist_failed` with message `Invalid finding type: scope_creep_warning. Must be one of FINDING_TYPES ...`.
- `scope_creep_check.py` lines 17-23 (baseline semantics), 212 (base_sha read), 163-192 (`_emit_finding` → `add_qgate_finding` with `finding_type='scope_creep_warning'`).
- SKILL.md:593 (guard contract), SKILL.md:635 (documented persist path).
- `constants.py:96` FINDING_TYPES members; `_findings_core.py:1051-1052` rejection; `manage-findings.py:456` argparse choices.
