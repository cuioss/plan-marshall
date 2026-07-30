# Aspect: Routing-Decision Verification

The routing-decision aspect grades, at finalize, every routing decision the run actually made — recipe-match, aspect-classification, and the execution-profile posture — so the mechanism self-corrects. It is the per-plan analog of the corpus-level `recipe-match` / `track-selection-accuracy` / `token-economics` audit checks, and feeds them.

## Deterministic facts vs LLM judgment

The split is the same the whole skill follows: the script `check-routing-decisions` produces the deterministic facts; this reference is the LLM contract that synthesizes a **judgment** from them. The script re-evaluates the named prune predicates against the realized footprint and emits facts — it computes **no** posture counterfactual. The LLM owns exactly one judgment: the OVER/UNDER posture verdict. `plan-retrospective` is already the heaviest finalize agent, so this aspect's verification stays deterministic in the script; reserve LLM cognition for the OVER/UNDER call — it must not become the overhead it polices.

The predicate definitions (the closed `prunable_when` vocabulary, the class→default-tier table, the resolution lattice) are owned by [`../../extension-api/standards/ext-point-lane-element.md`](../../extension-api/standards/ext-point-lane-element.md) — do not restate them here.

## Script facts (input to the judgment)

`check-routing-decisions run --mode {live|archived} [--diff-file ...]` emits:

| Fact | Meaning |
|------|---------|
| `posture` | the chosen `execution_profile` (`minimal` / `standard` / `full`) |
| `planning_lane` | the resolved `light` / `deep` planning lane |
| `mis_prune_checks[]` | one per prunable step: `pass` (step ran / predicate still holds), `skip` (no realized footprint, or a recorded non-predicate removal cause), `inconclusive` (removal cause unestablishable), or **`fail`** (predicate now false — a mis-prune). Every row also carries `removal_cause` — see [Removal cause precedes predicate re-evaluation](#removal-cause-precedes-predicate-re-evaluation) |
| `cost_preview` | `predicted_tokens` (init preview) vs `actual_tokens` (`execution_log` sum) and the signed `delta_tokens` / `delta_pct` |
| `recompose_divergence` | the `lane_resolution` decision-log entry count (init + phase-4 re-compose) |
| `recorded_lane_decisions[]` | the raw `lane_resolution` decision-log lines |
| `llm_judgement_required` | always `true` — the marker that the OVER/UNDER verdict is the LLM's, not the script's |

## Removal cause precedes predicate re-evaluation

**A removal fact never implies a removal cause.** A prunable step can leave `phase_6.steps` through several recorded mechanisms that are all orthogonal to the realized footprint — the posture-tier cutoff, an unresolved `lane: ask` with no provider, an inactive simplify step, and a ceremony-finalize selection resolving `never`. Inferring "the prune predicate fired" from the bare fact that the step is absent is therefore unsound, and it manufactured a false `fail` on every standard/minimal-posture plan whose footprint touched production code.

The script consults the recorded decision log FIRST and re-evaluates a predicate only for a step whose removal no recorded mechanism explains. The verdicts are mutually exclusive and jointly exhaustive over an absent step:

| Absent step's state | Verdict | `removal_cause` |
|---------------------|---------|-----------------|
| No realized footprint | `skip` | `not_evaluated` |
| Named by a recorded non-predicate mechanism | `skip` | the mechanism token |
| Decision log absent or unreadable | `inconclusive` | `unestablishable` |
| Readable log names no cause, predicate now false | `fail` | `predicate_evaluated` |
| Readable log names no cause, predicate still holds | `pass` | `predicate_evaluated` |

Log readability is the sole discriminator between `fail` and `inconclusive`: the composer emits a decision-log line for every removal mechanism, so a *readable* log naming no cause is positive evidence the predicate is the remover, while an *unreadable or absent* log substantiates nothing.

**The generalizable rule this encodes**: a deterministic audit check that infers *why* something happened from the fact *that* it happened is sound only when the observable state has exactly one possible cause. When two or more mechanisms can produce the same observable state, the check MUST read the recorded cause — especially when that record is already in the script's own input set — and MUST report `inconclusive` rather than a fabricated verdict when no cause can be established. This applies to every deterministic check in this skill, not only to mis-prune.

## The LLM judgment (the only cognition)

Synthesize ONE verdict — `OVER-PROVISIONED | UNDER-PROVISIONED | correct` — from the facts:

1. **Mis-prune is the highest-value signal.** Any `mis_prune_checks[].status == fail` is strong evidence of **UNDER-PROVISIONED** for that step: a step the lane skipped (e.g. `sonar-roundtrip` skipped as "no code delta") whose predicate the realized footprint falsifies (the merged diff touched production code). A wrongly-skipped adversarial / quality step is the file-worthy outcome. A `skip` row carrying a recorded `removal_cause` says nothing about provisioning — the step left the chain for a reason orthogonal to the footprint — and MUST NOT be read as either evidence for or against the posture. An `inconclusive` row means the removal cause could not be established; surface it as a plan-state defect (the decision log was missing or unreadable), never as a mis-prune.
2. **Posture counterfactual.** Compare the chosen `posture` against the posture the realized signals would have selected. A `minimal` run that produced a large production diff with mis-prunes reads OVER-pruned (UNDER-PROVISIONED); a `full` run on a trivial doc change with zero kept-step yield reads OVER-PROVISIONED.
3. **Cost-preview accuracy.** A large `cost_preview.delta_pct` (predicted far from actual) is a calibration signal, not a posture error — route it to the `cost_size_token_table` recalibration (§4.6a), not to a posture re-judgment.

## Output fragment + the file-worthy signal

Emit a TOON fragment carrying the verdict, the supporting facts, and — when a mis-prune fired or the posture counterfactual disagrees with the chosen posture — a proposed lesson. A **recurring** mis-prune across plans is the file-worthy signal: it routes to threshold tuning of the prune predicates (sonar / lessons-housekeeping) through the existing lesson / `architecture enrich` path, so the thresholds learn from outcomes rather than staying hard-coded. A one-off mis-prune is reported but not necessarily filed.

The judgment fragment carries the LLM verdict (`posture_verdict`, `proposed_lessons`) alongside the script's supporting facts, **using the same field names the script emits** (`mis_prune_checks`, `cost_preview`, `posture`, `planning_lane`) — the LLM augments the facts, it does not rename them. Keeping the names identical is what lets `compile-report.should_emit()` recognize the fragment as renderable (its routing-decisions carve-out gates on `manifest_present` / `mis_prune_checks` / `cost_preview` / `posture_verdict` / `posture`):

```toon
status: success
aspect: routing-decisions
manifest_present: true
posture: minimal | standard | full
planning_lane: light | deep
posture_verdict: UNDER-PROVISIONED | OVER-PROVISIONED | correct
mis_prune_checks[N]: [ {check, status, predicate, removal_cause, detail}, ... ]
cost_preview: { predicted_tokens, actual_tokens, delta_tokens, delta_pct }
proposed_lessons[M]: [ ... ]
```
