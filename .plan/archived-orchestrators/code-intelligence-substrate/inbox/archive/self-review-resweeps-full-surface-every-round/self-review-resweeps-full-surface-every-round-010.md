envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:24:14Z

component=plan-marshall:manage-metrics
category=improvement
bundle=plan-marshall
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
source_aspects=logging-gap-analysis,log-analysis

# DISPATCH_TERMINATION_CAUSES has no member for returned-with-findings, so 5 productive rounds are stamped error

`work/metrics-dispatch-boundaries-6-finalize.toon` for PR #1126:

```text
2026-08-09T00:48:38Z,error,250626,...   <- self-review round 1: found 5 defects, returned
2026-08-09T01:08:07Z,error,279701,...   <- round 2: found 5, returned
2026-08-09T01:19:40Z,error,200373,...   <- round 3: found 2, returned
2026-08-09T01:30:14Z,error,233141,...   <- round 4: found 3, returned
2026-08-09T01:45:37Z,error,284719,...   <- round 5: found 4, returned
2026-08-09T01:57:22Z,step_complete,279636,... <- round 6: clean, done
```

Five of the six rounds are stamped `termination_cause=error` — **the same token the taxonomy reserves for "the dispatch raised a fatal error"**. Every one of those five did its job: found defects, filed Q-Gate findings, returned for a loop-back.

The accepted set (`voluntary_checkpoint`, `task_complete_returned_verbatim`, `budget_yield`, `harness_cancellation`, `error`, `clean_exit_queue_empty`, `step_complete`, `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned`) has **no member expressing "returned with findings"**, so the loop-back path has nowhere honest to land and falls to `error`.

## Root cause

The taxonomy models how a dispatch *stopped* (voluntarily, cancelled, crashed, queue-empty) but not the *verdict* a review-shaped dispatch returns. A findings-bearing return is a success of the step and a non-completion of the loop, and only the second half has a token.

## Solution

Add a `returned_with_findings` (or `loop_back`) member and route the finalize loop-back path to it. `mark-step-done` already has a `loop_back` outcome with a `--loop-back-target` classifier; the dispatch ledger has no counterpart.

## Impact

Two concrete losses:

1. **`error` is unusable as a health signal in `6-finalize`.** Any audit counting failed dispatches on this plan finds 5 of 12 and would reasonably conclude the finalize was unstable. It was not.
2. **The one rule that reads this file cannot see it anyway.** The `DISPATCH_TERMINATION_CAUSE` logging-gap rule is scoped to `metrics-dispatch-boundaries-5-execute.toon` only. The 6-finalize file — 12 rows, 2,507,354 tokens, 51% of this plan — is read by no rule at all. Widening the taxonomy without widening the rule's scope fixes only half of it.

Same shape as the neighbouring `budget_yield` carve-out already documented in `logging-gap-analysis.md`: a deterministic, legitimate termination was being counted as the agent-initiated-re-dispatch failure mode until it got its own member. This is the next instance of that same lesson.
