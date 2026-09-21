envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:36:26Z

# Document all 11 --termination-cause values, not 6

component: plan-marshall:manage-metrics
category: anti-pattern
confidence: high
source: plan-retrospective (aspect: logging-gap-analysis)
suggested_epic: truthful-signals (documented index under-enumerates the set it indexes)

## Context

`manage-metrics record-dispatch-boundary --termination-cause` declares ELEVEN argparse choices:

```
voluntary_checkpoint, task_complete_returned_verbatim, budget_yield,
harness_cancellation, error, clean_exit_queue_empty, step_complete,
blocked_user_review, blocked_session_restart, task_batch_complete, agent_returned
```

Two documentation surfaces each enumerate only the first SIX and present that subset as closed:

- `manage-metrics/SKILL.md` — the `record-dispatch-boundary` Operations block AND the `## Canonical invocations` block, both showing a 6-member brace expansion.
- `plan-retrospective/references/logging-gap-analysis.md` § DISPATCH_TERMINATION_CAUSE — calls the 6 "the canonical value set" and instructs the LLM to emit a per-cause distribution over it.

This plan's own recorded rows use `step_complete` (x9, all of 6-finalize) and `task_batch_complete` (x1, 4-plan). Both are valid. Neither appears in any documented index, so the retrospective's distribution finding silently mis-buckets 10 of the run's 14 dispatch rows.

## Root cause

Five values were added to the argparse enum without the corresponding index rows being added in the same change. This is a direct instance of the standing rule in `persona-plan-marshall-agent/standards/agent-behavior-rules.md` § Workflow Discipline: *"A newly-authored index/summary table must enumerate every member of the set it indexes... When you add a member to the indexed set, add its index row in the SAME change."* The omission is invisible at the index site — a 6-value brace expansion reads as complete.

The SKILL.md prose makes it worse than a stale list: it asserts "missing or unrecognised values are rejected as script errors (there is no implicit fallback)", which invites a reader to treat the printed 6 as exhaustive.

## Proposed action

1. Update both `manage-metrics/SKILL.md` blocks to all 11 values, and document what each of the 5 undocumented ones means (particularly `step_complete` vs `task_batch_complete` vs `agent_returned`, which are not self-explanatory).
2. Update `plan-retrospective/references/logging-gap-analysis.md` DISPATCH_TERMINATION_CAUSE to the same 11, and re-derive which values count toward the ">50% agent-initiated re-dispatch" threshold — `step_complete` and `task_batch_complete` are almost certainly NOT agent-initiated re-dispatch, so the current rule may be counting a clean denominator against a mis-specified numerator.
3. Add a test that derives the documented value set FROM the argparse `choices` tuple rather than from a literal, so the next enum addition breaks the test instead of the docs.

## Evidence

- `python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary --help` — 11 choices
- `work/metrics-dispatch-boundaries-4-plan.toon` — 1 row, `task_batch_complete`
- `work/metrics-dispatch-boundaries-6-finalize.toon` — 10 rows, 9x `step_complete` + 1x `error`
- `manage-metrics/SKILL.md` — 6-value brace expansion in two places
