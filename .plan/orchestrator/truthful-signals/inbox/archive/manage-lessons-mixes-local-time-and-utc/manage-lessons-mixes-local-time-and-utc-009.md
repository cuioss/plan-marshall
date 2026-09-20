envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T18:07:27Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-07-29

# The dispatch-evidence channel that the dispatch audit enforces was only 64% populated on this plan

The execution-context dispatch audit asserts, in the inverse direction, that every step classified DISPATCHED actually *was* dispatched. Its sole evidence is the `[DISPATCH]` work-log line. On this plan that channel is incomplete:

- `[DISPATCH]` lines emitted: **9**
- `execution-context.{name} Complete` envelope completions observed: **14**

Five envelopes ran with no dispatch record at all:

| Envelope | Evidence it ran | `[DISPATCH]` line |
|---|---|---|
| `project:finalize-step-review-retrospective` | `7cea2f` Complete at 16:33:50; manifest records 72,510 tokens / 13 tool uses | absent |
| `lessons-capture` | `fe3ab1` Complete at 16:39:27; manifest records 89,398 tokens / 24 tool uses | absent |
| `automatic-review` (2nd fire) | `fbb1e9` Complete at 16:31:24 | absent |
| `automatic-review` (3rd fire) | `fbb1e9` Complete at 17:04:40 | absent |
| `automatic-review` (1st) | Complete at 15:35:40 | present (15:30:04) |

161,908 tokens of dispatched work — roughly 30% of finalize spend — left no dispatch evidence.

## Why it matters beyond bookkeeping

The audit's inverse-coverage half flags "step marked done with zero matching `[DISPATCH]` evidence" as *inline-where-dispatch-was-required*. On a channel this sparse that check cannot fire truthfully in either direction: a genuinely-inline step and a dispatched-but-unlogged step are indistinguishable. The detector is population-derived from a population it does not control, and nothing measures the channel's own completeness.

Re-fires are the specific gap: only the **first** dispatch of a step emits a line, so any loop-back or re-review re-entry is invisible.

## Solution

- Emit `[DISPATCH]` from the single dispatch seam so re-fires cannot bypass it, rather than from each step's prose.
- Have the audit report **channel completeness** (`dispatch_lines / envelope_completions`) alongside its findings, so a sparse channel downgrades the audit's own confidence instead of silently weakening its verdicts.

## Impact

Any conclusion the dispatch audit draws about inline-vs-dispatched execution is currently drawn over a 64%-populated evidence base, and the report presents those conclusions without that caveat.
