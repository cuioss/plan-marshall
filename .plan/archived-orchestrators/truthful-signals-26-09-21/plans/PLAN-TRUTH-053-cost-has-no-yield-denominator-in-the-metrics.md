> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-055`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-053: cost has no yield denominator — `metrics.md` reports a numerator and calls it a measurement

epic: truthful-signals
workstream: WS-01

⭐⭐ **OPERATOR DIRECTIVE, 2026-08-03**: *"add the quality metric (fixed / accepted / refused) to the
metrics. If done correctly, this is a plain script call."* ⇒ **Both halves verified first-party. The
design is decided; this plan implements it.**

## Objective

`metrics.md` reports tokens, duration, tool_uses — **all numerators**. On their own they support exactly
one verdict, *"this got more expensive"*, and **that verdict is routinely wrong about what matters.**

⇒ Give the metrics a **yield denominator**, so cost is expressible as **cost per unit of retained
value** rather than cost.

## ⛔ Why this is urgent rather than nice: our roadmap cannot currently tell a saving from a scope cut

`roadmap-token-reduction.md` sizes every lever as a **share of measured spend**. ⛔ **A lever that cuts
cost and cuts yield proportionally would be reported by our instrument as a WIN.**

⭐ **`code-intelligence-substrate` measured exactly this inversion** (`-018` § 2, from an effort-level
natural experiment): **cost rose and yield rose more, so cost-per-defect-found IMPROVED while cost
increased.** A reader given only the cost number *"would have concluded the opposite of the truth,
confidently, and would have proposed a fix that made things worse."*

⇒ ⛔⛔ **Their derived anti-goal binds this epic's roadmap**: *do not propose lowering effort levels as a
token saving.* It is the one intervention that **improves the token number while degrading defect
detection** — it would make both epics' instruments report success for a quality regression. **Reject it
on that ground, not by weighing it against a projected saving.** ⭐ The legitimate target is unchanged:
**bytes that buy nothing** — redundant exploration, re-read documents, unscoped re-sweeps. **Never
examination depth.**

## ✅ OBSERVED — the operator's "plain script call" is correct, verified first-party

`manage-findings list` **already exposes the exact filter**:

```text
--resolution {pending,fixed,suppressed,accepted,taken_into_account,rejected}
--plan-id, --type, --author, --bot-kind {coderabbit,pr-agent,sourcery}, --kind, --include-qgate
```

⇒ **The data exists, is plan-scoped, is already typed, and is queryable today.** No new store, no new
schema, no new producer. ⭐ **This is a routing/derivation gap, not a modelling problem** — the same
shape as `PLAN-TRUTH-050`'s, and the reason both are cheap.

⚠ **`review-retrospective` already computes a richer version of this per REVIEWER** —
`reviewers[]{raw_total, actionable_count, meta_count, fixed, accepted, taken_into_account, rejected,
suppressed, pending, resolved_actionable_count, actionable_fixed_count, pct_resolved_as_fixed}`.
⛔ **Do NOT duplicate it.** The gap is that it lives in a **review artifact, per reviewer**, and nothing
carries a **plan-level** yield figure into `metrics.md` where the cost numbers are. **Reuse its
definitions verbatim** — two independent definitions of "resolved" is how a field acquires two
producers (`PLAN-TRUTH-049`).

## ⛔ The directive names three buckets; the enum has SIX, and the distinction is load-bearing

`fixed / accepted / refused` maps onto a six-value enum, and **"refused" is not one value but two with
opposite meanings**:

| Resolution | Means | Counts as yield? |
|---|---|---|
| `fixed` | real, and acted on | ✅ **yes — the strongest signal** |
| `accepted` / `taken_into_account` | real, acknowledged without a code change | ✅ yes, weaker |
| `suppressed` | **real, deliberately not actioned** | ⚠ yes — a true finding |
| `rejected` | **refuted as a FALSE POSITIVE** (`ext-point-verify`) | ⛔ **NO — this is the noise term** |
| `pending` | not yet triaged | ⛔ neither — **and it must not silently become a zero** |

⇒ ⛔⛔ **Collapsing `suppressed` and `rejected` into one "refused" bucket destroys the measurement's
whole point.** `suppressed` is a true finding we chose not to action; `rejected` is a finding that was
wrong. **The noise test below is exactly the ratio between them**, so merging them makes the instrument
unable to answer the question it exists to answer.

⭐ **Recommendation, and the reason stated so it can be overruled**: implement the **six-value enum**,
and let the *presentation* collapse to three if that reads better. **A collapse in the renderer is
reversible; a collapse in the data is not.**

## ⭐ The noise test — the deliverable that makes this more than bookkeeping

From `-018` § 3, and neither epic had seen it stated anywhere:

> **If extra depth were producing noise, the SHARE of findings actually acted on would FALL as the
> count rose. If the share RISES with the count, the additional findings are not noise.**

⇒ **The count and the share move together only when the new material is real.** ⭐ This is the only
cheap answer to *"it just found more noise"*, and it is unanswerable from raw counts — **which is
precisely what we publish today.** It directly serves `PLAN-TRUTH-048` (is the extra self-review round
worth it) and `PLAN-CIS-031`.

## Deliverables

1. **D0 — GATE: reuse, do not re-derive, the resolution semantics.** Read `review-retrospective`'s
   definitions (`resolved_actionable_count`, `actionable_fixed_count`, `pct_resolved_as_fixed`) and
   `manage-findings`' enum, and state **one** definition of yield used by both. ⛔ **Two definitions of
   "resolved" is a two-producer defect waiting to happen.** ⚠ Confirm whether Q-Gate findings
   (`--include-qgate`) are in or out of the denominator — **it changes every ratio, and the answer must
   be stated, not defaulted.**
2. **D1 — `metrics.md` carries the yield block**, per plan: counts for all six resolutions, plus the
   derived cost-per-unit figures the roadmap needs. **Plain `manage-findings list` calls**, per the
   operator's read.
3. **D2 — `pending` and an empty finding-set must NOT render as zero yield.** ⛔ **This is the epic's own
   archetype and the highest risk in the plan**: a plan with no findings and a plan whose findings were
   never triaged would otherwise both publish *"yield: 0"* — **cost-per-defect of infinity, reported as
   a measurement.** ⭐ `review-retrospective` already sets the precedent: it renders
   `pct_resolved_as_fixed` as **`n/a`, never `0%`**, and **puts the denominator beside it**. **Copy that
   exactly.**
4. **D3 — the noise-test ratio is a first-class output**: the actioned SHARE alongside the count, so
   "found more" can be distinguished from "found more noise" without re-deriving it per question.
5. **D4 — tests, each verified to FAIL pre-fix.** (a) A plan with zero findings renders `n/a`, not `0`.
   (b) A plan with only `pending` findings renders `n/a`, not `0`. (c) `suppressed` and `rejected` are
   counted separately and never summed into one bucket. (d) The yield definition is asserted identical
   to `review-retrospective`'s — **a shared-definition pin, not two copies.**

⚠ Five deliverables. **D3 is the split point.** Kept because it is one derived field over D1's data and
splitting it would leave the plan delivering counts nobody can interpret.

## Claim Labels

- **OBSERVED (this orchestrator, first-party)**: the `manage-findings list --resolution` surface and its
  six values; `review-retrospective`'s `reviewers[]` field list and its `n/a`-never-`0%` rule;
  `rejected` being set by `ext-point-verify` when it refutes a finding.
- **OPERATOR DIRECTIVE (not a hypothesis)**: that the quality metric belongs in the metrics, and that it
  should be a plain script call. ✅ **Both verified; recorded as confirmed, not merely accepted.**
- **REPORTED (sibling `-018`, method not data)**: the cost-rose-yield-rose-more result and the noise
  test. ⚠ **They explicitly withheld the figures and flagged their own limits** — small after-group, the
  two periods differ in more than one variable, and the per-item trade-off *"internal yield up ⇒ external
  yield down"* **does NOT hold at the item level**, only the group means move oppositely. ⛔ **Take the
  METHOD; do not build on the magnitude without re-deriving it.**
- **HYPOTHESIS**: findings resolution is complete by `record-metrics` (order 998). ⚠ **Post-merge triage
  exists** (`PLAN-102` shipped it) ⇒ **a metric sampled at 998 may under-count later resolutions.**
  ⛔ **This is `PLAN-TRUTH-035`'s sampling-point defect arriving in a new field before it is even
  built** — D0 must state the sampling point in the output, or this plan reproduces the defect it is
  adjacent to.

## Expected Surface

- **OBSERVED**: `manage-findings/scripts/` — `list --resolution`
- **OBSERVED**: `.claude/skills/finalize-step-review-retrospective/SKILL.md` — the definitions to reuse
- **HYPOTHESIS**: `manage-metrics` — `generate`, the `metrics.md` renderer
- **HYPOTHESIS**: `roadmap-token-reduction.md` consumers — the cost-per-yield figures

## Dependencies and Sequencing

- ⛔ **`PLAN-TRUTH-035` is RUNNING on `manage-metrics` — SAME SURFACE. SERIALIZE; do not pair.**
  ⭐ Sequence **after** it: 035 settles which population a `metrics.md` number describes, and adding a
  new number before that is adding a second unlabelled partition.
- ⚠ **`PLAN-TRUTH-048`** (self-review priced but not scoped) **is the first consumer** — its "is the
  extra round worth it" question is unanswerable without D3. **Cite; do not merge.**
- ⚠ Cross-epic: **`PLAN-CIS-030`** (measurement) and **`PLAN-CIS-031`** (self-review delta-scoping) need
  the same denominator. **Notify — a shared definition, not two.**
- ⚠ `PLAN-TRUTH-050` D6 classifies report-vs-inbox facts; the yield block is a strong candidate for the
  terminal emission. **Evaluate at 050's outline.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-053-cost-has-no-yield-denominator-in-the-metrics.md"
```

## ⛔ SEQUENCING 2026-08-08 — this plan is THIRD in a three-plan `manage-metrics` chain

`manage-metrics` now carries three staged plans plus one shipped. Landing them in any other order
re-creates work:

1. **`PLAN-TRUTH-055`** (a re-entered phase cannot be represented) — **already emitted.** It supplies
   the population vocabulary and fixes the row model. Two `code-intelligence-substrate` plans also
   wait on it.
2. **`PLAN-TRUTH-066`** (the retrospective reads a record that is not yet written) — reconciles the
   two disagreeing phase-6 ledgers and the regenerate-after-loop-back path.
3. **THIS PLAN** — adds the yield denominator. It is last because a denominator computed over a row
   model that cannot represent a re-entered phase (055) and read from a record written after its
   reader (066) would be **a ratio built on both defects**.

⛔ **DO NOT PAIR any two of the three** — one module, one renderer.

⚠ **Already recorded and still binding**: this plan is the SAME SURFACE as the shipped
`PLAN-TRUTH-035` (the metrics renderer). **State its sampling point explicitly**, or it reproduces
035's defect in a new field — 035's whole finding was a figure that did not say which population it
came from.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
