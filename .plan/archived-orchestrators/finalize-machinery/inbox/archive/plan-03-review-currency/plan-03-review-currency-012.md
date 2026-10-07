envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T19:29:53Z

component=plan-marshall:platform-runtime
category=improvement
created=2026-09-17
bundle=plan-marshall

# Session-identity gate should be target-aware before aborting finalize

The finalize entry resolver aborts the whole phase when session capture
fails. On transcript-less targets the session id has exactly one consumer
(transcript token enrichment), which is a documented no-op there — so the
abort strands green plans over telemetry that cannot exist on the target.
The opencode runtime documents that it exposes no session id at all.

## Proposal

Before aborting, check transcript capability for the active target (e.g.
the `metrics normalized-tokens` no-op contract): when no transcript can
exist, degrade to proceed-without-enrichment with a recorded gap instead of
aborting. Keep the hard abort where a transcript exists but capture failed.

## Evidence

Plan plan-03-review-currency: `session_ids` absent since init, late capture
failed `hook_not_configured`; resolver aborted a fully green plan
(3/3 tasks done, orchestrator-tier verify green). Operator override +
`NO_SESSION_IDENTITY` sentinel completed the run with zero enrichment loss
beyond the documented no-op outcome. Bug filed as inbox finding
plan-03-review-currency-003.md.
