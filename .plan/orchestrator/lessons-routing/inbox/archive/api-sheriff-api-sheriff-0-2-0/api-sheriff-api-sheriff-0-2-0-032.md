envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T06:22:31Z

# Candidate lesson: post-merge `ci checks wait --adaptive` ran into its deadline only because the post-merge Performance Benchmark was still running (plan-marshall:tools-integration-ci (adaptive checks wait))

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-25-edge-route-decomposition (PR cuioss/API-Sheriff#487), source message 010.

Orchestrator note: the benchmark run (39078174255) finished green afterwards, so the deadline was not a failure. On the project side, CLAUDE.md already assigns post-merge verification to the orchestrator.


- Source: orchestrator-supplied observation (post-merge CI wait), PR #487
- Plan: plan-v02-25-edge-route-decomposition (V02-25, edge route decomposition)

### Observation

After the merge, `ci checks wait --adaptive` hit its deadline after 702s. Nothing had failed. The only check still running was the post-merge Performance Benchmark job (`.github/workflows/benchmark.yml`, triggered on `pull_request: closed` when merged, so it stays attached to the PR). Its runtime is longer than the adaptive wait budget.

### Candidate rule (for orchestrator classification)

A post-merge wait that includes the PR-attached benchmark run should not read a deadline as a failure. Either allow a separate, longer budget for that known slow job, or treat "deadline with only the benchmark still running and no failing check" as its own outcome, not a timeout. CLAUDE.md already puts post-merge verification with the orchestrator, not the plan, so the plan-side wait on this job may be redundant.
