envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:05:43Z

# Candidate lesson: a per-state population with section-wide assertions checks nothing per state

- source_signal: automatic-review / CodeRabbit inline (PR #1488)
- record_id: 3c5025 (comment PRRC_kwDOQ3xasM7uheEJ)
- file: test/plan-marshall/phase-6-finalize/test_loop_back_outcome.py:79
- resolution: fixed via TASK-023 — structured state-to-outcome declaration added, population derived from it, routing asserted per state

## What happened

`_NON_CLOSE_STATES` was the only per-state population, but the `loop_back` and `--outcome done` checks ran ONCE for the entire section, and nothing excluded `failed` for each state. Verified exactly as described: the per-state loop only checked that each state is NAMED. A fourth state could therefore bypass per-state routing checks entirely. The workflow provided only prose and a `{state}` placeholder — no authoritative structured mapping to derive from.

## Candidate rule

Iterating over a population and then asserting once outside the loop is N passing checks of one assertion, not N assertions. Every property the test claims per member must be asserted inside the loop — and when the source document offers no structured mapping, ADD one rather than hand-maintaining the population next to a prose claim.
