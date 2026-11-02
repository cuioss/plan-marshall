envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T15:42:39Z

# Candidate lesson: learned build timeout (525s) for verify -Ppre-commit clipped under foreign load (plan-marshall:build-maven (adaptive timeout) / project-local build gate)

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-26-config-validator-split` (PR cuioss/API-Sheriff#463), source message 007 (previously filed locally as API-Sheriff lesson 2026-10-14-20-005, now removed there).


**Source signal:** orchestrator-observed run behaviour (build gate).

**Observation:** The build gate ran `verify -Ppre-commit` through the Maven executor with the adaptive (learned) timeout of 525s. Under foreign machine load (other sessions / builds running concurrently) the run exceeded that budget and was clipped with `status: timeout`, although the build itself was not hung. A re-run at a larger budget is what established the actual result.

**Why it matters:** A learned timeout tuned on quiet-machine runs has no headroom for concurrent load, and a clipped run reads like a failure of the change. This repeats the pattern already recorded for this repo (a `status: timeout` near the budget means clipped, not hung; check `uptime` / running processes and the Maven log before blaming the change).

**Candidate corrective direction (for orchestrator classification):** Either the learned timeout should carry a load-aware margin (or a floor near the 600000ms Bash ceiling for the quality-gate profile), or a timeout outcome should trigger one automatic retry at the ceiling before it is reported as a gate failure.

**Suggested component:** plan-marshall:build-maven (adaptive timeout) / project-local build gate
