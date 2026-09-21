envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T13:10:59Z

component=plan-marshall:manage-metrics
category=bug
created=2026-07-29
bundle=plan-marshall

# Re-open the phase metrics window on loop-back re-entry

`status.metadata.loop_back_reentry` records a `6-finalize -> 5-execute` re-entry at
`2026-07-29T07:48:24Z`, and a fourth 5-execute dispatch consumed **186,858 tokens / 56 tool uses**
at `08:01:28`. `work/metrics.toon` nonetheless still carries:

```
[5-execute]
  end_time: 2026-07-29T05:00:46Z
  total_tokens: 913908
```

913,908 is exactly the sum of the three 5-execute dispatch-boundary rows that existed *before* the
loop-back. The phase window was closed at 05:00:46, the loop-back re-entered the phase, more work
ran, and the window was never re-opened — so the post-loop-back round is invisible to the phase
totals.

`metrics.md` then prints, above the table:

> Partial: unrecorded phases — 6-finalize

which asserts that 1-through-5 are complete and recorded. 5-execute is not.

Separately, `record-dispatch-boundary` stopped emitting entirely after `07:36:42`:
`work/metrics-dispatch-boundaries-6-finalize.toon` holds 6 rows while at least five further
6-finalize dispatches ran afterwards (automatic-review re-fire 08:23:49, verification-feedback
08:32:38, review-retrospective 09:34:41, lessons-capture 09:41:01, plan-retrospective 12:54:45).

## Solution

- On `loop_back_reentry`, re-open the target phase's metrics window (clear `end_time`, keep the
  accumulated totals) so the re-entered round accumulates into the same phase row.
- Make the `partial:` / `unrecorded_phases` caveat derive from a real completeness check —
  "does any dispatch-boundary row postdate this phase's `end_time`?" — rather than from
  "does this phase have an `end_time` at all". A phase with a stamped end_time and later rows is
  precisely the case the current caveat cannot express.
- Restore `record-dispatch-boundary` emission across the loop-back so the finalize tail is
  recorded at all.

## Impact

`metrics.md` under-reports this run by roughly 40 percent (1,958,168 reported vs ~3,263,376
reconstructed) while displaying a caveat that names the wrong phase. Any consumer reading the
Phase Breakdown table — the finalize `print-phase-breakdown` step, the token-economics and
exploration-share audit checks, the lane-lever effectiveness measurement arm — reads a confident
per-phase number that is false for every plan that takes a loop-back. This is the epic theme
applied to the measurement substrate itself: the numbers the epic uses to grade its own work are
produced by a counter that stops counting at the exact moment a run becomes interesting.

## Evidence

- `work/metrics.toon` `[5-execute] end_time 05:00:46 / total_tokens 913908` vs
  `work/metrics-dispatch-boundaries-5-execute.toon` row `2026-07-29T08:01:28Z,clean_exit_queue_empty,186858,56`.
- `status.metadata.loop_back_reentry.at = 2026-07-29T07:48:24Z`.
- `metrics.md` line 7: `> Partial: unrecorded phases — 6-finalize`.
- `work/metrics-dispatch-boundaries-6-finalize.toon` — 6 rows, last `07:36:42`; five later
  `[DISPATCH]` lines in `logs/work.log` have no matching row.
