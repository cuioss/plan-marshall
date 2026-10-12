envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:03Z

# Some dispatched leaves transitioned the plan phase themselves

Component (suggested): plan-marshall:plan-marshall (orchestrator/leaf contract), category anti-pattern (marketplace-owned)
Signal: orchestrator-reported; not verified against this plan's logs by the lessons-capture step

## Observation (orchestrator-reported, unverified)

The orchestrator reports that some leaves self-transitioned the phase during the finalize loop-backs. The work log shows the loop-back transitions as `[MANAGE-STATUS] Phase: 6-finalize -> 5-execute` lines without naming the caller, so this step could not confirm which component issued them.

## Candidate directive

Record the caller notation on every `set-phase` / phase transition so the log shows whether the orchestrator or a leaf moved the phase; if a leaf did, return a signal instead, per the leaf contract.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); orchestrator report.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-013.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
