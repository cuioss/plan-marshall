# PLAN-LB-153: A commit the phase-5 orchestrator makes outside the settlement gets its change-ledger row

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

A commit the orchestrator makes during phase 5 outside the per-deliverable settlement (a `verify -Ppre-commit` rewrite, a style fix, a Javadoc fix made after the envelope) has no `kind=change` ledger row, so the 5-execute to 6-finalize transition refuses with `execute_commits_unrecorded` / `bookkeeping_gap`. Three consumer plans hit it in three days; two ended with `termination_cause=error` and an operator question about a commit spanning two deliverables. Give such a commit exactly one owner that writes its row at the point it is made, under a `deliverable_id` no reader mistakes for an outline deliverable, so no operator decision is needed.

## Deliverables

1. The orchestrator-tier hand-back commit has one row owner. Either the `git-workflow commit` verb appends a `kind=change` row in `5-execute` when the commit is made outside Step 10a, or the hand-back workflow commits gate output through a path that ledgers it. The row carries a `deliverable_id` that is not an outline deliverable id, and a commit that touches files of two deliverables needs no attribution decision. The PLAN-LB-126 finalize behaviour and Step 10a's single row stay unchanged: no commit gets two rows.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
2. The `execute_commits_unrecorded` refusal has a documented recovery in `execution.md` § Execute Phase Completion that appends the row for each unrecorded SHA the refusal names, instead of halting for the operator. Tests cover a gate-rewrite commit, a style-fix commit and a two-deliverable commit at the 5-execute boundary.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer

## Standing Constraints

- Step 10a's settlement row and the PLAN-LB-126 finalize row are not displaced: the verb never writes a second row for one SHA.
- A `deliverable_id` for a non-deliverable commit is distinguishable from an outline deliverable id by every reader of the ledger.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.

## Claim Labels

- OBSERVED: `_record_finalize_change` appends the row only when the plan's `current_phase` is `6-finalize`; its docstring states why — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` § `_record_finalize_change` (re-read at HEAD).
- OBSERVED (leaf reading, not re-read): the only two row writers in phase 5 are Step 10a (`phase-5-execute/SKILL.md`) and the settlement for `worktree_dirty_at_boundary` (`plan-marshall/workflow/execution.md`); the settlement runs only on a dirty tree, so a commit already made never reaches it.
- OBSERVED (leaf reading, not re-read): the refusal's remedy `remap` in `manage-change-ledger` only repairs rewritten SHAs; the manual `append --kind change` exists and no workflow prescribes it for this case.
- HYPOTHESIS: the verb cannot tell a Step 10a commit from an orchestrator hand-back commit without a caller-supplied marker — confirm/refute at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` § the `commit` verb's argument surface (verify-at-outline).
- Verify-first clause: the outline settles which of the two designs (verb appends in `5-execute`, or the hand-back path ledgers its commits) leaves Step 10a's row single, against the verb's current callers.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — `_record_finalize_change`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — § Execute Phase Completion
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — Step 10a and the hand-back text (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-git/` — verb tests (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none staged. PLAN-LB-154 edits `execution-recovery.md`, a different file of the same skill.
- Adjacent to: `PLAN-LB-126` (shipped; the finalize half) and `PLAN-LB-91` (shipped; the history-rewrite remap) stay untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-153-phase5-handback-commit-rows.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
