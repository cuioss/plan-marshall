envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:22:33Z

component=plan-marshall:manage-metrics
category=bug
created=2026-07-29

# The dispatch-boundary audit trail under-reports finalize in two independent ways, and both read as measured zero

`record-dispatch-boundary` is the append-only audit trail `plan-retrospective` correlates against `[OUTCOME]`-log coverage. In this plan's 6-finalize it is incomplete on two separate axes.

## Axis 1 — three dispatched steps never got a row

`work/metrics-dispatch-boundaries-6-finalize.toon` holds **6 rows**. `work/metrics-accumulator-6-finalize.toon` holds **9 samples**. The gap is arithmetically exact, not inferred:

| Source | total_tokens |
|--------|-------------:|
| 6 recorded boundary rows summed | 715,271 |
| accumulator | 1,148,682 |
| **difference** | **433,411** |

And 433,411 = 226,123 (`automatic-review` re-fire) + 91,865 (`project:finalize-step-review-retrospective`) + 115,423 (`lessons-capture`) — the exact three steps whose `execution.toon` `execution_log` rows carry tokens but have no matching boundary row. So the dispatch-boundary trail under-reports finalize dispatch by 38% of its own token volume, and the three missing steps are identifiable to the token.

Every one of those three steps DID call `accumulate-agent-usage` (that is why the accumulator has 9 samples). So the two recorders sit at the same call sites and only one of them fired. This is the unchecked-persist/missing-second-call shape: two writes that must happen together, one of which is silently optional in practice.

## Axis 2 — the four context-load columns have no producer at all

Every row of every boundary file in this plan carries `0` for all four per-dispatch context-load columns:

```
rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}
2026-07-29T15:02:11Z,step_complete,79627,22,156950,0,0,0,0
...
```

That is 10 rows across 3 phases (4-plan 1, 5-execute 3, 6-finalize 6), all four columns zero. The flags exist (`--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens`) and default to 0; no call site anywhere passes them. The schema documents them as "the per-DISPATCH counterpart to the per-PHASE four-field view `enrich` writes", but the counterpart is never written.

A column that defaults to 0 and has no producer is indistinguishable, at read time, from a genuinely-measured zero. A consumer computing cache-read share per dispatch gets 0% and no signal that the facet was never captured.

## Impact

`plan-retrospective`'s DISPATCH_TERMINATION_CAUSE rule and the corpus-level dispatch-topology audit both read this file as the authoritative dispatch inventory. With 6 of 9 finalize dispatches absent and the entire context-load facet producerless, both audits are reasoning over a partial trail that presents itself as complete — the file carries no `partial` marker analogous to the one `manage-metrics generate` emits for unrecorded phases.

## Suggested corrective action

1. Fuse the two recorder calls at the finalize dispatch-return site so `record-dispatch-boundary` cannot be omitted while `accumulate-agent-usage` fires — or, better, have the boundary recorder be the single write and derive the accumulator from it, removing the divergence surface entirely. Then add a test that asserts, for a plan with N token-bearing `execution_log` rows in a phase, the boundary file for that phase has N rows.
2. Either populate the four context-load columns at every call site, or emit them as an explicit absent marker rather than `0`. Apply the same floor-not-truth treatment `generate` already uses: a boundary file that is missing rows or columns should say so in-band.
3. Add a `samples`-versus-`rows` reconciliation check to `analyze-logs` so this divergence is caught by the retrospective automatically instead of by hand arithmetic, as it was here.
