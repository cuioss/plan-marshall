envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:14:40Z

# Candidate lesson: zero cache/billing attribution — 0 of 14 dispatch-boundary rows carry the four context-load columns

**Component**: `plan-marshall:manage-metrics`
**Source signal**: plan-retrospective report for `dual-homed-hook-install-renders-identically`
**Suggested category**: bug

## Claim

The dispatch-boundary ledger records `total_tokens` per terminated dispatch, but **not a single row** on this plan carries the four context-load columns (cache-read / cache-creation / input / output). The population is fully enumerated and the count is a clean zero: `boundary_rows: 14`, context-load-bearing rows: `0`.

## Why a bare `total_tokens` is the wrong instrument

The project's own standing measurement (memory: TOKEN ROADMAP REV 7) is that `cache_read` is ~73–76% of billing weight and `output` ~1.1% — i.e. **~99% of billing weight is context, not generation**. A ledger that records only `total_tokens` therefore records the *least* actionable decomposition available: it cannot distinguish a dispatch that was expensive because it re-read a large resident context from one that was expensive because it generated a lot, and those two have opposite remedies.

This is the direct blocker on the `code-intelligence-substrate` epic's central finding (the average byte is re-read ~44.6x; cost is `resident_context x turns`). That analysis had to be reconstructed from published billing sums because the per-dispatch ledger the system already writes cannot answer it.

## Why the zero is worth filing rather than shrugging at

`total_tokens` being present makes the gap invisible. Every boundary row looks populated and well-formed; nothing reports "this row carries no attribution". A consumer summing the column gets a plausible number and no signal that the decomposition it would need is absent — the same *complete-looking partial* shape as the sibling candidate on ledger pairing.

## Suggested directive (for the orchestrator to judge)

1. **Record the four columns at `record-dispatch-boundary`.** The subagent `<usage>` payload the accumulator already consumes carries them; the boundary writer drops them. This is a widening of an existing write, not new instrumentation.
2. **Make an unattributed row say so.** A row written before the widening lands, or by a path with no `<usage>` available, must carry an explicit `attribution: absent` rather than silently omitting four columns — otherwise a mixed ledger sums a subset and reports it as a whole.
3. **Size the lever before staging the work.** Standing rule from the CIS epic: a change is staged with a measured size, not an assumed one. State what fraction of dispatches actually surface `<usage>` before committing to a schema change; a widening that populates 30% of rows produces a *new* partial-coverage instrument.

Cross-reference: this is the substrate `code-intelligence-substrate` WS-06 needs, so the orchestrator should check whether it belongs to that epic rather than to `truthful-signals` before staging it.
