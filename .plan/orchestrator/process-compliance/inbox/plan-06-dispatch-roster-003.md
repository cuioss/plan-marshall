envelope_version=1
sender_type=plan
sender_id=plan-06-dispatch-roster
epic=process-compliance
kind=finding
created=2026-09-23T07:07:33Z

# Finding: post-refine clean-tree gate trips on concurrent orchestrator-ledger churn

plan: plan-06-dispatch-roster (epic process-compliance, PLAN-06)
kind: finding
phase: 2-refine (post-dispatch contract assertion)

## Observation

After the phase-2-refine dispatch returned (confidence 99.5, operator clarifications baked in), `git status --porcelain` is non-empty. Every dirty path is orchestrator-ledger state, none inside refine's allowed write paths (`.plan/local/plans/plan-06-dispatch-roster/**`):

- `M .plan/orchestrator/process-compliance/epic.md`, `status.json`, `plans/PLAN-06-dispatch-roster.md` (own spec), `plans/PLAN-10-entry-capture.md`
- `D .plan/orchestrator/process-compliance/inbox/module-budget-campaign-completion-001.md`, `-002.md` (concurrent drain archiving)
- `M .plan/orchestrator/truthful-signals/epic.md`, `status.json`, two TRUTH plans
- untracked `inbox/archive/...`, `landings/`, new TRUTH plan

The workflow's violation branch reads ANY non-empty porcelain as "refine dispatched edits to main checkout" and refuses to advance. That reading is false here: a dispatched leaf confined to the plan directory cannot produce other-epics' ledger churn. Concurrent orchestration sessions wrote the ledger while refine ran.

## Why this matters

- The gate cannot attribute dirt to its author — only that dirt exists. Under concurrent orchestration the gate blocks a compliant plan indefinitely.
- The plan's own spec file (`plans/PLAN-06-dispatch-roster.md`) was modified mid-run by another session: per the spec's adjacency note, the surface must be re-grounded against the new HEAD before scoping regardless of the gate outcome.
- A `[CRITICAL] refine_contract_violation` work-log entry was emitted per the branch contract (truthful record of the gate firing), but the plan does NOT attribute the dirt to refine.

## Proposed disposition (orchestrator decides)

- Attribute-aware assertion: exempt `.plan/orchestrator/**` and `.plan/archived-orchestrators/**` ledger churn owned by other sessions from the refine/outline/plan clean-tree gates, or compare against a per-plan baseline of plan-scoped paths only.
- Until then, plans running beside live orchestration need a sanctioned "foreign-dirt noted, advance" disposition owned by the operator (this run stopped at the gate and asked).

Recorded per the standing instruction; the run did not advance past the gate on its own authority.
