envelope_version=1
sender_type=plan
sender_id=plan-06-dispatch-roster
epic=process-compliance
kind=finding
created=2026-09-23T05:30:40Z

# Finding: PLAN-06 spec still names the pre-migration ledger path

plan: plan-06-dispatch-roster (epic process-compliance, PLAN-06)
kind: finding
phase: 1-init

## Observations

1. The operator's hand-off (`implement .plan/orchestrator/process-compliance/plans/PLAN-06-dispatch-roster.md`) resolves on the migrated tracked tier. The staged spec's own `## Hand-Off Command`, `## Write-Boundary`, and all four `## Claim Labels` evidence pointers still name `.plan/local/orchestrator/process-compliance/...`.
2. `manage-status transition --completed 1-init` returned `mailbox.probe: not_orchestrated` with reason `request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer)`, even though `request.md` carries `source_id: .plan/orchestrator/process-compliance/plans/PLAN-06-dispatch-roster.md`.
3. Post-init `git status --porcelain` is non-empty from foreign ledger state (`M .plan/orchestrator/process-compliance/epic.md`, `M .plan/orchestrator/process-compliance/status.json`, plus untracked inbox files of other epics). The init contract's clean-tree assertion cannot distinguish this plan's drift from other sessions' ledger writes.

## Why this matters

- A stale hand-off pointer re-enters init derivation (duplicate plan) unless the exists-collision prompt saves it; on non-interactive runs the prompt is bypassed (already recorded as an Open Defect for `phase-gates-004` item 1).
- A `not_orchestrated` probe cuts the two-way mailbox routing for an epic-linked plan carrying a valid new-path `source_id` — the same class PLAN-05 filed as "description-source plans carry no source_id", now observed WITH a source_id.
- The porcelain gate treats any tracked-tree dirt as this plan's violation, including orchestrator-ledger writes owned by other sessions.

## Proposed disposition (orchestrator decides)

- Re-point the spec's Hand-Off / Write-Boundary / Claim-Label paths to `.plan/orchestrator/...` (or teach the pointer detector both tiers).
- Teach the mailbox probe the migrated tier, or document the new-path linkage explicitly.
- Scope the post-init clean-tree assertion to non-ledger paths, or exempt `.plan/orchestrator/**` ledger churn owned by other sessions.

No repository source touched for this filing; recorded per the standing emit-convention instruction.
