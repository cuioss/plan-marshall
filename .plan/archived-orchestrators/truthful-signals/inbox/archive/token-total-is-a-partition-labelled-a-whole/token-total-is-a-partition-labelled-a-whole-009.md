envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:54:21Z

component=plan-marshall:manage-metrics
category=bug
bundle=plan-marshall

# A re-entered phase row accumulates some fields and replaces others, producing an impossible row that `partial: false` certifies as complete

## What was observed

`work/metrics.toon` for this plan records `5-execute` as:

```toon
[5-execute]
  start_time: 2026-08-03T09:22:33Z
  end_time: 2026-08-03T10:00:14Z
  duration_seconds: 41973.0
  close_count: 3
  agent_duration_ms: 0
  agent_duration_seconds: 0.0
  total_tokens: 1961416
  tool_uses: 0
```

Three mutually inconsistent facts in one row:

1. **`total_tokens: 1961416` alongside `tool_uses: 0` and `agent_duration_ms: 0`.** A phase cannot consume ~2M dispatched tokens in zero tool uses over zero milliseconds. The previously-rendered `metrics.md` (generated between close 2 and close 3) shows `tool_uses: 753` and `total_tokens: 1,923,639` for the same phase. So across the third close, `total_tokens` **accumulated** (+37,777) while `tool_uses` and `agent_duration_ms` were **replaced with the closing call's zeros**.
2. **`duration_seconds: 41973` (11h39m) contradicts its own stored span.** `end_time - start_time` is 37m41s (2,261s). `duration_seconds` is a sum across all three closes; `start_time`/`end_time` are the last close only. Two different quantities, same row, no field distinguishing them.
3. **`start_time` is later than the end time the report renders.** `metrics.md` rendered `5-execute` with `Start: 2026-08-03T09:22:33Z` and `End: 2026-08-03T07:05:28Z` — a phase that ends 2h17m before it starts.

## Why the existing guard does not see it

`metrics.toon` states `partial: false` and `unrecorded_phases:` empty. The floor-not-truth partiality verdict is documented to key a phase's *recorded* status solely off the presence of an `end_time` marker. `5-execute` has an `end_time`, so it is "recorded" — and the row is certified complete while being internally impossible.

This is the epic archetype in its purest form: the completeness signal is real, correctly implemented against its stated rule, and answers a narrower question than the one a reader takes it to answer. `partial: false` means *"every phase has a closing marker"*; readers take it to mean *"these numbers are trustworthy"*.

## The conflicting contracts

The two documented behaviours genuinely disagree, which is the root cause rather than a coding slip:

- `end-phase` documents **replace** semantics: *"Calling `end-phase` multiple times for the same phase replaces the previous end data (does not accumulate)."*
- The re-entry feature documents **accumulate** semantics: `metrics.md` renders *"Re-entered phases: 5-execute. Totals for these phases are the sum across every close (close_count > 1)."*

The implementation does both, per field, and no document states which fields take which path.

## The generalisable rule

**When a record can be written more than once, every field needs a declared merge policy — and a row whose fields use different policies must not be summarised by a single completeness flag.**

Three checks worth making standing practice:

1. **State the merge policy per field, not per verb.** A `close_count > 1` row should be self-describing: either all fields accumulate, or the accumulated ones are named separately from the last-close ones (e.g. `duration_seconds_total` vs `last_close_duration_seconds`).
2. **Add a coherence assertion, not just a presence assertion.** `total_tokens > 0 AND tool_uses == 0` is a cheap, deterministic impossibility check; so is `end_time < start_time`. Presence checks cannot detect either.
3. **A completeness flag must name the question it answers.** `partial: false` should read as `all_phases_have_closing_marker: true` — the honest narrower claim — so a reader does not upgrade it to a correctness guarantee.

## Impact

Any plan whose execute phase is re-entered — which is every plan that checkpoints, yields on budget, or resumes across sessions; this one closed `5-execute` three times — carries a `5-execute` row with zeroed tool/duration fields and a `duration_seconds` that contradicts its own timestamps. Because `partial: false`, downstream consumers have no signal to distrust it, and the corrupted `tool_uses` feeds the retrospective's efficiency ratios directly.
