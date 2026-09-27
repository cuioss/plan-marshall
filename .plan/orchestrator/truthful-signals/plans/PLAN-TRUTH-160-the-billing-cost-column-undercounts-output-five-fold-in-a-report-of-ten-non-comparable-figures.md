# PLAN-TRUTH-160: The "Billing (cost)" column undercounts output five-fold, in a report of ten non-comparable figures

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15 from `adhoc-token-economy-analysis-001.md`, filed directly into this epic's inbox by an
ad-hoc analysis session (not a tracked plan). Corroborated first-party at staging: current model pricing
(Opus 5 $5/$25, Sonnet 5 $2/$10, Haiku 4.5 $1/$5) confirms output is 5× input on every current Claude
model, model-independently.

## Objective

**`manage-metrics/standards/data-format.md`'s `billing_weighted_total` formula weights `output` at
coefficient 1 instead of 5, so the rendered "Billing (cost)" column — presented as the authoritative cost
figure, with its own Total — undercounts the most expensive token class by 5×, skewing every
generation-versus-context conclusion drawn from it toward context.**

```text
billing_weighted_total = input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)
```

`cache_read` (0.1×) and `cache_creation` (1.25×) are correctly weighted; only `output` is not. The
consequence is directional and measured: working a corpus share back through the correction moves
generation from ~1.1% of the column to ~5.3% of real spend — small in absolute terms, but the column is
upstream of every token-reduction judgement in this repository (see this epic's own project-memory:
"~99% of billing weight is CONTEXT, not generation" was derived from this exact under-weighted column).

**A second, structural defect the coefficient fix does not touch.** The rendered report carries TEN
token-bearing figures (`total_tokens`, `dispatch_boundary_total`, `subagent_total_tokens`,
`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`,
`billing_weighted_total`, `cache_read_per_tool_use`, `inline_main_context_tokens`) spanning three
populations (`main-context-window`, `dispatched-subagent`, `derived-cost`) the document's own Token-Field
Population Lattice states are "not additively comparable." A `cache_read`/`cache_creation`/`output`
percentage triple is also rendered with no unit label, so it reads ambiguously as either token shares or
weighted-cost shares — two readings that differ by more than an order of magnitude, discriminable only by
an internal cross-check (dividing the context terms by their weights should reproduce the independently
measured average re-read factor: 41.7 against 44.6 under the cost reading, off by 10× under the token
reading).

**Operator directive, the primary ask.** Reduce the billing display to a single number, and reconsider
whether to display a cost figure at all — the confusion is structural, not a coefficient bug alone. Do NOT
fix the coefficient in isolation; a correctly-weighted tenth figure in a report of ten non-comparable
figures is still the confusion this directive names.

## Deliverables

Three deliverables. D0 is a gate.

**D0 — GATE: decide whether a cost figure belongs in the report at all, and derive the full rendered
population it interacts with.** If no consumer needs "what did this plan cost", removing the column takes
the coefficient bug with it. If it stays, D0 settles the single-figure shape.

**D1 — Fix the weighting and collapse to one figure (if D0 keeps the column).** `input + 5×output +
0.1×cache_read + 1.25×cache_creation`, as ONE rendered figure with a stated unit (priced-cost, not raw
tokens), replacing the ten-figure report. The per-category breakdown is demoted to recorded-but-not-
rendered (the lattice's Direction 2, where fields nobody reads already live). The weights are a named
constant derived from model pricing, not inlined in formula prose, so a future pricing change cannot leave
doc and code disagreeing.

**D2 — Re-derive every already-published conclusion that cited the old column, and correct or caveat it.**
This epic's own project memory cites token-roadmap figures computed from this exact defect; D2 names what
must be re-stated rather than silently left wrong.

## Claim Labels

- OBSERVED: `manage-metrics/standards/data-format.md` § Direction 1 defines `billing_weighted_total` with
  `output` at coefficient 1 (quoted verbatim by the source finding; re-verify at outline against HEAD).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: data-format.md:56,152 still reads billing_weighted_total = input + output + round(0.1*cache_read) + round(1.25*cache_creation) verbatim at this HEAD -- output coefficient is 1, not 5
- OBSERVED: current Claude model pricing has output at 5× input on every current model (Opus 5, Sonnet 5,
  Haiku 4.5) — corroborated first-party at staging against the `claude-api` skill's model table.
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: Current published Claude API pricing (Opus 5 5/25, Sonnet 5 2/10, Haiku 4.5 1/5 per Mtok) confirms output=5x input on every current model, unchanged since staging
- OBSERVED: the same document renders ten token-bearing figures across three stated-non-comparable
  populations (re-verify at outline against HEAD).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: data-format.md's own Token-Field Population Lattice section and explicit 'not additively comparable' language confirmed verbatim at this HEAD; exact ten-figure/three-population tally not independently re-counted this pass
- ⚠ HYPOTHESIS: the corpus-share correction (generation ~1.1% → ~5.3% of real spend) is arithmetically
  correct. ⛔ Not independently re-derived at staging — re-verify at outline (verify-at-outline).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: The 1.1%->5.3% corpus-share arithmetic was not independently re-derived at cleanup time; explicitly deferred to verify-at-outline by the spec itself
- ⚠ HYPOTHESIS: no consumer of the rendered report actually needs a per-category token breakdown, only a
  single cost figure. ⛔ An asserted absence of a need — D0 owns this decision and may find a consumer that
  does need the breakdown, which changes D1's shape (verify-at-outline).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: Asserted absence of a per-category-breakdown consumer was not swept against actual report readers at cleanup time; D0 owns this decision

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — the
  formula and the rendered report shape (D0, D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/**` — the rendering
  implementation (verify-at-outline)
- HYPOTHESIS: `doc/adr/022-Economy_rules_bind_the_persisted_artifact_never_the_reasoning_that_produced_it.adoc`
  § Risks — already records this defect class as a standing risk (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-metrics/**` — coverage for the corrected weighting and shape
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` and
  `marketplace/bundles/plan-marshall/skills/phase-5-execute/**` — the `record-dispatch-boundary` call
  sites that pass no context-load flags (added 2026-09-17, folded from
  `truth-166-architecture-refresh-migration-churn-007.md`)
  (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Bears directly on how PLAN-TRUTH-157's own landing report (this epic's `landings/PLAN-TRUTH-157.md`)
  and every prior landing's Phase Breakdown table should be read — none are corrected retroactively by
  this spec; D2 states what needs re-derivation going forward.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-160-the-billing-cost-column-undercounts-output-five-fold-in-a-report-of-ten-non-comparable-figures.md"
```

## ⭐ FOLDED 2026-09-17 — THE COLUMN IS EMPTY BECAUSE NO CALL SITE PASSES THE FLAGS THE RECORDER ALREADY ACCEPTS

Forwarded from `truth-166-architecture-refresh-migration-churn-007.md` (PR #1501, first-party). Expected
Surface extended in the same act (the dispatch-return sites, above).

⛔ **The instrumentation is neither missing nor dishonest — it is unwired.** `record-dispatch-boundary`
declares all four context-load flags and deliberately writes the literal `unmeasured` rather than a false
`0`, and `unmeasured_context_load_columns` names what each row declined to claim. But **0 of 13**
dispatch-boundary rows across `4-plan` / `5-execute` / `6-finalize` carried a measured figure on that run,
so `context_position_cost.position_multiple` is `unmeasured` plan-wide; **27 of 32** execution-log rows
carry no token figure; and `manage-metrics enrich` never ran, leaving
`totals_billing_weighted_total: 0` at `population_count: 0` and the `Billing (cost)` column empty for all
six phases — on a run costing 9,979,683 tokens with finalize alone at 53%.

This is the same defect this plan already targets, one layer earlier: D0 asks whether a cost figure belongs
in the report at all, and this fold supplies the answer's precondition — **an empty column is not evidence
the cost is small, it is evidence nothing passed the flags**. Remedy: pass the four flags at the finalize
and execute dispatch-return sites that already call `record-dispatch-boundary`, and either run `enrich`
from `record-metrics` or render the column as explicitly unpopulated. ⭐ The project ranks context cost
first (`TOKEN REDUCTION IS PRIORITY 1`), and the cache-read share — documented as the dominant component of
billing weight — is unknown at both the per-dispatch and per-phase tier until this lands.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
