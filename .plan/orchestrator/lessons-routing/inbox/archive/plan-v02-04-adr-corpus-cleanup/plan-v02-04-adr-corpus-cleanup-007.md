envelope_version=1
sender_type=plan
sender_id=plan-v02-04-adr-corpus-cleanup
epic=lessons-routing
kind=finding
created=2026-10-26T09:56:06Z

# Recurrence: post-merge `ci checks wait --adaptive` on the merge-queue path exceeds the 600 s Bash ceiling (plan-marshall:tools-integration-ci adaptive checks wait)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-04-adr-corpus-cleanup (PR cuioss/API-Sheriff#521, merge f5826465), lessons-capture step.

Related to api-sheriff-api-sheriff-0-2-0-032 ("post-merge `ci checks wait --adaptive` ran into its deadline only because the post-merge Performance Benchmark was still running").

## Observation

After the merge queue merged PR #521, the post-merge `ci checks wait --adaptive` call needed longer than the harness Bash ceiling of 600 s. The adaptive budget is not capped at the harness ceiling, so a synchronous call cannot finish inside one Bash invocation, and the wait has to be re-issued or detached by hand.

## Why it matters

The adaptive budget and the harness ceiling come from two different seams and do not know about each other. A synchronous wait the workflow documents as one call cannot complete as one call, and a leaf is not allowed to background result-bearing work.

## Suggested direction

- Clamp the adaptive budget to the `harness bash-timeout-ceiling` and return a resumable `still_pending` result with the elapsed time, so the caller re-issues the wait; or
- route the post-merge wait through the `await-long-running` detach seam from the orchestrator, as the pre-merge wait-region barrier already is.
