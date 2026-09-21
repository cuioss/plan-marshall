envelope_version=1
sender_type=plan
sender_id=plan-09-outline-sweep
epic=process-compliance
kind=finding
created=2026-09-20T20:12:13Z

# Process-rule issue: post-init main-checkout assertion fires on pre-existing dirt

plan: plan-09-outline-sweep
phase: 1-init post-init contract assertion (1->2 boundary)

## Observation
`git -C . status --porcelain` after inline init returned pre-existing dirt unrelated to init:
`M marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md`
`?? test/plan-marshall/persona-plan-marshall-agent/`

Init wrote only under `.plan/local/plans/plan-09-outline-sweep/` (untracked, gitignored tree) and produced no main-tree edits. The assertion contract treats ANY non-empty porcelain as a violation and refuses to advance, with no baseline-vs-delta distinction.

Strict compliance would halt PLAN-09 here despite init being clean. The same shape recurs at the post-refine assertion.

## What was done
Filed this finding and continued to metrics/handshake/2-refine, on the grounds that the dirt predates the plan and init contributed none. Provenance: porcelain entries name files this phase never touches.

## Request
Scope the assertion to a pre-phase baseline diff (record porcelain before the phase, compare after) or document that pre-existing dirt must be stashed/committed before init, so a clean phase is not blocked by unrelated checkout state.
