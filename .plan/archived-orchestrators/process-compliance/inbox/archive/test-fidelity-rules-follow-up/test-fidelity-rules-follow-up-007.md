envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-20T08:31:27Z

# Process-rule outcome: finalize aborted on missing session identity (transcript-capable branch)

## Observed

- All 14 tasks complete, queue empty (`loop-exit-guard` clean), `5-execute -> 6-finalize` boundary stamped, `5-execute` captured, transition to `6-finalize` succeeded.
- `status.metadata.session_ids` and the retired scalar `session_id` are both absent (plan-init logged the missing capture as a warning at creation).
- Exactly one late `platform_runtime session capture` was attempted; it failed with `hook_not_configured` (`$CLAUDE_CODE_SESSION_ID` unset; remedy named: install the SessionStart hook).
- `runtime-info` reports harness `claude` and no `runtime.target` override exists, so the workflow resolves the default transcript-capable target.

## Conflict

- None — the workflow names this branch explicitly: on a transcript-capable target with a failed late capture, abort finalize rather than inventing a filler identity.
- The cost is a stranded green worktree (14 done tasks, verified builds) with no PR until the identity exists.

## What was done on this run

- Aborted before the `phase-6-finalize` dispatch; no filler `session_id` was invented and no finalize step ran.
- The unenriched-proceed branch was rejected because the target resolves transcript-capable, not transcript-less.

## Request

- Remedy (operator): install the SessionStart hook (`/marshall-steward`), then re-enter with `/plan-marshall plan=test-fidelity-rules-follow-up` (auto-detect resumes at `6-finalize`; the late-capture path will then succeed).
- Consider a plan-init hard gate (or a pre-finalize early check) so a plan missing its session identity fails fast at creation rather than after a full execute phase.
