envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-19T21:03:33Z

# Process-rule gap: no script-mediated write path to the process-compliance inbox

## Observed

- Operator instruction: file process-rule issues into `.plan/local/orchestrator/process-compliance/inbox`.
- `manage-files write/mkdir` require `--plan-id` and resolve inside the plan store (`.plan/local/plans/{plan_id}`); no surveyed verb writes to the orchestrator store path above.
- AGENTS.md hard rule: `.plan/` access via scripts only — never Read/Write directly.

## Conflict

- Strict compliance allows neither a direct `Write` to the inbox (scripts-only violation) nor leaving the issues unfiled (operator instruction violation).
- The existing inbox files (e.g. `test-fidelity-rules-001.md`) show the envelope shape but not the sanctioned write verb that produced them.

## What was done on this run

- Asked the operator through the question tool; the operator granted a one-time exception (`Allow inbox files`) for this path.
- Wrote `test-fidelity-rules-follow-up-001.md` through `-005.md` via direct file writes under that explicit exception, after reading one existing inbox file for the envelope shape.
- Plan-state reads/writes otherwise stayed on script-mediated verbs.

## Request

- Publish one sanctioned script verb for filing process-compliance inbox findings (or document the exception flow: ask, record the grant, then write), so future runs do not have to choose between the scripts-only rule and the filing instruction.
