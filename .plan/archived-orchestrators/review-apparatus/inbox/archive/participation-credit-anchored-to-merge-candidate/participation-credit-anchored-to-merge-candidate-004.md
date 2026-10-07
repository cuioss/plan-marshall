envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T21:18:46Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_plan=participation-credit-anchored-to-merge-candidate
source_pr=1349

# Finalize yielded control five times with no operator question pending

## Context

The session transcript reduces to 11 operator turns. Six are genuine gate answers
(scope split, domain set, execution posture, outline defects, outline proceed, merge
mutex). The other five are the operator restarting a run that had stopped for no stated
reason:

```
user: why did you stop?
user: continue with finalize. Do not step before the end
user: continue without further stopping
user: why did you stop?
user: why did you stop?
```

Two of those are not questions being answered at all — they are standing instructions,
and the operator had to issue the same instruction twice ("Do not step before the end",
then "continue without further stopping"). A standing instruction that must be reissued
is evidence the yield points are not conditioned on operator input in the first place.

The dispatch ledger corroborates the shape. `6-finalize` recorded 8 dispatch
terminations, of which two did not complete a step:

| termination_cause | tokens | tool_uses |
|---|---:|---:|
| `error` | 214,886 | 46 |
| `blocked_session_restart` | 189,719 | 37 |

That is 404,605 tokens — 11.4% of the run's entire 3,547,890 dispatched total — spent on
dispatches that produced no step completion. `5-execute` additionally shows one
`voluntary_checkpoint` (428,709 tokens).

The cost is not only tokens. `6-finalize` spans 16:04:43Z to roughly 21:05Z — about
4h50m of wall clock — of which only 59m30s is agent-worked time. Some of that gap is
legitimate and unavoidable (CI waits, the ~30-minute merge-queue FIFO budget, the queue
landing poll). But the "why did you stop?" turns are gaps that ended only when a human
noticed and prodded, and nothing bounds those.

## Root cause

Three distinguishable stop shapes are being conflated into one operator experience:

1. A genuine operator gate (the merge-mutex escalation) — correct, and it asked a real
   question with real options.
2. A `blocked_session_restart` — a real constraint, but one that terminated a dispatch
   holding 189,719 tokens of context and required a human to restart it.
3. Bare yields with no question — the "why did you stop?" cases, where the run simply
   stopped mid-finalize.

Only shape 1 is legible to the operator. Shapes 2 and 3 present identically: the run is
idle and the operator has no way to tell whether it is waiting on them, waiting on CI,
or has simply stopped. The absence of a question is not visible as an absence.

## Proposed action

1. **Never yield without a question or a stated wait.** When finalize stops, it should
   either fire an `AskUserQuestion`, or emit a work-log line naming what it is waiting
   on and its budget. A stop with neither is the defect.
2. **Make the standing instruction stick.** "continue without further stopping" was
   issued and then had to be issued again. Whatever consumes that instruction is not
   surviving the dispatch boundary; it should be recorded in plan state, not carried in
   context.
3. **Report non-completing dispatch spend at finalize close.** The ledger already
   distinguishes `error` and `blocked_session_restart` from `step_complete`, and
   `analyze-logs` already sums `error_total_tokens` (214,886) and
   `retryable_total_tokens` (189,719). Surface that pair in the finalize summary so an
   11% non-completion spend is visible in the run rather than only in a retrospective.

## Evidence

- transcript: `extract-chat-signal` reduced transcript — 11 operator turns, 6 gate
  decisions, 5 unprompted restarts quoted above.
- aspect: log_analysis — `6-finalize` dispatch rows including `error` (214,886) and
  `blocked_session_restart` (189,719); `error_total_tokens: 214886`,
  `retryable_total_tokens: 189719`.
- artifact: `metrics.md` — `6-finalize` worked 59m30s; phase opened 16:04:43Z, last
  dispatch boundary 21:05:00Z.
- counter-example worth preserving: the merge-mutex escalation named the holding plan,
  the exhausted budget and the attempt count, and stated it could not establish holder
  liveness from inside the worktree. That is the shape every stop should have.
