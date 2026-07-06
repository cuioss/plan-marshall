# Aspect: Routing-Decision Verification

The routing-decision aspect grades, at finalize, every routing decision the run actually made — recipe-match, aspect-classification, and the execution-profile posture — so the mechanism self-corrects. It is the per-plan analog of the corpus-level `recipe-match` / `track-selection-accuracy` / `token-economics` audit checks, and feeds them.

## Deterministic facts vs LLM judgment

The split is the same the whole skill follows: the script `check-routing-decisions` produces the deterministic facts; this reference is the LLM contract that synthesizes a **judgment** from them. The script re-evaluates the named prune predicates against the realized footprint and emits facts — it computes **no** posture counterfactual. The LLM owns exactly one judgment: the OVER/UNDER posture verdict. `plan-retrospective` is already the heaviest finalize agent, so this aspect's verification stays deterministic in the script; reserve LLM cognition for the OVER/UNDER call — it must not become the overhead it polices.

The predicate definitions (the closed `prunable_when` vocabulary, the class→default-tier table, the resolution lattice) are owned by [`../../extension-api/standards/ext-point-lane-element.md`](../../extension-api/standards/ext-point-lane-element.md) — do not restate them here.

## Script facts (input to the judgment)

`check-routing-decisions run --mode {live|archived} [--diff-file ...]` emits:

| Fact | Meaning |
|------|---------|
| `posture` | the chosen `execution_profile` (`minimal` / `auto` / `full`) |
| `planning_lane` | the resolved `light` / `deep` planning lane |
| `mis_prune_checks[]` | one per prunable step ABSENT from `phase_6.steps`: `pass` (predicate still holds / step ran), `skip` (no realized footprint), or **`fail`** (predicate now false — a mis-prune) |
| `cost_preview` | `predicted_tokens` (init preview) vs `actual_tokens` (`execution_log` sum) and the signed `delta_tokens` / `delta_pct` |
| `recompose_divergence` | the `lane_resolution` decision-log entry count (init + phase-4 re-compose) |
| `recorded_lane_decisions[]` | the raw `lane_resolution` decision-log lines |
| `llm_judgement_required` | always `true` — the marker that the OVER/UNDER verdict is the LLM's, not the script's |

## The LLM judgment (the only cognition)

Synthesize ONE verdict — `OVER-PROVISIONED | UNDER-PROVISIONED | correct` — from the facts:

1. **Mis-prune is the highest-value signal.** Any `mis_prune_checks[].status == fail` is strong evidence of **UNDER-PROVISIONED** for that step: a step the lane skipped (e.g. `sonar-roundtrip` skipped as "no code delta") whose predicate the realized footprint falsifies (the merged diff touched production code). A wrongly-skipped adversarial / quality step is the file-worthy outcome.
2. **Posture counterfactual.** Compare the chosen `posture` against the posture the realized signals would have selected. A `minimal` run that produced a large production diff with mis-prunes reads OVER-pruned (UNDER-PROVISIONED); a `full` run on a trivial doc change with zero kept-step yield reads OVER-PROVISIONED.
3. **Cost-preview accuracy.** A large `cost_preview.delta_pct` (predicted far from actual) is a calibration signal, not a posture error — route it to the `cost_size_token_table` recalibration (§4.6a), not to a posture re-judgment.

## Output fragment + the file-worthy signal

Emit a TOON fragment carrying the verdict, the supporting facts, and — when a mis-prune fired or the posture counterfactual disagrees with the chosen posture — a proposed lesson. A **recurring** mis-prune across plans is the file-worthy signal: it routes to threshold tuning of the prune predicates (sonar / lessons-housekeeping) through the existing lesson / `architecture enrich` path, so the thresholds learn from outcomes rather than staying hard-coded. A one-off mis-prune is reported but not necessarily filed.

The judgment fragment carries the LLM verdict (`posture_verdict`, `proposed_lessons`) alongside the script's supporting facts, **using the same field names the script emits** (`mis_prune_checks`, `cost_preview`, `posture`, `planning_lane`) — the LLM augments the facts, it does not rename them. Keeping the names identical is what lets `compile-report.should_emit()` recognize the fragment as renderable (its routing-decisions carve-out gates on `manifest_present` / `mis_prune_checks` / `cost_preview` / `posture_verdict` / `posture`):

```toon
status: success
aspect: routing-decisions
manifest_present: true
posture: minimal | auto | full
planning_lane: light | deep
posture_verdict: UNDER-PROVISIONED | OVER-PROVISIONED | correct
mis_prune_checks[N]: [ {check, status, predicate, detail}, ... ]
cost_preview: { predicted_tokens, actual_tokens, delta_tokens, delta_pct }
proposed_lessons[M]: [ ... ]
```
