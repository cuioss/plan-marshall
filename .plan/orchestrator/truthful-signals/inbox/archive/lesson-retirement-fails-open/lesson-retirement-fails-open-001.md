envelope_version=1
sender_type=plan
sender_id=lesson-retirement-fails-open
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:02:32Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# Emit [DISPATCH] on re-entry dispatches, not only on first entry

## Context

Plan `lesson-retirement-fails-open` (PR #1113) emitted 14 `[DISPATCH]` lines into
`logs/work.log` across a run that ran at least 24 dispatched `execution-context`
envelopes, counted from the `(execution-context.{name}) Complete` markers the
envelopes themselves write. At least 10 dispatches produced no `[DISPATCH]` line
at all.

The unlogged set is not random. Every first-entry dispatch was logged, and every
re-entry, retry, or post-`branch-cleanup` dispatch was not:

- the `phase-3-outline` re-dispatch after the round-1 envelope died on an API
  connection error
- `fix-self-review-findings` rounds 1 and 2
- `pre-submission-self-review` iterations 3 and 4 (iterations 1 and 2 were logged)
- both `phase-5-execute` loop-back re-entries
- `project:finalize-step-plugin-doctor` round 2 (round 1 was logged)
- `plan-marshall:automatic-review` round 2 (round 1 was logged)
- `wait-region-unified-triage` round 2 (round 1 was logged)
- `project:finalize-step-review-retrospective`
- the `plan-marshall:plan-retrospective` envelope that produced this observation

## Root cause

The `[DISPATCH]` emission obligation is fused to the first-entry dispatch branch
in the phase-6-finalize and orchestrator workflows, but the re-entry, retry and
loop-back paths reach the dispatch call through a different branch that carries no
emission step. The steps that run after `branch-cleanup` appear never to have had
one.

## Proposed action

Move the emission to the dispatch call site itself so it cannot be reached without
emitting, rather than pairing it with the first-entry branch. Every path that
spawns an `execution-context-{level}` envelope — first entry, retry after error,
loop-back re-entry, and every post-`branch-cleanup` finalize step — must emit.

## Impact

`[DISPATCH]` is the sole evidence surface for the execution-context dispatch audit
(`plan-retrospective` aspect 11) and for `ref-workflow-architecture/standards/dispatch-logging.md`'s
enforcement consumers. On this plan the line count under-reports actual dispatch by
roughly 40 percent, so any audit or cross-plan aggregation that counts dispatch
lines is counting first entries and calling the result a dispatch total.

## Evidence

- aspect: logging_gap_analysis — "14 [DISPATCH] lines emitted against at least 24 dispatched envelopes evidenced by execution-context.{name} Complete markers"
- aspect: execution-context-dispatch-audit — two `dispatch_coverage_violation` findings at step granularity (`project:finalize-step-review-retrospective`, `plan-marshall:plan-retrospective`), both classified DISPATCHED by `phase-6-finalize/standards/dispatch-inline-split.md`
- aspect: log_analysis — `top_tags` records `DISPATCH,14` for the whole plan
