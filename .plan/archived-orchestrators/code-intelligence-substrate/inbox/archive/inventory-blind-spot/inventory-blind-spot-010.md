envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:37:32Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall
source_plan=inventory-blind-spot

# `multi_module` is a scope_estimate the budget table has no row for, so no token budget was enforceable

## Observation — this run

`references.json` records `scope_estimate: multi_module`, set deliberately at refine (decision.log `188867`: "Scope: multi_module - Modules: 3").

The plan-efficiency aspect's calibration-anchors table in `references/plan-efficiency.md` has rows for exactly four values:

```
surgical | single_module | cross_cutting | complex
```

`multi_module` matches none of them. The aspect's documented behaviour on an unanchored row is to fall back to four generic ratio thresholds — which it did, and three of the four tripped. But the *absolute* token/duration budget (the thing that would have said "2.37M tokens is too much for this change") was never applicable, because there is no row to apply.

The plan consumed ~2.37M tokens (a floor — 6-finalize is still open) for a 10-file change, and no anchored budget check ever evaluated it.

## Root cause

Two vocabularies for the same field, maintained in different places and never cross-checked:

- the producer: whatever `phase-2-refine` / `manage-status scope-estimate-heuristic` may emit;
- the consumer: the hardcoded row set in the plan-efficiency reference doc.

Nothing enforces that the second covers the first. The failure is silent by design — the doc *specifies* a fallback for unanchored rows, so the gap reads as a supported path rather than as drift.

## Solution

1. Add the missing `multi_module` rows (bug_fix / feature / refactor) to the anchors table.
2. Better: add a test asserting `set(scope_estimate values the producers can emit) subset-of set(rows in the anchors table)`. Population-derived, so a future scope-estimate value cannot silently land outside the budget gate.
3. Have the aspect emit an explicit `error`-severity finding when it falls back for an *unrecognised* value (as opposed to a genuinely unanchored combination), so the drift is loud rather than absorbed.

## Generalisation

**A documented fallback can disguise a vocabulary gap.** When a consumer's lookup table is a hand-maintained subset of a producer's enum, and the miss path is a graceful degradation rather than an error, the two drift apart invisibly and the degradation becomes the normal path. Any enum consumed by a table in a *different* file needs a closure assertion.

Note the irony worth recording: this plan's own headline fix was introducing `FILE_CATEGORIES` so that an unknown category name becomes a distinguishable answer instead of a confident empty one. The retrospective auditing that plan hit the identical defect class in its own budget gate.

## Impact

`plan-retrospective/references/plan-efficiency.md`. Any plan with `scope_estimate=multi_module` — which refine sets whenever a change spans 2+ modules — runs without an absolute budget anchor.
