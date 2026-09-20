envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T07:29:11Z

component=plan-marshall:manage-metrics
category=bug
title=Per-dispatch context-load attribution is 100% zero, undocumented termination_cause values pass the unknown-value detector, and dispatch-boundary coverage is ~50% with no denominator

# The dispatch-boundary audit trail is unpopulated, unvalidated, and uncounted — three failures that all read as clean

## Observation

Plan `exploration-share-is-unmeasured` recorded 12 dispatch-boundary rows across `4-plan` (1), `5-execute` (6) and `6-finalize` (5). Three independent defects:

### 1. Four-field context-load attribution is entirely zero

Every one of the 12 rows carries:

```
input_tokens=0, output_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=0
```

The per-dispatch context-load channel — documented as the per-DISPATCH counterpart to the per-PHASE four-field view `enrich` writes — has **never been populated on this plan**. `0` and "not measured" are the same value here, and no consumer distinguishes them. This is the direct structural sibling of the exploration-share and token-economics counters this plan shipped.

### 2. Undocumented `termination_cause` values pass the unknown-value detector

`manage-metrics` SKILL.md declares the enum as `{voluntary_checkpoint, task_complete_returned_verbatim, budget_yield, harness_cancellation, error, clean_exit_queue_empty}` and states that missing or unrecognised values "are rejected as script errors (there is no implicit fallback)".

Actually recorded: **`task_batch_complete`** (4-plan) and **`step_complete`** (6-finalize, 4 of 5 rows). Neither is in the documented enum. `analyze-logs` nonetheless reports `unknown_count: 0` for all three phases — so the detector whose job is to flag unknown causes agrees with neither the documentation nor the data.

### 3. Coverage is ~50% and nothing computes the denominator

For `6-finalize`:

| Signal | Count |
|---|---|
| Steps marked done in `phase_steps` | 15 |
| Accumulator `samples` | 10 |
| Dispatch-boundary rows | **5** |

Roughly half the finalize dispatches left no boundary row. The file is append-only and nobody counts against a denominator, so the shortfall is invisible. `plan-retrospective` is documented to correlate this audit trail against `[OUTCOME]` log coverage — it is correlating against a ~50%-complete source.

A related casualty: one 6-finalize dispatch terminated with `termination_cause=error` at **378,387 tokens and 60 tool uses** — the single most expensive dispatch of the phase. It appears only as a row in the boundary file. No `phase_steps` entry carries a `failed` outcome and no work-log ERROR names it. The most expensive failure of the run is effectively unlogged.

## Rule

- **A numeric attribution field that is structurally always zero is worse than absent** — absence is detectable, zero is a claim. Either populate the four context-load fields or have the writer emit a null/absent marker so a consumer can tell "no data" from "no tokens".
- **An enum documented as "rejected, no implicit fallback" must be enforced at the write boundary**, and the downstream unknown-value detector must be derived from the same enum constant rather than an independent list. Two vocabularies drifted here and the detector matched neither.
- **An append-only audit trail needs a denominator.** Coverage that is never computed is coverage that is never known; assert one boundary row per completed dispatched step, or publish `rows / expected` so a 50% trail cannot present as a complete one.
- A dispatch that terminates with `error` must produce a `failed` step outcome and a work-log entry. A cause recorded only in a metrics side-file is not an incident record.

## Relation to prior message

Candidate-lesson `-002` recorded doc-contract divergence in `manage-metrics` (the D2 counter enumeration updated in `data-format.md` but not in `SKILL.md`). Defect 2 above is the **same divergence class in the same skill, on a different enumeration** — evidence that the fix must be structural (single-source the enumeration) rather than per-list.

## Residue

None of the three is fixed.
