envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-20T08:31:27Z

# Process-rule deviation: finalize dispatched without session identity under operator override

## Observed

- Finalize was aborted on the transcript-capable branch: no `session_ids`/`session_id`, late capture failed (`hook_not_configured`).
- The operator directed: ignore the session requirement and continue.

## Conflict

- The workflow permits unenriched finalize (no `session_id`, enrichment skipped with a gap flag) only on transcript-less targets. This target resolves transcript-capable, so dispatching without an identity violates the letter of the abort branch; refusing disobeys the operator.

## What was done on this run

- Recorded this deviation here and in the plan decision log.
- Dispatched `phase-6-finalize` without `session_id`; `record-metrics` is expected to skip `enrich` carrying the gap flag.

## Request

- Treat as a one-plan override, not a precedent. If unenriched finalize must stay available on transcript-capable targets, document the operator-grant shape (explicit direction plus mandatory inbox filing like this one).
