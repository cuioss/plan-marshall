envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=finding
created=2026-09-17T12:38:05Z

# Session-identity gate hard-blocks finalize on transcript-less targets (abstraction bug)

Observation (plan `plan-03-review-currency`, opencode target, 2026-09-17):
`status.metadata.session_ids` absent since init, single sanctioned late
`platform-runtime session capture` failed with `hook_not_configured`
(`$CLAUDE_CODE_SESSION_ID` unset), so the execution.md resolver aborted
finalize on a fully green plan (3/3 tasks done, orchestrator-tier
`verify plan-marshall` green, 22,184 tests).

Why this is a bug, not a gate working as intended: the session id has exactly
one consumer — transcript token enrichment (`record-metrics` → `enrich` →
`metrics normalized-tokens`). On OpenCode that op returns `no-op`
(`transcript_not_found`) on every input and `enrich` degrades gracefully, and
`opencode_runtime` documents that OpenCode exposes no session id at all. The
abort therefore strands green plans over telemetry that is a documented no-op
on the target — a Claude-only concern leaking through the platform
abstraction.

Remedy direction: gate the abort on transcript availability (target
capability), or degrade to proceed-without-enrichment with a recorded gap,
instead of aborting finalize where no transcript can exist.

Operator decision on this plan: proceed without session identity (sentinel
`NO_SESSION_IDENTITY`, fully disclosed in the decision log). No transcript
enrichment is lost beyond the documented no-op outcome; no filler identity
was invented.
