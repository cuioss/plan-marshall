envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:38Z

# Outline deliverables that extend a shared test fixture must depend on the deliverable that creates it

## Observation

Deliverable 2 created `RuntimeChildProcess.java` and `KilledRuntimeFixture.java` (write-new). Deliverables 4, 6, 7 and 8 listed `RuntimeChildProcess.java` as write-replace and built their killed-runtime ITs on the fixture, but none depended on 2, directly or transitively, although the Approach section said they extend it. Phase 4 could have ordered or parallelised them before the fixture existed. The fix pass added 2 to the depends of 4 and 8 (6 and 7 inherit through 4).

## Rule

When a deliverable lists a file as write-replace that another deliverable creates as write-new, the Metadata depends line must name the creating deliverable (directly or transitively). The outline author can check this mechanically: every write-replace path that is a write-new path elsewhere in the outline implies a dependency edge.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-002.md` from plan runtime-lifecycle (PLAN-08, #29)
