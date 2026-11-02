envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-20T21:05:09Z

# Candidate lesson: a daemon-routed Maven build does not inherit the caller's environment (plan-marshall:build-maven / build-server-client)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492), source message 003.

Tooling angle: the executor silently ignores caller env when it routes through the daemon. Either forward a declared env allowlist to the daemon job, or warn when the caller's env differs from the daemon's for variables the build reads.


Plan plan-v02-12-idp-addressing-model (PR #492, merge 03cb4755), lessons-capture step. Component: build execution (build-maven executor / compose sample).

## Observation

A recorded build needed `API_SHERIFF_IMAGE` overridden (compose sample on arm64, because the published image is amd64-only — see the companion candidate). Setting the variable for the executor call had no effect: the default execution mode routes the build through the build-server daemon, which runs with its own environment, not the caller's.

## Rule

When a recorded build must see an environment override, run it with `--execution-mode in_process` and pass the variable via `env VAR=value python3 .plan/execute-script.py plan-marshall:build-maven:maven run ...` (one command, no `VAR=val cmd` shell prefix). A daemon-routed build silently ignores caller env.
