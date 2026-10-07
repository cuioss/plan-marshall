envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:23:30Z

component=plan-marshall:manage-metrics
category=anti-pattern
created=2026-07-29

# manage-metrics SKILL.md documents 6 of 11 termination_cause values, and this plan rewrote that file without fixing it

`record-dispatch-boundary`'s real argparse enum has **11** values:

```
voluntary_checkpoint, task_complete_returned_verbatim, budget_yield,
harness_cancellation, error, clean_exit_queue_empty,
step_complete, blocked_user_review, blocked_session_restart,
task_batch_complete, agent_returned
```

`manage-metrics/SKILL.md` documents **6** — the first six — and states, emphatically, that the flag is "Required — missing or unrecognised values are rejected as script errors (there is no implicit fallback)". A reader who trusts the SKILL would conclude the other five are rejected. They are accepted.

## The sharp edge

The two values this plan's own boundary files actually contain are **both** undocumented:

- `step_complete` — all 6 rows of `metrics-dispatch-boundaries-6-finalize.toon`
- `task_batch_complete` — the single row of `metrics-dispatch-boundaries-4-plan.toon`

So 7 of this plan's 10 recorded boundary rows carry a `termination_cause` that its own SKILL says cannot exist. The `logging-gap-analysis` reference compounds it: its DISPATCH_TERMINATION_CAUSE rule tells the analyst to report "the per-cause distribution over the canonical value set" and then enumerates only the 6 documented values, so an analyst following the reference literally would emit a distribution that omits the only causes present.

## Why this is filed as a recurrence, not a first sighting

`project:finalize-step-lessons-housekeeping` recorded during this very run (decision `63e5e7`):

> "Only component match is lesson 2026-07-27-08-006 (manage-metrics, unrelated termination-cause doc drift)."

So a lesson for manage-metrics termination-cause doc drift **already exists**, was surfaced during this plan's finalize, and was dismissed as "unrelated" — it was judged against this plan's deliverable scope rather than against the file the deliverable was about to rewrite.

## Root cause

Two compounding factors. The enum grew by five values and the prose count was never re-derived (the count-prose-staleness archetype). And the Boy Scout Rule did not reach it: deliverable 1 rewrote `manage-metrics/SKILL.md` end to end — replacing the `end-phase` Idempotency line, extending the `phase-boundary` paragraph, extending the `generate` Output block, and adding `close_count` to the `metrics.toon` example — while the stale enum sat in the same document, in the section describing the very artifact the plan was fixing the accounting for.

## Suggested corrective action

1. Correct the enum in `manage-metrics/SKILL.md` to all 11 values, and correct the "rejected as script errors" sentence so it describes the real accepted set.
2. Correct the enumeration in `plan-retrospective/references/logging-gap-analysis.md` DISPATCH_TERMINATION_CAUSE so the "canonical value set" it names matches argparse.
3. Reconcile with existing lesson `2026-07-27-08-006` rather than filing a parallel one — this is its second observation, and its recurrence is evidence the lesson needs enacting, not restating.
4. Generalizable guard: an enum documented in prose alongside an argparse `choices` list is a count-and-membership claim about a set. Pin it with a test that asserts the documented value list equals the parser's `choices` tuple, the same way the dispatch-roster closure test pins the step rosters.
