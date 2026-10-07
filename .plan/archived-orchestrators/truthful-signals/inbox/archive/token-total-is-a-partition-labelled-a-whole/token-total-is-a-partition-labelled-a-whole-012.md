envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:55:53Z

component=plan-marshall:manage-status
category=improvement
bundle=plan-marshall

# A gate that fired five times and found defects on three of them is recorded as "clean" — `phase_steps` is last-write-wins, so an eventful gate is indistinguishable from a first-pass-clean one

## What was observed

`pre-submission-self-review` ran **five times** during this plan's finalize. The work log records the sequence: iteration 4 at `10:33:19Z` — *"Complete - iteration 4 found 2 issues (fourth inline-trigger cascade site in data-format.md signature table)"* — and iteration 5 at `11:08:28Z` — *"iteration 5 closure pass clean at 234d8f97b"*. Three consecutive firings each found a real defect: a documentation cascade believed closed at 2 sites, then 3, then 4. Only the fifth pass enumerated the population rather than sampling it.

What survives in structured state is a single row:

```toon
pre-submission-self-review:
  outcome: done
  display_detail: "self-review clean: 204 candidates examined, no check matched"
```

`mark-step-done` overwrites the step's record on each call, so the terminal outcome replaces the history. Any consumer reading `phase_steps` — a retrospective, an audit, a preference emitter, a human — sees a gate that passed cleanly on what appears to be one pass. The three defect-finding firings exist only as free-text work-log lines that no structured consumer reads.

## The second problem in the surviving string

`204 candidates examined` is a **volume**, not a coverage figure. It records how much was looked at, not what share of the relevant population was covered — and the plan's own history proves the distinction was load-bearing: four of the five passes examined a large number of candidates and still missed a cascade site, because the passes sampled rather than enumerated. A number that grows with effort and is silent about completeness is the wrong summary for a coverage gate, and it is the only number that survives.

This is the `volume-read-as-coverage` archetype appearing in the plan's own finalize record.

## The generalisable rule

**When a step can run N times, its structured record must carry N and the per-firing outcomes — a last-write-wins field turns a struggle into a success story.**

Three checks worth making standing practice:

1. **Record iteration count and per-iteration outcomes.** `mark-step-done` should accumulate a `firings[]` list (or at minimum stamp `iteration_count` and `defects_found_total`) rather than replacing. The information exists at write time; only the schema discards it.
2. **A retry is signal, not noise.** Steps that needed 5 passes are the strongest available input to "which gates are under-specified" — precisely the question a retrospective and a preference emitter exist to answer, and precisely the data the current schema destroys. Note this plan's `finalize-step-preference-emitter` reported `0 gate dispositions recorded, no hints owed`, on a finalize with five gate firings and a full review loop-back.
3. **Report coverage, not volume, in a coverage gate's summary.** Prefer `enumerated 12/12 cascade sites` over `204 candidates examined`. If the denominator is unknown, say so — an honest `denominator unknown` is more useful than a large numerator.

## Impact

Applies to every re-runnable finalize step, and the loss is silent and total. This plan's finalize was unusually eventful — five self-review firings, one full review loop-back producing two fix tasks, four commits made during finalize — and its `phase_steps` record reads as an uneventful clean run throughout. Any cross-plan analysis of gate effectiveness built on `phase_steps` is reading only the last frame of every gate.
