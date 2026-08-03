# Check: billing-composition (cross-plan)

Re-derives, as a first-party deterministic check, the corpus figures a one-off
analysis previously reported by hand: the **billing composition** (which weighted
part of the billing formula the corpus actually pays for) and the **payload-byte
composition** (which tool-call bucket the observed result bytes actually came
from). This is a cross-plan check: it emits one aggregate block — a figures table
plus the per-plan audit rows behind it — rather than one row per plan in
isolation. The deterministic computation lives in `scripts/audit.py`
(`cross_billing_composition` / `emit_billing_composition_block`); this
sub-document is the interpretation guide.

The check exists because a hand-computed composition figure is unreproducible and
carries no population: it cannot be re-run against a changed corpus, and a reader
cannot tell how many plans it was computed over or how many of those plans were
under-recorded. Every figure this check emits carries its own population and its
own floor label, so neither question is left open.

## Inputs the check reads

Per plan, the script reads two families of per-phase fields from
`work/metrics.toon` and one reconciliation source per phase. No other input is
consulted, and no figure is read from a persisted aggregate — every number is
re-derived from the raw per-phase fields.

| Input | Field(s) read | Used for |
|-------|---------------|----------|
| `work/metrics.toon` | per-phase `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` | the billing-formula reconstruction and its composition shares |
| `work/metrics.toon` | per-phase `{exploration,work,execute,orchestration,unclassified}_result_bytes` | the payload-byte composition shares and the residual |
| `work/metrics.toon` | per-phase `total_tokens`, `close_count` | the reconciliation comparand and the `unabsorbed_loop_back` under-count |
| `work/metrics.toon` | top-level `partial`, `unrecorded_phases` | the `omitted_row` under-count and the floor label |
| `work/metrics-dispatch-boundaries-{phase}.toon` | the `total_tokens` and four context-load columns, summed per phase | the same-population reconciliation (see below) |

The per-phase fields are written by `manage-metrics enrich` from the transcript
engine's `message.usage` four-field walk and its tool-call walk; the ledger rows
are written by `manage-metrics record-dispatch-boundary`, one per dispatch
termination. See `manage-metrics/standards/data-format.md` § Per-Phase Fields,
§ Billing weights, and § Per-Dispatch Context-Load Attribution for the field
definitions.

### Corpus partition (delivery-cost check)

This check runs over the SHIPPING partition of the corpus, not every scanned
plan: its figures are cost-composition ratios, so a plan that consumed budget and
delivered nothing would dilute every one of them. A plan carrying no delivery
evidence — no PR record and no footprint — is excluded before the check sees it.
See SKILL.md § "Shipping-predicate corpus partition" for the derived predicate.

**Two independent exclusions, never merged.** This check reports two exclusion
sets and they count different things:

| Exclusion | Columns | Reason a plan lands here |
|-----------|---------|--------------------------|
| Non-shipping | `plans_excluded_non_shipping` / `excluded_non_shipping_plan_ids` | The plan delivered nothing, so it is out of the delivery-cost corpus regardless of what it measured. |
| Absent counters | `plans_excluded_no_counters` / `excluded_plan_ids` | The plan measured neither family, so it cannot be read as a zero composition. See the next section. |

The non-shipping partition is applied first, so a plan excluded as non-shipping
never reaches the absent-counter test.

## Absent is not zero — and a population is per FIGURE, not per block

**A plan measuring neither family is EXCLUDED from the corpus and named in
`excluded_plan_ids`. It is never admitted at a zero share**, which would invent a
maximally-favourable composition out of the absence of any measurement. A
**measured** zero is a real observation and stays in.

The two families are independent, and this is the reason each figure carries its
own population rather than the block carrying one corpus size:

- a plan archived **before** the payload-byte counters existed carries the
  billing four-field view but no bytes — it contributes to the billing figures
  and to none of the byte figures;
- a plan run on a target that **declines** the transcript primitive carries
  neither and is excluded outright.

Reading a byte share against the block's plan count would therefore overstate the
population behind it. `population` on each figure row is the number of plans that
contributed to **that** figure.

## The reconciliation (why this is not a re-read of the phase rows)

Each phase is reconciled against the plan's dispatch-boundary ledger under the
same rule `cmd_generate` applies (`data-format.md` § Dispatch-Boundary
Reconciliation):

```text
reported = max(row_value, dispatch_boundary_total)      # NOT a sum
```

The per-phase accumulator and the boundary ledger record the **same population** —
every dispatched leaf appears once in each — so summing would double-count every
leaf, while `max()` recovers the under-count that arises when a leaf's
`record-dispatch-boundary` fired but the accumulator fold was missed.

The ledger's four context-load columns carry the same four-field view the phase
row does, so the identical rule extends to every field the billing formula
consumes. In the healthy case the phase row is already the larger value — the
`enrich` four-field walk covers the parent orchestrator turns too, which the
ledger rows do not — so `max()` is a no-op and fires only on the under-count it
exists to recover. A phase where it did fire is named in the row's
`reconciled_phases` cell.

An absent ledger file is a clean no-op (`max(row, 0) == row`), exactly as it is
generate-side.

## The two named under-counts

They are reported in **separate columns** and counted in separate block-header
lines. They are different facts with different readings and MUST NOT be collapsed
into one "incomplete" verdict.

| Under-count | Fires when | Reading |
|-------------|-----------|---------|
| `unabsorbed_loop_back` | a phase row carries `close_count > 1` | `close_count` is the authoritative, inference-free re-entry marker. That row's figures are **sums across closes**, so the plan's absolute reconstruction covers more than one entry. The composition SHARES stay meaningful (both numerator and denominator accumulated together); the absolute `billing_total` does not describe a single pass. |
| `omitted_row` | a canonical phase is absent from `metrics.toon` — a member of the persisted `unrecorded_phases`, or a phase with no section at all | That phase's billing weight and payload bytes are missing outright, so every figure the plan contributes to is a **floor**. Both sources are consulted so a plan predating the `#812` partiality markers is still caught structurally. |

## Emitted figures

| Figure | Unit | Definition |
|--------|------|-----------|
| `billing_weighted_total_reconstructed` | `weighted_tokens` | The corpus billing-formula reconstruction: `input + output + round(0.1 × cache_read) + round(1.25 × cache_creation)`, summed over the contributing plans. The same `round()` the producer applies, so the re-derivation matches it rather than approximating it. |
| `billing_share_cache_read_input_tokens` | `share` | The weighted `cache_read` part's share of the reconstruction. |
| `billing_share_cache_creation_input_tokens` | `share` | The weighted `cache_creation` part's share. |
| `billing_share_output_tokens` | `share` | The `output` part's share. |
| `byte_share_exploration` | `share` | Exploration result bytes as a share of ALL observed payload bytes. |
| `byte_share_work` | `share` | Work result bytes, same denominator. |
| `byte_share_execute` | `share` | Execute result bytes, same denominator. |
| `byte_share_orchestration` | `share` | Orchestration result bytes, same denominator. |

`input_tokens` carries no share of its own: it is the complement of the three
named billing parts, so naming it would restate a derivable number rather than
add one.

**The byte denominator is ALL FIVE buckets, residual included.** The four named
shares are shares of the whole observed payload population, not of a flattering
subset. The fifth bucket (`unclassified` — the fail-open bucket the transcript
engine's classifier routes an unrecognised tool name into) is emitted as the
per-plan `residual_bytes` count alongside `denom_bytes` rather than as a named
share, so no observed byte is silently dropped from a composition it is not named
in, and a reader can verify the four shares plus the residual account for the
whole.

This denominator deliberately DIFFERS from `exploration-share`'s, which excludes
`orchestration` and `unclassified` to keep its ratio from moving when the
workflow machinery changes. That check measures *behaviour*; this one measures
*composition*, so it must account for every byte. Do not compare the two checks'
byte shares directly.

### Every figure carries its population and its floor label

| Column | Meaning |
|--------|---------|
| `population` | How many plans contributed to THIS figure. Never the block's corpus size. |
| `floor_population` | How many of those contributing plans are floored (see below). |
| `label` | `floor` when `floor_population > 0`, else `measured`. |

A plan is **floored** when the `input-integrity` check marks it `metrics_blind`,
when its `metrics.toon` carries the `#812` `partial` verdict, or when it has an
`omitted_row`. The floor verdict is CONSUMED from `input-integrity` rather than
re-derived here — that check is the engine's no-false-healthy foundation and
stays the single source of the blind verdict.

**A `floor`-labelled figure is a lower bound, not a truth.** It was computed over
at least one plan whose inputs are under-recorded, so the real value is at least
the reported one and the gap is unquantified. Read it as "at least X", never as
"X".

## Emitted columns

```
exclusion_rule: …
reconciliation_rule: per phase, reported = max(row_value, dispatch_boundary_total) — NOT a sum …
byte_denominator: all 5 buckets; the unclassified residual is emitted as residual_bytes rather than as a named share
plans_in_corpus: K
plans_excluded_no_counters: X
excluded_plan_ids: id;id;…
unabsorbed_loop_back_plans: A
omitted_row_plans: B
reconciled_plans: C
genuine_signal_count: G
figures[F]{figure,unit,value,population,floor_population,label}
rows[K]{plan_id,billing_total,cache_read_share,cache_creation_share,output_share,exploration_byte_share,work_byte_share,execute_byte_share,orchestration_byte_share,residual_bytes,denom_bytes,reconciled_phases,unabsorbed_loop_back,omitted_row,label,severity}
```

| Row column | Meaning |
|------------|---------|
| `plan_id` | The scanned plan's directory basename (rows sorted by `billing_total`, desc). |
| `billing_total` | This plan's reconciled billing-formula reconstruction. |
| `cache_read_share` / `cache_creation_share` / `output_share` | The plan's own billing composition, or `n/a` when its reconstruction is 0. |
| `{source}_byte_share` | The plan's own payload-byte composition, or `n/a` when it observed no bytes. |
| `residual_bytes` | The `unclassified` residual — the explicit unknown, never folded into a named share. |
| `denom_bytes` | All five buckets summed: the denominator the four shares are taken over. |
| `reconciled_phases` | `;`-joined phases where the ledger reconciliation actually corrected an under-count. Empty is the healthy case. |
| `unabsorbed_loop_back` | `;`-joined phases with `close_count > 1`. |
| `omitted_row` | `;`-joined canonical phases missing from `metrics.toon`. |
| `label` | `floor` when this plan's inputs are under-recorded, else `measured`. |
| `severity` | Uniform severity column — see below. |

`severity` is `genuine` when the row carries ANY of `unabsorbed_loop_back`,
`omitted_row`, `reconciled_phases`, or a `floor` label; `informational` when the
plan is fully recorded and needed no correction.

### Corpus-partition exclusion columns

Two further block-header lines carry the non-shipping exclusion — the OTHER
exclusion set, counting a different thing from `plans_excluded_no_counters`:

| Line | Meaning |
|------|---------|
| `plans_excluded_non_shipping` | How many scanned plans were excluded as non-shipping — reported SEPARATELY from `plans_in_corpus` and from `plans_excluded_no_counters`. |
| `excluded_non_shipping_plan_ids` | The excluded plans, each as `{plan_id}:{archived_reason or unrecorded}`. |

## How the orchestrator interprets the rows

EVERY emitted row is adjudicated with a stated verdict and cited evidence; a row
may be dismissed as informational/expected ONLY with a cited reason.

- **A `floor`-labelled figure** — read and quote it as a lower bound, never as a
  measurement. Naming the floor is mandatory: the honest phrasing is "at least X
  over N plans, of which F are floored", not "X". This is the same obligation
  `input-integrity` imposes corpus-wide, applied to this check's own product.
- **`unabsorbed_loop_back` (genuine)** — the plan's composition SHARES are still
  readable (numerator and denominator accumulated together), but its absolute
  `billing_total` covers more than one pass through the phase. Do not quote that
  plan's absolute figure as a per-run cost. Cross-read the plan's `close_count`
  phases against its `metrics` row before drawing any per-phase conclusion.
- **`omitted_row` (genuine)** — the plan is missing a canonical phase outright.
  Every figure it contributed to is a floor. Name the missing phases; do not
  treat the plan's composition as complete.
- **`reconciled_phases` non-empty (genuine)** — the recorded phase row
  UNDER-COUNTED and the ledger recovered it. This is a recording-path signal, not
  a plan defect: the leaf's `record-dispatch-boundary` fired while the
  accumulator fold did not. Recurring across plans, it is a `manage-metrics`
  recording defect worth filing; on a single plan it is informational context for
  why that plan's figure moved.
- **`byte_share_exploration` (informational corpus shape)** — this is a
  composition, not a verdict. A high exploration byte share says the corpus's
  observed payload came predominantly from lookup; it says nothing on its own
  about whether that lookup was necessary. Cross-read `exploration-share` (which
  measures the behaviour against a productive denominator and carries the
  corpus-relative outlier flags) before drawing any efficiency conclusion. Note
  the denominators differ — do not compare the two numbers directly.
- **`billing_share_cache_read_input_tokens` (informational corpus shape)** — the
  share of billing weight attributable to context re-reads. A single run's value
  is a BASELINE, not a finding; the file-worthy signal is a MOVEMENT across
  successive audits, which is what this check exists to make measurable.
- **`plans_excluded_no_counters` / `excluded_plan_ids`** — the corpus-exclusion
  read-out and a floor annotation for the whole block. A corpus summary MUST NOT
  claim a composition verdict while excluded plans are unmeasured; name them.
  When exclusions outnumber inclusions the honest verdict is **"not yet
  measurable"**, which is neither a pass nor a regression.

## Critical rules

- The script is the single source of truth for every per-plan number and every
  corpus figure. Do not re-read `metrics.toon` or re-derive a share in chat — a
  hand-derived composition figure is exactly what this check replaces.
- **This check produces MEASUREMENT ONLY.** It quantifies no saving, projects no
  saving, and combines no dispatched-plus-inline token populations into a
  headline figure. A reading that converts a share into an avoided-cost estimate
  is outside this check's remit and unsupported by its inputs.
- **Absent is not zero.** A plan measuring neither family is excluded and named,
  never admitted at a zero share. A measured zero is a real observation and stays
  in.
- **A population is per figure.** Never quote a figure without the `population`
  and `label` on its own row; never borrow another figure's population.
- **`max()`, not a sum.** The reconciliation is non-double-counting by
  construction. Do not add a phase row to its ledger total anywhere.
- **The two under-counts stay separate.** `unabsorbed_loop_back` and
  `omitted_row` have different readings; collapsing them into one "incomplete"
  cell destroys the distinction the check exists to report.
- The four byte shares are taken over ALL five buckets. Do not re-normalise them
  over the four named sources — that would silently absorb the residual into the
  named shares.
- This check is read-only; it never edits `.plan/` files.
