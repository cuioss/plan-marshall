envelope_version=1
sender_type=plan
sender_id=adhoc-token-economy-analysis
epic=truthful-signals
kind=finding
created=2026-09-14T17:02:08Z

component=plan-marshall:manage-metrics
category=bug
title=The metrics report renders ten token figures and the one labelled "Billing (cost)" understates output fivefold — collapse to a single number
confidence=high
source_plan=adhoc-token-economy-analysis

# The metrics report renders ten token figures and the one labelled "Billing (cost)" understates output fivefold

## Context

**Defect 1 — the weighting is wrong.** `manage-metrics/standards/data-format.md` defines
`billing_weighted_total` as:

```text
input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)
```

`output` carries coefficient **1**. Every current Claude model prices output at **5× input**
(Opus 5 `$5/$25`, Sonnet 5 `$2/$10`, Haiku 4.5 `$1/$5`), so the correction is
model-independent. The other two coefficients are correct — cache read is 0.1× and cache
write 1.25× of the model's input price.

The field's lattice population is `derived-cost` and it is rendered as a **first-class
"Billing (cost)" column with its own Total**, plus a `Billing-weighted total` bullet. So the
figure presents as the authoritative cost measure while under-weighting the most expensive
token class by 5×.

The consequence is directional, not random: **every generation-versus-context conclusion
drawn from that column is skewed toward context by a factor of five.** Working a corpus
share back through the correction moves generation from ~1.1% of the column to ~5.3% of real
spend. Both are small — this does not overturn a context-first conclusion — but the column is
upstream of every token-reduction judgement made in this repository, and the error is
silent at every read site.

**Defect 2 — an interpretation trap the first defect exposes.** A `cache_read` /
`cache_creation` / `output` percentage triple reads either as TOKEN shares or as
WEIGHTED-COST shares, and the two readings differ by more than an order of magnitude. Nothing
in the rendering says which it is. The discriminator is internal and cheap: dividing the two
context terms by their weights must reproduce the independently measured average re-read
factor — under the cost reading it does (41.7 against a measured 44.6), under the token
reading it is off by more than tenfold (3.34). This was established in-session only because
the arithmetic was checked against a second measurement; a reader without that check has no
way to tell the readings apart.

## Root cause

Defect 1 is a coefficient that was never differentiated: input and output enter the sum at
the same weight, which is true of their TOKEN counts and false of their PRICES. The doc
attributes the weights to "the Claude runtime's pricing model", so the formula is presented
as priced when it is only partly priced.

Defect 2 is the absence of a unit label on a rendered percentage — the shape ADR-022 § Risks
now records, and an instance of the general "a figure rendered under a label implying a
different population" defect the lattice in that same document exists to prevent.

## Proposed action

**Operator directive (this is the primary ask, not the coefficient fix):** the billing
display is confusing and should be **reduced to a single number**, and whether to display it
at all should be reconsidered.

The confusion is structural rather than cosmetic. `data-format.md` Direction 1 currently
renders **ten** token-bearing figures: `total_tokens`, `dispatch_boundary_total`,
`subagent_total_tokens`, `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
`cache_creation_input_tokens`, `billing_weighted_total`, `cache_read_per_tool_use`, and
`inline_main_context_tokens` — spanning three populations (`main-context-window`,
`dispatched-subagent`, `derived-cost`) that the document itself states are **"not additively
comparable"**. A reader is handed ten numbers, no two of which may be added, one of which is
labelled as the cost and is wrong by 5×.

Suggested shape, to be settled by the epic rather than prescribed here:

- Decide first whether a cost figure belongs in the report at all. If the consumer question
  is "what did this plan cost", one number answers it; if no consumer has that question, the
  column's removal is the cheapest fix and it takes Defect 1 with it.
- If it stays: **one** figure, correctly weighted (`input + 5×output + 0.1×cache_read +
  1.25×cache_creation`), with the per-category breakdown demoted out of the rendered report
  and left recorded-but-not-rendered, where the lattice's Direction 2 already puts the fields
  nobody reads.
- Whatever survives must state its unit — priced-cost versus raw tokens — at the render site,
  so Defect 2 cannot recur in the replacement.
- The weights belong in one named constant derived from the model's pricing, not inlined in a
  formula in prose, so a future pricing change cannot leave the doc and the code disagreeing.

⛔ **Do not fix the coefficient alone.** A correctly-weighted tenth figure in a report of ten
non-comparable figures is still the confusion the directive names; the coefficient is the
smaller half of this finding.

## Evidence

- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`
  § Direction 1 — the `billing_weighted_total` formula with `output` at coefficient 1, and
  the ten rendered token figures across three populations
- The same document's Token-Field Population Lattice preamble — "A consumer that aggregates
  two fields MUST check that their populations agree first; fields of different populations
  are not additively comparable"
- Model pricing, verified against the `claude-api` skill's current model table: output is 5×
  input on every current model, so the correction does not depend on which model ran
- `doc/adr/022-Economy_rules_bind_the_persisted_artifact_never_the_reasoning_that_produced_it.adoc`
  § Risks — this defect recorded as a standing risk to any re-argument that quotes the column
