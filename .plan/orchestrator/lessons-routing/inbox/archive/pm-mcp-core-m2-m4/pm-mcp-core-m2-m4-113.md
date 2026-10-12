envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:50Z

# Triage workflow prescribes deliverable 0 for fix tasks, but manage-tasks commit-add rejects it

## Observation

`verification-feedback` / triage.md tells the triage leaf to create fix tasks with `deliverable: 0` (finding-originated, not tied to an outline deliverable). `manage-tasks commit-add` treats 0 as missing and refuses it. The leaf worked around it by attributing each of TASK-20..26 to the "nearest" outline deliverable, which silently misattributes fix work in per-deliverable metrics, commit chaining and retrospective deliverable alignment.

## Suggested direction

Pick one contract: either accept `deliverable: 0` (or an explicit `origin: fix` with no deliverable) in commit-add's validation, or change triage.md to require the source deliverable and document how to derive it. Add a contract test that the triage workflow's example payload passes commit-add validation.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-024.md` from plan runtime-lifecycle (PLAN-08, #29)
