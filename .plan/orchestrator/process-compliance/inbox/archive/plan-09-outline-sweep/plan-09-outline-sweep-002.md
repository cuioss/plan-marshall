envelope_version=1
sender_type=plan
sender_id=plan-09-outline-sweep
epic=process-compliance
kind=finding
created=2026-09-20T20:11:59Z

# Process-rule issue: mailbox probe reports not_orchestrated for valid orchestrator spec pointer

plan: plan-09-outline-sweep
epic: quality-aspect PLAN-09
phase: 1-init transition 1-init -> 2-refine

## Observation
`request.md` was created via the Step 4 file-pointer branch with `--source-id .plan/local/orchestrator/quality-aspect/plans/PLAN-09-outline-sweep.md` (the canonical emitted shape `implement .plan/local/orchestrator/{slug}/plans/PLAN-NN-{slug}.md`).

On `manage-status transition --completed 1-init` the mailbox checkpoint returned `probe: not_orchestrated` with reason `request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer), so this plan has no epic and no mailbox`.

The pointer IS an orchestrator plan-spec path, created per the file-pointer contract. Classification via `inbox detect` does not recognize this shape, so the plan cannot receive epic mailbox mail despite originating from the epic.

## What was done
Continued; mailbox linkage for this plan remains unresolved. No `inbox read` polling will observe epic mail.

## Request
Align `inbox detect` pointer grammar with the Step 4 file-pointer canonical shape, or document the expected `--source-id` form for orchestrator-spec ingestion so the mailbox probe resolves `orchestrated=true`.
