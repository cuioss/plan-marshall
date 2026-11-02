envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T09:32:39Z

# Candidate lesson: task derivation attaches whole-module gates to one half of a breaking split

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-44-route-type-merge` (PR cuioss/API-Sheriff#476), source message 003. Suggested route: plan-marshall (phase-4-plan task derivation / verification-command assignment).



**Signal:** orchestrator observation, confirmed in the work log.

## What happened

The deliverables split a breaking type merge into a production half and a test half (TASK-1/2 for the new `routing.Route` and its tests, TASK-3 for the production migration that deletes `RouteRuntime`, TASK-4 for the test migration).

- TASK-2 carried an edit to `PreBootFrameworkFreeArchTest` plus an arch-test verification. At 2026-10-15T16:54:00Z (row f85088) the narrow run went red with 10 violations, all on `routing.RouteRuntime`, which only TASK-3 deletes. The executor called this a "plan sequencing defect: deliverable 1 cannot hold its arch-test criterion while RouteRuntime exists". The operator moved the arch-test edit from TASK-2 to TASK-3 (row 390fbc).
- The orchestrator reports the same pattern for TASK-3. As the production half of the split, it got a module-wide `verify`-class verification that cannot pass until the paired test task (TASK-4) has migrated the tests.

## Suggested corrective action

When phase-4-plan splits a breaking change into production and test tasks, it should:

- give the production half a compile-scope verification (`compile -pl <module> -am`), not test/verify/arch gates;
- attach module-wide test, verify or arch-rule gates to the task that completes the pair, or to the deliverable-level sweep;
- place an arch-rule edit that only holds once a type is deleted in the task that deletes it.
