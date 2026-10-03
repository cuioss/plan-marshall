envelope_version=1
sender_type=plan
sender_id=opencode-bootstrap-executor-fix
epic=process-compliance
kind=finding
created=2026-09-27T08:08:35Z

# Process-compliance finding: finalize session identity cannot identify OpenCode

## Observed failure

At the `6-finalize` entry resolver for plan `opencode-bootstrap-executor-fix`:

- `status.metadata.session_ids` was absent.
- The single permitted late-capture attempt returned `hook_not_configured` because the runtime exposes no Claude session identity.
- The fallback `platform_runtime runtime-info` reported `harness: claude`, although the live session and deployment are OpenCode.
- Under the workflow contract, that made the resolver classify the runtime as transcript-capable and abort finalize instead of using the transcript-less OpenCode branch.

## Process-rule violation

The runtime target is resolved inconsistently across the finalize entry path. The session-binding primitive observes that no Claude session exists, but the target classifier defaults to Claude and never reaches the documented transcript-less branch. This is the same target-resolution defect family the plan is fixing, surfacing as a process-blocking finalize failure.

## Required remediation

- Unify runtime-target resolution for `platform_runtime runtime-info`, session capture, and the finalize session-identity resolver.
- On OpenCode, a missing session identity must resolve to the documented transcript-less finalize branch with a population-carrying metrics gap flag, not as transcript-capable Claude.
- Add a process-compliance regression test for finalize entry under an OpenCode runtime with no session identity.

## Severity

Process-blocking. The plan reached `6-finalize` with all tasks complete, but cannot dispatch the finalize skill without an operator repair.
