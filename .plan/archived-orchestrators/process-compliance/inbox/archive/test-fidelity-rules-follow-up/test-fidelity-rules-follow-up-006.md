envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-19T21:03:33Z

# Process-rule deviation: advanced past the post-refine clean-tree gate under operator override

## Observed

- `phase-2-refine` re-run (deep lane) returned `status: success`, 99% confidence, complex track, 0 pending, no extra validation.
- Post-dispatch assertion `git -C . status --porcelain` returned `M uv.lock` — the violation branch mandates a `[CRITICAL]` entry, no transition, no metrics fused call.
- The `[CRITICAL]` entry was emitted; then the operator directed: ignore the `uv.lock` change for this plan.

## Conflict

- The workflow's violation branch has no override lane: it orders the orchestrator to stop, with recovery only via revert or relocate of the offending files.
- Obeying the operator (advance) violates the letter of that branch; refusing disobeys the operator.

## What was done on this run

- Recorded this deviation here and in the plan decision log, naming the file and the override.
- Advanced the `2-refine -> 3-outline` metrics boundary and the `2-refine` handshake capture with the tree still dirty, so downstream history shows the gate was failed-then-overridden rather than passed.
- `uv.lock` was left untouched (neither reverted nor moved).

## Request

- Define the sanctioned override shape for a failed clean-tree gate (explicit operator disposition string plus a mandatory inbox filing like this one), or confirm that the gate is absolute and an override must never advance.
