envelope_version=1
sender_type=plan
sender_id=hook-timeout-unit-confusion
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:57:05Z

# HEAD-advance step re-fires emit no [STEP] bracket, under-reporting executions 5x

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_plan=hook-timeout-unit-confusion
source_pr=1131

## Context

The finalize FOR loop re-fires head-dependent steps whenever a fix commit advances HEAD. This run
did that three times (`self-review-fix` at 14:43Z, an unnamed second round, `self-review-fix-3` at
17:15Z) plus once more after the phase-5 loop-back. Observed execution counts, each evidenced by its
own `execution-context.{name}` STATUS Complete line in `logs/work.log`:

| Step | Actual executions | `[STEP]` brackets | `execution.toon` rows |
|---|---|---|---|
| `project:finalize-step-lessons-housekeeping` | 5 | 1 | 1 |
| `project:finalize-step-plugin-doctor` | 7 | 1 | 1 |
| `default:pre-submission-self-review` | 7 | 1 | 2 |

Every re-run returned the identical verdict — lessons-housekeeping reported
`0 removed, 0 promoted, 0 adapted, 19 retained` five times; plugin-doctor reported
`clean, 2 skills gated` seven times. At roughly 110K–250K tokens per dispatch that is on the order
of 2,000,000 tokens spent re-confirming unchanged verdicts, and **no artifact anywhere records that
these were re-fires**.

The `[STEP] Executing step:` / `Completed step:` bracket is emitted on the first execution only. The
work log therefore carries 16 `Executing` lines for a phase that executed its steps roughly 35 times.
`execution.toon`'s `execution_log` shares the same under-count rather than providing an independent
check on it.

## Root cause

The `[STEP]` bracket is emitted by the FOR-loop body at first entry, while the re-fire path is the
loop's *re-entry* branch after a HEAD advance. The re-entry branch re-dispatches the step (the
`[DISPATCH]` lines are present for most of them) but does not re-emit the step bracket, so the two
signals disagree about how many times the step ran and only the quieter one is used for counting.

## Proposed action

1. Emit the `[STEP] Executing step:` / `Completed step:` bracket on **every** execution, re-fires
   included, and carry the round ordinal in the line (`re-fire 3/3 at HEAD {sha}`).
2. Record the count structurally rather than only in prose: `mark-step-done` already accepts
   repeatable `--fact KEY=VALUE`, so a `re_fire_count` fact on the step record turns an invisible
   cost into a first-class number that `plan-retrospective` and the archived-plan audit can query
   without log archaeology. This is the mechanism the "display_detail is a rendering of recorded
   facts, not their sole record" contract was built for.
3. Consider whether a re-fire whose inputs are unchanged needs to run at all. `plugin-doctor` re-ran
   seven times over the same two skill dirs and returned the same clean verdict each time; its
   `head_at_completion` anchor is exactly the input needed to decide that cheaply.

## Evidence

- `logs/work.log` — `[STEP] Executing step:` appears 16 times, `Completed step:` 15 times, against
  ~35 envelope completions evidenced by `execution-context.*` STATUS lines.
- `logs/work.log` `14:56:17Z` — "Self-review fix committed as b1ea868ce - HEAD advanced past 8124d4b,
  re-entering the FOR loop: head-dependent steps (lessons-housekeeping, pre-push-quality-gate,
  plugin-doctor) re-fire, pre-submission-self-review retries". The loop *announces* the re-fire and
  then runs it without brackets.
- `execution.toon` `execution_log` — `pre-submission-self-review` twice, `project:finalize-step-lessons-housekeeping` once.
- `work/metrics-accumulator-6-finalize.toon` — `total_tokens: 4808218`, `tool_uses: 1022`,
  `samples: 22` for a phase whose step ledger shows 16 executions.
- aspects `logging_gap_analysis`, `execution_context_dispatch_audit`, `plan_efficiency`.

## Why this belongs to truthful-signals

Two ledgers (`[STEP]` lines and `execution.toon`) agree with each other and both disagree with
reality, which reads as corroboration. The agreement is not independent — they are fed from the same
emission point — so a consumer that cross-checks them gets a false confirmation of the under-count.
