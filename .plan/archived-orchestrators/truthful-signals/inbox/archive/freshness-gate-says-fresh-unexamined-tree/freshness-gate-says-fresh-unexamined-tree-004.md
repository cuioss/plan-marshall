envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:28:16Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=freshness-gate-says-fresh-unexamined-tree
source_pr=1425

# blocked_user_review dispatch spend falls into neither published spend class

## Context

The dispatch-boundary fact block publishes two spend classes, and
`logging-gap-analysis.md` specifies them as the figures a reader acts on:

- `error_total_tokens` — spend on dispatches that are "genuinely non-productive"
- `retryable_total_tokens` — spend on retryable / infrastructure terminations,
  declared as exactly `blocked_session_restart` + `harness_cancellation`

On this plan both reported `0` for every phase. Meanwhile the 6-finalize boundary
ledger holds three rows with `termination_cause: blocked_user_review` carrying
189571 + 190364 + 194420 = **574355 tokens**.

`blocked_user_review` is a declared member of `DISPATCH_TERMINATION_CAUSES` and means
"the dispatch stopped because it requires an operator decision the leaf cannot make".
It is a non-completion. It is in neither published class.

## Root cause

The two spend classes were defined by enumerating their members
(`error`; `blocked_session_restart` + `harness_cancellation`) rather than by
partitioning the cause vocabulary. Any cause added to `DISPATCH_TERMINATION_CAUSES`
after those two definitions were written lands outside both and is silently
unaccounted.

A reader summing the published classes gets `0 + 0 = 0` and concludes the run had no
non-completing dispatch spend, on a plan with 574K tokens of it.

## Proposed action

1. Make the spend classification a **partition** of `DISPATCH_TERMINATION_CAUSES`,
   so every cause lands in exactly one class and adding a cause forces a class
   assignment. A third class (`operator_blocked_total_tokens`) is the obvious home
   for `blocked_user_review`.
2. Publish an `unclassified_total_tokens` residual alongside the classes, computed as
   total minus the sum of the classes. A non-zero residual is then self-reporting
   rather than invisible.
3. Add a structural test asserting the class assignment covers the tuple, in the same
   shape as the existing `test_manage_metrics.py` enum-equality tests.

## Evidence

- aspect: log_analysis — `6-finalize.rows[]` shows 3 `blocked_user_review` rows at 07:29:22, 09:09:24, 09:28:03
- aspect: log_analysis — `6-finalize.error_total_tokens: 0`, `retryable_total_tokens: 0`
- `logging-gap-analysis.md` — declares `retryable_total_tokens` as `blocked_session_restart` + `harness_cancellation`, an enumeration not a partition
- `manage-metrics/SKILL.md` — `blocked_user_review` is a declared member of the accepted cause set
