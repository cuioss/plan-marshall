# Check: lane-lever-effectiveness (cross-plan)

The **checkpoint measurement arm** of the token-optimization roadmap
(`.plan/plan-optimization/HANDOVER.md`). Measures whether the cost-reducing
**lane levers** the roadmap shipped are actually being **engaged**, and scores
each plan's realized token spend against the **armed per-scope-class checkpoint
targets**. Rather than inferring cost health from generic symptoms, this check
directly verifies the mechanics the roadmap introduced to reduce spend:

- **recipe auto-routing** — a plan seeded from a recipe / lesson (#811
  lane-selection) that skipped the full planning ceremony.
- **the light planning lane** — `planning_lane == "light"` (bounded, localized
  changes route to the light outline lane).
- **the minimal execution posture** — `execution_profile == "minimal"` (the
  posture that subtracts review / sub-agent elements).
- **the #854 surgical-fix micro-lane** — the fast path that recommends the
  minimal posture for a bounded surgical-scope, concrete request.

The deterministic computation lives in `scripts/audit.py`
(`cross_lane_lever_effectiveness` / `emit_lane_lever_effectiveness_block`); this
sub-document is the interpretation guide. It is a **cross-plan** check: it
aggregates the whole corpus into per-checkpoint-class spend verdicts plus
corpus-wide lever-engagement counts.

## Inputs the check reads

All inputs are per-plan (no global logs):

| Input | Source | Used for |
|-------|--------|----------|
| `scope_estimate` | `references.json` | checkpoint class + armed target |
| summed `total_tokens` | `work/metrics.toon` (sum over recorded phases) | the measured spend — see § "What population the targets score" |
| `recipe_key` / `plan_source` | `status.json::metadata.plan_source` | recipe auto-route HIT |
| `planning_lane` | `status.json::metadata.planning_lane` | light-lane fire (`== "light"`) |
| `execution_profile` | `status.json::metadata.execution_profile` | chosen posture; `minimal` is the cost-reducing lever |

### Corpus partition (delivery-cost check)

This check runs over the SHIPPING partition of the corpus, not every scanned
plan: a plan carrying no delivery evidence — no PR record and no footprint — is
excluded before the check sees it, so a plan that burned budget and delivered
nothing cannot be scored against a delivery checkpoint target. See SKILL.md §
"Shipping-predicate corpus partition" for the derived predicate.

## Armed checkpoint targets

A plan's `scope_estimate` maps to its checkpoint class and the armed total-token
target (the roadmap's optimization checkpoint, sourced from the single
`THRESHOLDS["checkpoint_token_targets"]` table — no inline duplication):

| Checkpoint class | Armed target |
|------------------|--------------|
| `surgical` | ≤ 1.2M tokens |
| `single_module` | ≤ 1.5M tokens |
| `multi_module` | ≤ 2.5M tokens |

A `scope_estimate` outside this map (e.g. `broad`) is `unclassed` — measured but
carries no verdict.

### What population the targets score

The measured spend is `metrics.toon` `total_tokens`, read under its
**default-plus-exception** population labelling — the same contract the rendered
`Tokens (dispatched unless marked)` column declares:

- **Default** — a phase row is a **dispatched-subagent** measurement.
- **Exception** — a row whose `total_tokens_population` is `inline` is a
  **main-context-window** measurement that `manage-metrics enrich` folds in
  because the phase dispatched nothing. A row marked `mixed` is still the
  dispatched figure, with its inline spend excluded.
- **The sum** — a sum containing an `inline` row therefore **spans populations**
  and is not a dispatched total. Read the report's `(spans populations)` marker
  before describing a checkpoint verdict as a dispatched-work verdict.

`billing_weighted_total` (the `Billing (cost)` column) is a **derived-cost**
measure of what the phase cost to buy. It answers a different question from the
dispatched work these targets score and is **never** summed into the measured
spend. The full contract lives in
`manage-metrics/standards/data-format.md` § "Default-plus-exception labelling of
the `Tokens` column".

### Re-derivation outcome: ZERO delta

The armed targets above were re-derived against that measured population and **no
value moved**. The reason is structural, not an omission: the plan that
introduced the population labelling deliberately **retained** the inline fold (it
is what keeps a zero-dispatch phase countable, and five consumers are load-bearing
on it), so the population these targets score is exactly the population they
scored before — only its labelling changed. Moving them down would have required
inventing a reduction factor for an exclusion that never occurred.

Consequently this check's `CHECK_ERA` boundary is **deliberately not bumped** for
that plan: every archived plan's checkpoint verdict is bit-identical across it, so
a bumped stamp would falsely claim that pre-boundary rows read as era-expected and
post-boundary ones as regressions. Re-open the calibration only if the inline fold
is ever actually removed.

## Computation and verdicts

Per plan the script computes the checkpoint **verdict** and the lever-adoption
columns:

| Verdict | Meaning |
|---------|---------|
| `within` | Summed `total_tokens` ≤ the class target. |
| `over` | Summed `total_tokens` > the class target — the genuine overspend signal (`checkpoint_over`). |
| `unclassed` | `scope_estimate` is outside the armed set — no target to score against. |
| `no_metrics` | No recorded `total_tokens` (metrics-blind plan) — the spend is unmeasured. |

| Column | Meaning |
|--------|---------|
| `recipe_routed` | The plan was seeded from a recipe / lesson (`plan_source` present). |
| `lane` | The planning lane the router resolved (`light` / `deep`). |
| `posture` | The execution posture the plan ran (`minimal` / `auto` / `full`). |
| `posture_not_taken` | A surgical-scope plan (the micro-lane recommends `minimal`) that ran a non-minimal posture — an informational lever-adoption gap. |
| `lever_engaged` | Any cost-reducing lever fired for this plan (recipe route OR light lane OR minimal posture). |
| `avoided_tokens` | Scope-gated subtraction estimate — see below. |

### `avoided_tokens` — the scope-gated subtraction estimate

For a plan where a cost-reducing lever **was engaged** AND that came in **under**
its class target, `avoided_tokens` is the headroom kept under target
(`target − total_tokens`). It is an **upper-bound** estimate of the tokens the
engaged lever helped avoid — it credits the lever with the full headroom, so read
it as a ceiling, not a precise attribution. Zero when no lever engaged or the plan
overspent. Summed corpus-wide into `estimated_avoided_tokens`.

## Emitted columns

```
plans_measured: P
recipe_routed: R
light_lane_fires: L
minimal_posture_chosen: M
posture_not_taken: N
checkpoint_over: O
estimated_avoided_tokens: A
surgical_over: x/y (target 1200000)
single_module_over: x/y (target 1500000)
multi_module_over: x/y (target 2500000)
rows[K]{plan_id,scope,checkpoint_class,target,total_tokens,verdict,recipe_routed,lane,posture,posture_not_taken,lever_engaged,avoided_tokens,flags,severity}
```

| Column | Meaning |
|--------|---------|
| `flags` | `checkpoint_over` when the plan overspent its target, else empty. |
| `severity` | Uniform D1 severity column: `genuine` when `checkpoint_over` fired, else `informational`. |

### Corpus-partition exclusion columns

Two further block-header lines accompany the block above:

| Line | Meaning |
|------|---------|
| `plans_excluded_non_shipping` | How many scanned plans were excluded from this check's corpus as non-shipping — a number reported SEPARATELY from `plans_measured`. |
| `excluded_non_shipping_plan_ids` | The excluded plans, each as `{plan_id}:{archived_reason or unrecorded}`. |

An excluded plan delivered nothing, so it is absent from this check's aggregates
by design; the count is the audit trail proving no row was silently dropped.

## How the orchestrator interprets the rows

- **`checkpoint_over` (`severity: genuine`)** — the plan spent MORE than its
  armed class target. This is the primary actionable signal: a plan whose scope
  class had a cheap lane available yet still overspent. Read against the
  `posture` / `lane` / `recipe_routed` columns to see whether the levers were
  even engaged.
- **`posture_not_taken` on a surgical plan** — the #854 micro-lane recommends the
  minimal posture for surgical scope; a surgical plan that ran `auto` / `full`
  did not take the recommended lever. Informational (not genuine) — a
  lever-adoption gap worth noting, especially when it co-occurs with
  `checkpoint_over`.
- **low `recipe_routed` / `light_lane_fires` / `minimal_posture_chosen` across
  the corpus** — the levers are armed but under-used. Surface as a
  lever-adoption observation (the machinery exists but plans aren't routing
  through it), not a per-plan fault.
- **`no_metrics` verdict** — the plan's spend is unmeasured (metrics-blind); its
  checkpoint verdict is a floor, not truth. Consume the `input-integrity`
  verdict before trusting any spend conclusion for that plan.

The `cross-check-synthesis` coupling `surgical_overpay` joins `checkpoint_over`
with token-economics `big_spend_tiny_footprint` — see
[`cross-check-synthesis.md`](cross-check-synthesis.md). A plan carrying both is a
clear lane-lever MISS: the cheap lane existed to keep it small and it overspent
anyway.

Per the SKILL.md Step-3 contract, EVERY emitted row is adjudicated with a stated
verdict and cited evidence; a row may be dismissed as informational/expected ONLY
with a cited reason (e.g. "within target, minimal posture engaged — the lever
worked").

## Critical rules

- The script is the single source of truth for the checkpoint targets
  (`THRESHOLDS["checkpoint_token_targets"]`) and the per-plan verdict. Do not
  re-derive spend or targets in chat.
- The `avoided_tokens` estimate is an explicit UPPER BOUND (full headroom
  credited to the engaged lever). Never report it as a precise saving.
- The measured spend sums `total_tokens` and ONLY `total_tokens`. Never fold the
  derived-cost `billing_weighted_total` into it — that would mix a cost
  population into a work total and inflate every checkpoint verdict.
- Never describe a checkpoint verdict as a *dispatched* spend verdict without
  checking the report's population markers first: a sum containing an `inline`
  phase row spans populations.
- This check is read-only; it never edits `.plan/` files.
