envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:02Z

# pr wait-for-queue-settle surfaced a transient GraphQL error as pr_read_failed

Component (suggested): plan-marshall:tools-integration-ci (ci pr wait-for-queue-settle), category improvement (marketplace-owned)
Signal: branch-cleanup queue-landing gate, decision log 7b9edf

## Observation

While PR #30 was still queued, `pr wait-for-queue-settle` returned `pr_read_failed` on a transient GitHub GraphQL "Something went wrong" error. A `pr queue-state` read confirmed the PR was still queued, and a re-issued wait observed `settle: merged` (merged after about 270 s of an 1800 s budget).

## Candidate directive

Let the wait verb retry a transient GraphQL/5xx read inside its own budget (bounded, with backoff) and report a read failure only when retries are exhausted, so the caller does not need a manual re-check to tell a platform hiccup from a real failure.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); decision log 7b9edf.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-012.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
