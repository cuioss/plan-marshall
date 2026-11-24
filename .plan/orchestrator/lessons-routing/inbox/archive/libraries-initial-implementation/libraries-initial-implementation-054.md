envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:34Z

component=plan-marshall:phase-6-finalize
category=bug
title=phase-6-finalize: refuse pre-push-quality-gate done until the build verdict at HEAD is green
source_lesson=2026-11-22-21-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# phase-6-finalize: refuse pre-push-quality-gate done until the build verdict at HEAD is green

# Candidate lesson: pre-push-quality-gate was marked done in the same second a red build finished

- Source signal: plan-retrospective of plan-12-forms-kinds-schema-layout (inbox plan-12-forms-kinds-schema-layout-001; logging_gap and llm_to_script_opportunities aspects). Component `plan-marshall:phase-6-finalize`, confidence high.

## What happened

On the final round of PR 54 the finalize steps `finalize-step-simplify` and `pre-push-quality-gate` were logged `Completed (outcome=done)` at 20:00:47Z and 20:00:48Z, the same second the build in `build-results/default/maven-2026-11-22-195931.log` finished with BUILD FAILURE (`git-store`, `ConcurrentWritersTest.tenWritersWithOwnClones`, "Failed to close extension context"; 1 error in 406 tests). The branch was pushed on that verdict. A re-run at 20:01:08Z on the identical tree was green, so no broken code landed, but the gate passed on a red build. Neither re-fired step logged an `Executing step` line, so the step log alone does not show the order.

## Root cause

The step was closed by a chained command that did not wait for and read the build TOON `status` before marking the step done; nothing in `mark-step-done` ties the gate's outcome to the recorded build result.

## Candidate rule

`mark-step-done --step pre-push-quality-gate --outcome done` checks the change-ledger's last build row for the current HEAD and refuses unless it is `status: success` (an explicit operator override aside), and a re-fired step always logs its `Executing step` line. Distinct from the flaky test itself (PLAN-22 deliverable 2 item (i)): this one is about the gate accepting a red verdict. Owning component: `plan-marshall:phase-6-finalize`.
