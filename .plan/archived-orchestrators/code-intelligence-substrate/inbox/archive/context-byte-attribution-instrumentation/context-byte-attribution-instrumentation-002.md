envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:41:07Z

# Close 6-finalize so its accumulator folds into the phase row

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source_plan: context-byte-attribution-instrumentation
source_pr: 1086

## Context

This plan's `metrics.md` reports a headline total of **2,335,557 tokens**, honestly marked
`n=4/6` with `> Partial: unrecorded phases — 6-finalize`. The true figure is approximately
**3,536,429** — the report under-states actual spend by **34%**.

The missing 1,200,872 tokens are not lost. They sit on disk in two places:
`work/metrics-accumulator-6-finalize.toon` (1,162,508 over 8 samples) and
`work/metrics-dispatch-boundaries-6-finalize.toon` (1,200,872 over 9 rows).

Notably, 6-finalize was the plan's **largest** phase — it outspent 5-execute (1,200,872 vs
1,155,049). The single biggest cost centre is the one the report cannot see.

## Root cause

`6-finalize` is the terminal phase, so nothing ever calls `end-phase`/`phase-boundary` on it. The
partiality contract keys "recorded" off the presence of an `end_time`, which never gets stamped.
`manage-metrics/SKILL.md` already names this exact case — "the canonical case is a `6-finalize` whose
terminal close never folded its accumulator in" — so the defect is documented but unfixed, and it
bites every plan, not just this one.

The retrospective step compounds it: `plan-retrospective` is dispatched from *inside* 6-finalize, so
`retrospective_tokens: 0` and the phase cannot be closed before its own retrospective runs.

## Proposed action

Have `archive-plan` (the terminal manifest step, which runs after every other finalize step) call
`end-phase --phase 6-finalize` unconditionally, then regenerate `metrics.md`. The accumulator already
holds the data; only the fold is missing.

Secondary: reconcile the accumulator against the dispatch-boundary ledger while folding. Here they
disagree by exactly 38,364 tokens — precisely the `blocked_session_restart` row, whose
`accumulate-agent-usage` call never fired because the session died mid-dispatch. A samples-vs-rows
comparison would have named that lost sample instead of silently absorbing it.

## Evidence

- aspect: plan_efficiency — reported 2,335,557 (n=4/6) vs reconstructed 3,536,429; 6-finalize is the dominant phase at 34% share
- aspect: logging_gap_analysis — `[6-finalize]` in `work/metrics.toon` carries `start_time` only, no `end_time`; file untouched since 10:51:28 despite finalize running to 16:27
- aspect: execution_context_dispatch_audit — accumulator 8 samples vs ledger 9 rows, delta 38,364 = the blocked_session_restart row
