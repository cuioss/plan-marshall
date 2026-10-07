envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:50:23Z

component=plan-marshall:manage-metrics
category=bug

# record-dispatch-boundary accepts 11 termination causes; SKILL.md documents 6 — and 5 of this plan's 6 rows use an undocumented one

## Observation

`manage-metrics record-dispatch-boundary --termination-cause` accepts eleven values. Its own SKILL.md documents six.

**Actual argparse choices** (`record-dispatch-boundary --help`):

```
voluntary_checkpoint, task_complete_returned_verbatim, budget_yield,
harness_cancellation, error, clean_exit_queue_empty,
step_complete, blocked_user_review, blocked_session_restart,
task_batch_complete, agent_returned
```

**Documented in `manage-metrics/SKILL.md`** — identically in the Operations section and in the `## Canonical invocations` block:

```
{voluntary_checkpoint|task_complete_returned_verbatim|budget_yield|harness_cancellation|error|clean_exit_queue_empty}
```

Five values are undocumented: `step_complete`, `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned`.

**This is not theoretical for this plan.** PLAN-TRUTH-001's own dispatch-boundary rows:

| Phase | Cause | Rows |
|-------|-------|-----:|
| 4-plan | `task_batch_complete` | 1 |
| 5-execute | `harness_cancellation` | 1 |
| 5-execute | `voluntary_checkpoint` | 2 |
| 5-execute | `clean_exit_queue_empty` | 1 |
| 6-finalize | `step_complete` | 4 |
| 6-finalize | `error` | 1 |

Five of ten rows carry a cause the documentation does not list, and `step_complete` alone is 40% of the corpus.

**The divergence propagates into a consumer contract.** `plan-retrospective/references/logging-gap-analysis.md` instructs the DISPATCH_TERMINATION_CAUSE rule to emit:

> One `info`-severity finding with the per-cause distribution **over the canonical value set** (e.g. `"4 voluntary_checkpoint, 1 task_complete_returned_verbatim, 2 budget_yield, 0 harness_cancellation, 0 error, 1 clean_exit_queue_empty"`).

Its worked example enumerates the six documented values. A retrospective following that instruction literally reports a distribution that omits half of this plan's rows — and the omitted half is the majority.

The same document's `> 50%` agent-initiated-re-dispatch warning is computed over `voluntary_checkpoint + task_complete_returned_verbatim`. With five of ten rows sitting outside the value set the rule reasons about, the denominator is no longer the population.

## Root cause

The argparse `choices` list grew and the SKILL.md prose did not. Nothing binds them: `plugin-doctor`'s `ARGUMENT_NAMING_*` cluster reads the `## Canonical invocations` block as source-of-truth for verb and flag *names*, and passes cleanly here because the verb and the flag are both correct. Enum *membership* is not checked, so the structural guard that exists for this document has a hole exactly the shape of this defect.

The consequence is the standing archetype: a document that calls its own list "the canonical value set" while a live producer emits values outside it. The phrase asserts completeness that nothing enforces.

## Proposed action

1. Reconcile SKILL.md's Operations section and `## Canonical invocations` block with the eleven actual choices, and document the semantics of the five new values — `step_complete` in particular is now the dominant finalize-phase cause and has no written meaning.
2. Extend the `plugin-doctor` canonical-invocations analyzer to compare documented `{a|b|c}` enum literals against the script's argparse `choices` for the same flag. This defect class is mechanically detectable from the two artifacts the analyzer already reads.
3. Update `logging-gap-analysis.md`'s DISPATCH_TERMINATION_CAUSE rule to derive its distribution from the observed rows rather than from a hand-listed canonical set, and to recompute the `> 50%` denominator over all rows. A rule that reasons over a stale enum under-reports in proportion to how fast the enum grows.
4. Classify the five new causes against the `> 50%` agent-initiated-re-dispatch threshold explicitly. `task_batch_complete` and `step_complete` look like clean terminations and should probably be excluded like `budget_yield`; `blocked_user_review` and `blocked_session_restart` are neither clean nor agent-initiated and need their own treatment.

## Evidence

- `manage-metrics.py record-dispatch-boundary --help` — eleven `--termination-cause` choices
- `manage-metrics/SKILL.md` § `record-dispatch-boundary` and § `## Canonical invocations` — six values, twice
- `work/metrics-dispatch-boundaries-{4-plan,5-execute,6-finalize}.toon` — ten rows, five carrying `task_batch_complete` or `step_complete`
- aspect: log_analysis — `dispatch_boundaries.*.unknown_count: 0` (the reader recognises the new values; only the docs do not)
- aspect: logging_gap_analysis — `enum_divergence.undocumented_choices[5]`
- `plan-retrospective/references/logging-gap-analysis.md` § DISPATCH_TERMINATION_CAUSE — "over the canonical value set"
