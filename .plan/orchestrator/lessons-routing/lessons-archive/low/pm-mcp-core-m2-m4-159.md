envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:51Z

# Candidate lesson: manage-metrics record-dispatch-boundary rejected at the 5-execute to 6-finalize boundary

- Component: plan-marshall:manage-metrics
- Suggested category: bug
- Signal: script failure cluster (argparse_rejection, 1 occurrence)

## Evidence

- work.log 2026-10-12T18:37:02Z: script_failure notation=plan-marshall:manage-metrics:manage-metrics
  exit_code=2 failure_kind=argparse_rejection, usage of `record-dispatch-boundary` printed
  (--plan-id, --phase, --termination-cause {voluntary_checkpoint, ...}). The logged detail is cut off,
  so the rejected argument is not visible. It was 38 s after phase-5-execute transitioned to
  6-finalize itself.

## Suggested correction

Check the caller of record-dispatch-boundary at the phase boundary against the declared flags and
the termination-cause vocabulary. Make sure the failure detail names the rejected argument rather
than only the usage text.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-009.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
