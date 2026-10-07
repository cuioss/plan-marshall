envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:54:22Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
source_plan=terminal-title-channel-reconciliation
source_pr=1023

# Check state carried zero participation information in BOTH directions on one PR

## Status of this message

This does not propose a new rule — the standing rule ("only `ci pr comments` is evidence of
participation") already exists and is correct. It is filed as **evidence**, because the
epic's PLAN-80 / PLAN-72 threads are currently reasoning about small-n reviewer-behaviour
counts and this run supplies a clean data point that the existing corpus does not contain.

## What makes this data point different

Prior evidence for the rule is spread across PRs: `#1016` had Sourcery SKIPPED-but-reviewing;
other PRs had PR-Agent SUCCESS-but-silent. Those are two observations on two PRs, each of
which is individually explainable as a per-PR glitch.

On **#1023, all three failure modes occurred simultaneously, on the same PR, against the
same diff**:

| Bot | Reported check state | Actual participation |
|-----|---------------------|----------------------|
| Sourcery | **SKIPPED** | **Reviewed** |
| PR-Agent | **settled / success** | **Published nothing** |
| CodeRabbit | **PENDING past 1005s** | Resolved and reviewed |

So on one PR the check state was wrong in the false-negative direction (Sourcery), wrong in
the false-positive direction (PR-Agent), and uninformative-but-eventually-right in the
latency direction (CodeRabbit). All three at once.

## Why that matters more than three separate observations

A per-PR glitch hypothesis predicts the errors are independent and rare, so a majority-of-
check-states heuristic would still work. Observing all three simultaneously on one PR
falsifies that: there is no majority to take. The check-state channel does not carry a
degraded participation signal — it carries **no** participation signal, and a consumer
cannot recover one by aggregating across bots on the same PR.

## Consequence for the epic

- Any refusal/participation detector work (PLAN-80) must treat check state as strictly
  unusable input, not as a prior to be corrected.
- The `_github_pr.py` wait path that keys on check state can wait the full buffer for a bot
  that already finished (CodeRabbit) while declaring finished a bot that never started
  (PR-Agent). Both cost real wall-clock in the finalize band.
- The PR-Agent erraticism count (PLAN-72) gains this PR as an observation, but note it
  published **nothing** here — consistent with the erratic-per-PR reading, not with the
  withdrawn "low signal" reading.
