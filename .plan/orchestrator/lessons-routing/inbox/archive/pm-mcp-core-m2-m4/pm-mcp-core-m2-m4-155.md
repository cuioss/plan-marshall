envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:48Z

# Candidate lesson: finalize triage builds are not recorded in the change ledger

- Component: plan-marshall:manage-change-ledger / plan-marshall:phase-6-finalize (triage, push freshness)
- Suggested category: improvement
- Signal: orchestrator observation, partly corroborated by the logs

## Observation

Builds that triage sub-agents ran during phase 6 were not recorded in the change ledger at the
committed tree sha. Push freshness therefore read `stale` after each inline-fix commit, and the
orchestrator re-ran a full clean verify each time.

## Evidence

- script-execution-2026-10-12.log: the last `manage-change-ledger append` is at 18:25:46Z (phase 5).
  None follows during phase 6, although work.log shows four further build rounds there
  (pre-push-quality-gate done at 19:29, 19:49, 20:29, 21:04 and 21:40, with triage builds between).
- The `stale` freshness readings are the orchestrator's observation and are not written to the
  plan logs.

## Suggested correction

A build that a dispatched triage leaf runs successfully on a committed tree records a ledger entry
for that tree sha, the same as phase-5 builds do, so the following push can verify freshness without
another full build.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-003.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
