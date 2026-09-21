envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:23:04Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=finalize-step-contract-guard-residue

# Forward the four context-load flags that record-dispatch-boundary already accepts

## Context

`manage-metrics record-dispatch-boundary` declares four optional context-load flags — `--input-tokens`, `--output-tokens`, `--cache-read-input-tokens`, `--cache-creation-input-tokens` — the per-dispatch counterpart of the four-field view `enrich` writes per phase. They are deliberately defaultless: an omitted flag writes the literal `unmeasured` so "the caller passed no measurement" stays distinguishable from "the dispatch loaded zero context".

Across this plan, **all 11 recorded dispatch rows** carry `unmeasured` in all four columns:

```
context_position_cost:
  total_rows: 11
  measured_rows: 0
  unmeasured_rows: 11
  position_multiple: unmeasured
```

The recorder behaved correctly and the reader reported honestly. The measurement simply never happened, on any dispatch, in either phase that recorded boundaries.

The cost is that per-dispatch billing attribution is blank plan-wide. Combined with the terminal-phase enrich gap, the plan's dominant cost centre — `6-finalize`, 2,635,188 dispatched tokens over 10 dispatches — has neither per-phase nor per-dispatch context-load attribution.

## Root cause

A caller-side omission, not a missing capability. The dispatcher has the dispatched agent's `<usage>` totals in hand at the moment it calls `record-dispatch-boundary` — it already forwards `--total-tokens`, `--tool-uses` and `--duration-ms` from the same envelope — and simply does not forward the four-field view alongside them.

## Proposed action

At every `record-dispatch-boundary` call site, forward the four `message.usage` fields from the returning agent's envelope alongside the totals already passed. This is the cheapest of the measurement gaps this retrospective found: the data is present at the call site, the flags exist, and the reader already handles them.

Once wired, `position_multiple` becomes computable and the per-dispatch half of token attribution stops being blank.

## Evidence

- aspect: log_analysis — `context_position_cost.measured_rows: 0` of `total_rows: 11`, `position_multiple: unmeasured`
- aspect: log_analysis — every row's `unmeasured_columns` lists all four fields, `unrecognised_columns` and `indeterminate_columns` both empty
- source: `manage-metrics/SKILL.md` record-dispatch-boundary — the four flags are declared and documented as defaultless
- aspect: llm_to_script_opportunities — candidate 5, complexity low
