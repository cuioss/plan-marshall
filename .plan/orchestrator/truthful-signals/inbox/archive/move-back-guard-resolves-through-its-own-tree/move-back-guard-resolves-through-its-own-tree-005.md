envelope_version=1
sender_type=plan
sender_id=move-back-guard-resolves-through-its-own-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T18:48:58Z

component=plan-marshall:manage-execution-manifest
category=bug
confidence=high
source_plan=move-back-guard-resolves-through-its-own-tree
source_pr=1361

# record-step writes placeholder zeros that are indistinguishable from a measured zero

## Context

All eight `execution_log` rows this plan recorded carry `total_tokens=0` and `tool_uses=0`, alongside durations that are visibly hand-rounded to the second (6000 / 6000 / 6000 / 8000 / 24000 / 8000 / 6000 / 288000 ms):

```
"verify:compile",5-execute,executed,0,0,6000,"2026-08-27T07:12:50Z"
"verify:module-tests",5-execute,executed,0,0,288000,"2026-08-27T15:45:47Z"
```

A `verify:module-tests` run of 288 seconds did not consume zero tokens and zero tool uses; nobody passed the usage. But the row asserts a measurement. A consumer summing `execution_log.total_tokens` gets `0` for the whole phase and has no way to tell that from a phase that genuinely dispatched nothing.

## Root cause

`record-step`'s usage parameters default to `0` rather than to an explicit unmeasured sentinel, so an omitted argument is silently promoted to a measured value. This is the exact shape that `manage-metrics record-dispatch-boundary` already closed for its own four context-load columns, where an omitted flag writes the literal `unmeasured` and is omitted from the result TOON — *"'the caller passed no measurement' stays distinguishable from 'the dispatch loaded zero context'"*. The same discipline has not reached the sibling ledger.

## Proposed action

Apply the `record-dispatch-boundary` contract to `record-step`: an omitted `--total-tokens` / `--tool-uses` writes `unmeasured` rather than `0`, is omitted from the return TOON, and is named in an `unmeasured_columns` field. A **measured** zero stays `0`. Downstream sums then report their own coverage instead of silently averaging an unmeasured phase in as free.

This closes the ledger half of the same problem the `6-finalize`-instrumentation candidate closes for the phase half; the two are best fixed together, since a `record-step` row that says `unmeasured` is only useful once finalize emits rows at all.

## Evidence

- `execution.toon` `execution_log[8]` — every row `total_tokens=0, tool_uses=0`
- aspect: logging_gap_analysis — "Every verify:* execution_log row records total_tokens=0 and tool_uses=0 — a MEASURED-looking zero that is actually an unrecorded value"
- `manage-metrics/SKILL.md` § record-dispatch-boundary — the already-shipped contract this proposal asks to mirror: "They have no numeric default: an omitted flag writes the literal `unmeasured` into its column"
