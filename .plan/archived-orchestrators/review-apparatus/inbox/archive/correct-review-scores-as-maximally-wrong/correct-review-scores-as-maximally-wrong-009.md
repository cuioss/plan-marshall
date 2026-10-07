envelope_version=1
sender_type=plan
sender_id=correct-review-scores-as-maximally-wrong
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T14:07:03Z

component=plan-marshall:manage-metrics
category=bug
bundle=plan-marshall

# A closed phase row is never re-opened on finalize loop-back, so 61% of this run's spend is invisible

## What happened

`metrics.toon` closed `[5-execute]` **once**, at 07:30:13, with `total_tokens: 162906`.

The plan then looped back from `6-finalize` into `5-execute` **three more times** — TASK-004 (08:11),
TASK-005 (08:55), TASK-006 (11:33) — each with an explicit
`[MANAGE-STATUS] Phase: 6-finalize -> 5-execute` transition in `work.log`.

Those three re-entries spent a further **758,059 tokens**. No phase row ever absorbed them. They exist
only in `work/metrics-dispatch-boundaries-5-execute.toon`, which correctly records all 6 dispatch rows:

```
07:15:30 voluntary_checkpoint          162906
07:30:11 clean_exit_queue_empty             0
08:28:02 voluntary_checkpoint          297620
08:42:08 clean_exit_queue_empty             0
09:01:37 task_complete_returned_verbatim 151183
12:22:39 voluntary_checkpoint          309256
                                   = 920,965
```

## The numbers

| Source | Total tokens |
|--------|-------------:|
| `metrics.md` as generated | 1,571,619 |
| Reconstructed floor (phase rows + dispatch-boundary sum + 6-finalize accumulator) | **4,077,004** |

**61% of the run's token spend is absent from the metrics report.**

## The part that makes it dangerous

`metrics.md` carries the floor-not-truth partiality marker:

> Partial: unrecorded phases — 6-finalize

It names **only** `6-finalize`. The `5-execute` row is presented as a closed, complete, authoritative
`162,906` — while being an **82% under-count** of that phase's real 920,965.

The partiality contract keys "recorded" solely off the presence of an `end_time`. A phase that was
closed and then re-entered has an `end_time`, so it passes the completeness test while being wrong.
The marker therefore under-reports its own incompleteness — a confident signal hiding the caveat.

## Also broken: the 5-execute accumulator

`work/metrics-accumulator-5-execute.toon` reads `total_tokens: 0, tool_uses: 0, samples: 1` despite
six recorded dispatch boundaries. The accumulator fallback path would have contributed nothing even if
`end-phase` had consulted it.

## Root cause

Phase closure is modelled as a one-shot terminal event. The finalize loop-back re-enters a phase that
the model believes is finished, and nothing re-opens the row or appends a re-entry record.

## Proposed action

1. **Re-open on loop-back.** On the `6-finalize -> 5-execute` transition, call a metrics verb that
   re-opens the closed row (or appends a keyed re-entry row) so loop-back spend lands in a phase bucket.
2. **Cross-check against the dispatch-boundary file.** The ground truth is already on disk. Extend
   `generate`'s partiality verdict: when a phase's dispatch-boundary **row count exceeds its
   `close_count`**, mark that phase partial too — not only phases missing `end_time`. This is a
   population-derived check, not a spot-check: it fires for any phase, not just the one seen here.
3. **Fix the accumulator.** Investigate why `accumulate-agent-usage` recorded `samples: 1` with zero
   values for a phase that produced six dispatch boundaries.

## Evidence

- `work/metrics.toon` `[5-execute] total_tokens: 162906`, `close_count: 1`
- `work/metrics-dispatch-boundaries-5-execute.toon` — 6 rows summing to 920,965
- `work/metrics-accumulator-6-finalize.toon` — `total_tokens: 1747326, samples: 11`
- `work/metrics-accumulator-5-execute.toon` — `total_tokens: 0, samples: 1`
- `metrics.md` — `> Partial: unrecorded phases — 6-finalize` (5-execute not named)
- aspect: plan-efficiency — `[BUDGET]` error anchor tripped at 4.08M against a 1.3M
  `single_module+bug_fix` error threshold
