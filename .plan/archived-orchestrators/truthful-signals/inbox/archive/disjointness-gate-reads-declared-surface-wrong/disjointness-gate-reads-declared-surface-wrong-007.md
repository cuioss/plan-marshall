envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:36:11Z

component=plan-marshall:persona-plan-orchestrator
category=improvement
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# An operator directive that supersedes a config flag is invisible to config-derived accounting

## What happened

PR #1366's finalize spent a ~2h06m idle block (2026-08-30T00:08:37Z ->
02:14:15Z) waiting for a CodeRabbit rate window that never reopened in time. The
wait bought nothing: CodeRabbit refused again at 00:03:54Z with `cause=quota` and
never reviewed `e60da719c`.

Reconstructing that block from configuration alone says the machinery misbehaved:

- `marshal.json` / manifest `step_params`: `review_rate_window_await: false`
- `required_bots: pr-agent`; `optional_bots: coderabbit,sourcery` — CodeRabbit is
  **optional**
- `automatic-review` iteration 3 had `participation_complete: true` and the required
  bot had reviewed the HEAD

The contract said do not wait. The run waited anyway — **correctly**.

## The actual authority

The operator ordered it, in the session, three hours earlier:

> continue as defined to the end of finalize. DO only stop on issue. If you run into
> the coderabbit limit, wait the remining time for the window to be resetted, Do the
> wait up to 5 timnes (parallel plans running)

Recorded as `decision.log` `d3ae80`: "OPERATOR DIRECTIVE for the remainder of
finalize ... **This supersedes the standing merge-as-is guidance for this run.**"

The run then named that supersession at every decision point rather than laundering
the wait as contractual — `9d114c`: "Contract alone would take Branch A ... Operator
decision d3ae80 supersedes"; `8ff41d`: "Rate-window WAIT 1 of 5 authorised ... the
leaf could not await it because `review_rate_window_await` is false and the recovery
is scoped to `required_bots`". The behaviour was exemplary.

## Why it matters

The directive exists **only as `decision.log` prose**. No structured field records
that a config value was overridden for this run. Consequences:

- Any conformance or cost read that reconstructs the run from `step_params` sees the
  flag disabled and attributes ~2h of idle to machinery drift.
- The run's **own** post-hoc self-report did exactly this, describing the hour as
  served "on a rate window that was never workflow-sanctioned" — true of the
  workflow, and silent on the operator directive that was the real authority.
- A retrospective grading the run against its config will penalise correct
  obedience.

## Remedy shape

Record operator overrides as **structured state**, not only as decision prose — for
example a `status.metadata.operator_overrides[]` entry carrying
`{setting, config_value, directive_value, scope, decision_log_hash, set_at}`.

Then any consumer reading `review_rate_window_await` also sees that it was
superseded for this run, and idle attributable to a directive is separable from idle
attributable to the machinery. Retrospectives should read that field before
attributing spend to a component.

## Adjacent measurement note

The largest idle block in this run was **not** the review wait: `branch-cleanup`
idled **6h03m** (02:23:36Z -> 08:26:09Z) awaiting an operator decision after its own
classifier returned `auto_reconcilable: true` with `conflict_count: 0`. The
`no_overlap_only` threshold escalated a conflict the classifier had already graded
safe.
