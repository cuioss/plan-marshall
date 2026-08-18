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
| `mis_prune_checks[]` | one per prunable step: `pass` (step ran / predicate still holds), `skip` (footprint unresolvable — no `--diff-file` **and** the shared whole-chain resolver recovered none — or a recorded non-predicate removal cause), `inconclusive` (removal cause unestablishable), or **`fail`** (predicate now false — a mis-prune). Every row also carries `removal_cause` — see [Removal cause precedes predicate re-evaluation](#removal-cause-precedes-predicate-re-evaluation) |
| `footprint_source` | how the realized footprint was obtained: `diff_file` (explicit `--diff-file`), `resolved` (recovered through the shared resolver), or `unresolved` (no tier answered → the mis-prune checks skip). A **supplied** `--diff-file` never yields `unresolved`: see [A supplied `--diff-file` resolves or raises](#a-supplied---diff-file-resolves-or-raises) |
| `cost_preview` | `predicted_tokens` (init preview) vs `actual_tokens` (`execution_log` sum) and the signed `delta_tokens` / `delta_pct` |
| `recompose_divergence` | the `lane_resolution` decision-log **line** count. ⚠ Despite the field name this is NOT a recompose count: the composer emits one line per dropped step plus one per lane warning, so the number rises with the size of a single compose's subtraction, not with the number of composes. Read it as "how much lane subtraction was recorded", never as "how many times the manifest was recomposed" |
| `recorded_lane_decisions[]` | the raw `lane_resolution` decision-log lines |
| `llm_judgement_required` | always `true` — the marker that the OVER/UNDER verdict is the LLM's, not the script's |

## A supplied `--diff-file` resolves or raises

An **absent** `--diff-file` and a **supplied but unresolvable** one are different states and are reported differently.

Absent, the script recovers the footprint through the shared whole-chain resolver, and only a still-unresolvable footprint degrades the mis-prune checks to `skip`. Supplied, the argument is resolved against the plan directory first and the process cwd second — so the plan-relative form the capture pattern documents (`--diff-file work/footprint.txt`, matching the sibling `collect-fragments add --fragment-file` flag in the same workflow) names the same file an absolute path does. If no candidate exists the script **raises**, naming every candidate it tried.

It must not return an empty footprint there. Doing so gave a could-not-look the same token as a nothing-to-look-at, and that token degrades to a `skip` that reads benign in every downstream summary: the documented plan-relative invocation silently reported *"footprint unresolvable"* while the identical file passed as an absolute path found a real mis-prune. The two invocations now produce the same verdict, which is the property to hold onto.

## The realized footprint's production verdict comes from the build map

`footprint_has_production` — the input to every `no_code_delta` re-evaluation — classifies each path through `build.map` in marshal.json, the declared file-to-build oracle, via the `_footprint_classification` module this check **shares** with `check-manifest-consistency.py`. The two previously carried byte-identical private prefix tuples declaring a whole project-local dotfile tree to be bookkeeping — a tree a build extension may route as `production`, and on the Claude target does (`.claude/skills/*.py`).

A path counts as production when the oracle routes it `production`, **or when it resolves to `unclassified`**. The second half is fail-closed rather than sloppy: the verdict this feeds is a mis-prune `fail` — a step pruned as `no_code_delta` when code did change — so answering "not production" for a path nobody could classify would turn an unknown into an exoneration.

`unclassified` is **narrower than "unrouted"**. Where the oracle is silent the shared classifier still recognises documentation (by suffix) and test files (by filename/directory convention), so an unrouted `README.md` or `test_foo.py` never reaches the production set. Without those convention rungs a project whose `build.map` declares no `test` route would have every tests-only footprint reported as a mis-prune.

## Removal cause precedes predicate re-evaluation

**A removal fact never implies a removal cause.** A prunable step can leave `phase_6.steps` through several recorded mechanisms that are all orthogonal to the realized footprint — every gate that reports a subtraction through the composer's shared `[STATUS] … dropped …` record (the posture-tier cutoff and the narrowing decision-matrix rows among them), plus the individually-shaped mechanisms: an unresolved `lane: ask` with no provider, an inactive simplify step, a ceremony-finalize selection resolving `never`, and the retired aggregate posture-cutoff line that only archived logs still carry. Inferring "the prune predicate fired" from the bare fact that the step is absent is therefore unsound, and it manufactured a false `fail` on every standard/minimal-posture plan whose footprint touched production code.

**Reader coverage is part of that soundness.** The script parses the shared subtraction-record shape through the same definition the composer writes it with, and matches it gate-agnostically, so a gate added to THAT family is recognised without an edit here. A mechanism the reader cannot parse reads exactly like one that was never recorded — the same false `fail`, arriving by a different route.

⚠ That guarantee covers one shape, not every removal. A new gate that renders its own line still needs a matching pattern, and one already exists: the `reconcile` verb's `frozen_manifest_stale` path can drop an arbitrary `phase_6` step — a prunable one included — on a line carrying no `[STATUS]` tag, so its removals are still unrecognised and still produce the false `fail` this check exists to end.

The script consults the recorded decision log FIRST and re-evaluates a predicate only for a step whose removal no recorded mechanism explains. The verdicts are mutually exclusive and jointly exhaustive over an absent step:

| Absent step's state | Verdict | `removal_cause` |
|---------------------|---------|-----------------|
| Footprint unresolvable (no `--diff-file` **supplied** and the shared resolver recovered none) | `skip` | `not_evaluated` |
| Named by a recorded non-predicate mechanism | `skip` | the mechanism token |
| Decision log absent or unreadable | `inconclusive` | `unestablishable` |
| Readable log names no cause, predicate now false | `fail` | `predicate_evaluated` |
| Readable log names no cause, predicate still holds | `pass` | `predicate_evaluated` |

Log readability is the sole discriminator between `fail` and `inconclusive`: the composer records a decision-log line for the removal mechanisms this reader parses, so a *readable* log naming no cause is positive evidence the predicate is the remover, while an *unreadable or absent* log substantiates nothing. That inference is only as good as the reader's coverage — a mechanism it cannot parse is indistinguishable from one that was never recorded, which is why coverage is a property of the shared shape rather than of a hand-maintained list.

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
