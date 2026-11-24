envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:35Z

component=plan-marshall:phase-5-execute
category=bug
title=phase-5 and pre-push leaves: run result-bearing builds synchronously with an explicit timeout, never in the background
source_lesson=2026-11-23-12-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# phase-5 and pre-push leaves: run result-bearing builds synchronously with an explicit timeout, never in the background

# Candidate lesson: leaf agents backgrounded result-bearing builds

- Source signal: leaf-rule violation in plan plan-23-forms-hardening (inbox plan-23-forms-hardening-009; orchestrator-reported, verified by timing in the logs).

## What happened

Twice the build-busy title token was set and cleared within about 2 seconds and only then was the in-process build resolved and started: 09:20:43 set, 09:20:45 cleared, 09:20:46 resolved, the `maven run` finishing at 09:26:01 after 316 s (phase-5 envelope 2); and 10:14:08 to 10:14:10 in the pre-push-quality-gate leaf. The Bash call returned at once while the build ran. The execution-context contract allows `run_in_background` in a leaf only for fire-and-forget work; a build whose verdict the next step needs runs synchronously with an explicit timeout (600000 ms). No wrong verdict resulted, but the backgrounding hides the exit code from the synchronous path and makes the build-busy bracket wrong.

## Candidate rule

State the explicit `timeout: 600000` at the call site of the canonical build commands in the phase-5 and pre-push workflow text (the likely trigger is a build expected to outlast the default timeout), and use the cleared build-hook token with no completed `maven run` yet as a detector of a backgrounded build. Owning components: `plan-marshall:phase-5-execute` and the pre-push gate leaf text.


## Recurrence in a later plan (plan-11-store-anchoring-signed, inbox plan-11-store-anchoring-signed-010)

`verify -Ppre-commit` ran about 290 s per task here (slowest maven call 350 s, 54 maven calls, 47% of script time). The harness moved every command over about 180 s to the background, so the execute leaf of envelope 1 finished its gates by notification, and envelope 2 ended four times with "waiting on its own background work" before it handed back. One gate run stopped at the learned build timeout of 326 s and had to be re-run with `--timeout 590` (see also 2026-11-23-12-004). Open question the plan could not settle: whether the Bash `timeout` the leaf passes reaches the tool call above 180 s on this target; if not, long per-task gates belong on the orchestrator-tier path.
