envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:44:29Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# A loop-guard counter must count the current cycle, not the PR's lifetime

## Observation

PLAN-111 added a bounded self-response-loop guard to `cmd_fetch_findings`: when the self-authored-reply pre-filter strips too many "own reply re-ingested as new" comments in a row, the guard files a Q-Gate finding at the bound instead of looping forever. Round 1 of that guard compared a **lifetime** counter against the bound — `fetch_findings` runs with `unresolved_only=False`, so it counts every `## Triage dispositions` comment the PR has ever accumulated, across every prior review cycle.

Consequence: any PR that legitimately completed 3+ ordinary triage cycles would trip the guard on its next fetch, even with zero actual self-ingestion happening in the current cycle. `pr-agent` caught this on review before merge.

## Why it matters

This is the epic's own theme (a confident signal hiding a caveat), reproduced **inside the fix built to correct a different instance of it**. "Loop detected" read as authoritative while the counter backing it measured the wrong thing — cumulative history instead of convergence within the run that matters.

## Corrective rule

Fixed in TASK-004 by introducing `_current_cycle_self_response_count` — a **trailing-run** count computed by relying on the provider's comment ordering (grouped by kind, not strict chronological order) to isolate the current cycle from prior ones.

Generalised detector: any bounded-loop guard added over a fetch/query call that does not itself scope to "this run" needs an explicit audit of whether the underlying data source is lifetime-cumulative or run-scoped. A guard against runaway repetition is only correct if what it counts actually resets between the units it is trying to bound.

## Evidence

Caught live, pre-merge, by `pr-agent` review on PR #1047; fixed same-PR in TASK-004.
