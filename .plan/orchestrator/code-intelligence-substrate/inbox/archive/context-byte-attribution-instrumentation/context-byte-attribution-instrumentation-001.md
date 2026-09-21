envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:40:46Z

# Populate the four per-dispatch context-load columns or drop them

component: plan-marshall:manage-metrics
category: bug
confidence: high
source_plan: context-byte-attribution-instrumentation
source_pr: 1086

## Context

`record-dispatch-boundary` carries four context-load columns — `input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens`. Across this plan's entire lifecycle, all
**15** dispatch-boundary rows in all four phase files recorded `0` for all four columns.

This is the plan whose stated objective was context-byte attribution. Its own per-dispatch
attribution measured nothing.

## Root cause

The columns have no producer. A population-derived whole-tree content sweep (`architecture search
--content`, 4227 files scanned) finds `--cache-read-input-tokens` in exactly three files:
`manage-metrics/SKILL.md`, `manage-metrics/standards/data-format.md`, and
`manage-metrics/scripts/manage-metrics.py`. Every real call site — `phase-5-execute/SKILL.md`,
`phase-6-finalize/SKILL.md`, `plan-marshall/workflow/execution.md` — invokes
`record-dispatch-boundary` without them, so `default 0` is the only reachable value.

This is not a sampling claim: the flag appears in zero caller files out of the whole tree.

## Proposed action

Either (a) forward the four `message.usage` fields at every `record-dispatch-boundary` call site so
the columns carry real data, or (b) delete the columns. Shipping four always-zero columns that a
downstream reader will reasonably interpret as "this dispatch consumed no context" is worse than not
having them — it is a confident number with a hidden caveat, the exact archetype this epic exists to
eliminate.

If (a), note that `record-dispatch-boundary` is invoked by the ORCHESTRATOR after a dispatch returns,
so the four fields must come from the returning agent's usage envelope, not from the orchestrator's own.

## Evidence

- aspect: execution_context_dispatch_audit — 17 `[DISPATCH]` lines, 15 boundary rows, all four context columns zero on every row
- aspect: log_analysis — raw `work/metrics-dispatch-boundaries-6-finalize.toon` confirms zeros at the storage layer, not a parser artifact
- aspect: request_result_alignment — the plan shipped per-PHASE attribution while the sibling per-DISPATCH attribution stayed structurally unpopulatable
