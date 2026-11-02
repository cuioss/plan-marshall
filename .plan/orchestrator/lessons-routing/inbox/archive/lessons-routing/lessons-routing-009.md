envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T17:51:16Z

# Two finalize surfaces disagree with the recorded state: a waiver the merge gate ignores, and a PR body that outlives a scope narrowing

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-05-response-hygiene (PR #526), candidate lessons 003 and 011. Observed with plugin and executor 0.1.2010.

## Observation

1. `manage-status loop-back close --waive-refire finalize-step-simplify/security-audit` recorded a waiver for the two steps. Later `pre_merge_gate merge` refused with `merge_candidate_not_gated` for exactly those two steps, because the merge gate does not read the waiver. Both steps had to be re-run anyway, so the waiver was a no-op that cost a round. This is the same family as the HEAD-binding finding routed earlier from plan-v02-20 (an operator narrowing of the re-fire set that the barrier does not honour).
2. During the run the delivered behaviour narrowed (withhold all five conditional validators, then withhold two on GET and HEAD). The PR body kept describing the first version until the functional review flagged it as a false self-report, and a replacement test lost the rationale comment of the test it replaced.

## What to consider

- Either make the merge gate honour a recorded `--waive-refire` waiver for the current HEAD, or make `loop-back close` refuse or warn that the waiver will not satisfy the merge gate.
- When a fix round changes the delivered behaviour and not only its implementation, regenerate the PR body from the final diff and re-check that replaced tests keep the rationale comment, before the functional review.
