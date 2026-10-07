# Design Outline — Execution-Profile Lane Selection (init-phase)

**Status: LANDED — SHIPPED as PR #811 (2026-06-30)**, with two known landing defects tracked in
[`../HANDOVER.md`](../HANDOVER.md): the §4.6 posture dialogue shipped **inert** inside the dispatched
init leaf (fix in flight: plan `fix-execution-profile-posture-dialogue`; made fully native later by
`../plans/plan-5-inline-init.md`), and the §4.8 routing-decisions retrospective aspect shipped
**non-rendering** (missing SECTION_SPEC row → `../plans/plan-2-routing-render.md`). This document
remains the design reference; the text below predates the ship.
Companion to the token analysis in
[`03-synthesis-optimal-path.md`](../03-synthesis-optimal-path.md) — this is the operator-facing mechanism
that turns the analysis's "right-size the pipeline" recommendation into a concrete, cost-visible
decision at init.

## 1. Motivation

From the token analysis:

- **~73% of every plan's tokens are framework overhead around the edit** — planning 35.9% + finalize
  36.8%; execute (the actual edits) is the *smallest* macro-bucket at 27.4%.
- **A hard ~1.0M-token floor** — even a 20-LOC fix paid ~1.0M tokens.
- **The value split is sharp.** *Adversarial validators* (outline scope-validator, automated-review,
  self-review, security-audit-as-finder) find real defects and earn their cost; *transform/confirm
  steps* on inputs that don't need them (refine on a complete spec, sonar/lessons-housekeeping with a
  structurally-empty output) are near-pure overhead.

The synthesis conclusion: *"the operator should be able to see the ~100x cost multiplier before
committing a trivial task to the deep lane."* This feature is that visibility plus the lever to act on
it.

## 2. The operator-facing decision

At init, after classification, the dialogue presents a **lane / execution-profile** posture:

| Posture | Intent | Composition |
|---------|--------|-------------|
| **auto** (recommended) | Computed per change-type + thresholds over the project's *configured* steps. | Keeps adversarial validators; prunes structurally-empty prunable steps. |
| **minimal** | Operator accepts the risk; mechanical / low-stakes change. | The tier-`minimal` floor (§4.1 default table): sync-baseline · PR · ci-verify · lessons-capture · lessons-housekeeping (smart-skips when no lesson touched) · branch-cleanup · record-metrics · archive (+ meta derived-state: deploy-target, sync-plugin-cache). No adversarial steps, no security-audit, no retrospectives; plus any step the operator pins. |
| **full** | Every configured step. | The full deep-lane behavior. |

Two requirements:

1. **The dialogue shows concrete consequences** — exactly which steps each posture runs (§4.6).
2. **A config knob (`lane_selection: ask | auto`, default `ask`) decides whether to prompt or take
   `auto` silently.**

## 3. What it builds on (existing machinery, confirmed in code)

- **recipe-match** (`phase-1-init` Step 5c): already gates *auto-route vs. prompt-the-user* via
  `auto_route_recipe` (default `true`) + a confidence threshold — the ask/auto-with-preview pattern
  this feature mirrors.
- **planning-lane** (`phase-1-init` Step 8b): `evaluate_signals_pure(...)` in
  `manage-status/scripts/_cmd_planning_lane.py` scores signals S1–S6 → `{light, deep}`, persisted to
  `status.metadata.planning_lane`. Has `deep_lane: auto|always|never` and a one-way
  `planning_lane_override`. Its docstring states it exists *"so the routing thresholds are never
  duplicated"* (the audit check already imports it).
- **manifest composer** (`manage-execution-manifest`): already projects a concrete step set from the
  `marshal.json` keyed-map, and already prunes steps from a classification (aspect-classify "drops
  build / quality-gate / test steps for analysis/planning requests").
- **Re-route with firmer signals already happens**: the init router is conservative (unknown signals →
  deep) and "the light lane is confirmed once the orchestrator re-routes with the full signal set."

## 4. Design

### 4.1 Per-element lane contract (the core mechanism)

Every phase/step element **self-declares its lane membership** via a frontmatter contract;
`minimal`/`auto`/`full` are *postures* (cutoffs) over those self-classifying elements. This keeps the
posture→steps mapping derived (not a maintained list) and reuses the existing nested-step-config +
`implements:`/`mode:` archetype model.

> **Overriding principle — everything is configurable (user decision wins).** The contract supplies
> *defaults*. No classification is a hard lock: whether an element sits at the `minimal` floor, `auto`,
> or `full`, an explicit project/user config override always wins. For correctness-critical elements
> (`derived-state`) a weakening override surfaces a loud **warning** but is still honored — the operator
> decides, the system informs. (This matches plan-marshall's config-controlled posture elsewhere — obey
> the knob, don't impose a separate hard rule.)

Each element declares one block:

```yaml
lane:
  class: derived-state | core | adversarial | prunable
  tier: minimal | auto | full            # optional — defaults from class
  prunable_when: <predicate-id>          # required for class: prunable; ignored otherwise
```

`class` is the primary declaration; `tier`/`prunable_when` default from it. Class → defaults:

| class | default tier | prunable? | examples |
|-------|--------------|-----------|----------|
| **derived-state** | minimal | no — override emits a correctness **warning** (present only where the steps exist) | deploy-target, sync-plugin-cache |
| **core** | minimal | no | push, create-pr, ci-verify, branch-cleanup, record-metrics, archive |
| **adversarial** | auto | no | outline scope-validator (first pass), automated-review, self-review, security-audit-as-finder |
| **prunable** | auto | yes — via `prunable_when` | sonar-roundtrip, lessons-housekeeping, refine, 4-plan decomposition |

`minimal` is the **floor** of the lattice `minimal ⊏ auto ⊏ full`. A `minimal`-tier element runs under
every posture (it is the leanest posture an operator can pick), so the `core`/`derived-state` elements
are on by default in all three lanes — that is how "archiving is always part of the plan" holds without
a dedicated `always` level.

**Per-element override knob** (nested in `marshal.json`, like finalize-step params) pins any element —
value ∈ `off | minimal | auto | full | ask` (`off` = never run; `minimal` = force-keep in every
posture; `ask` = always prompt):

```json
"plan": { "phase-6-finalize": { "steps": {
  "sonar-roundtrip":    { "lane": "minimal" },    // promote: force-keep in every posture
  "plan-retrospective": { "lane": "full" },        // only at full
  "security-audit":     { "lane": "ask" }           // always prompt for this one
}}}
```

**Resolution (per element, at manifest composition):**

1. effective tier = per-element override (marshal.json) ▸ else declared `lane.tier` ▸ else class
   default — an explicit override always wins, including an `off` that drops a `derived-state`/`core`
   floor element (which additionally emits a correctness warning, but is honored);
2. element **runs iff** `tier ⊑ posture` on `minimal ⊏ auto ⊏ full` (posture = the init-chosen global
   preset);
3. if effective tier is `ask` → surface this element individually in the dialogue;
4. if class == `prunable` **and** `prunable_when` holds at firm-signal time → skip even when
   `tier ⊑ posture` (the conditional pruning of §4.7 — sonar on no-code-delta, etc.); by
   default `derived-state`/`core`/`adversarial` are not predicate-demoted (an operator may still opt one
   in via config).

So `auto` = "run every element whose tier ⊑ auto, minus any prunable element whose predicate
fires"; `minimal` = "only the tier-`minimal` floor"; `full` = "everything." The §4.7 table is
the declarative set of `prunable` predicates, not a hard-coded skip list.

**Default `lane` tiers (the shipped frontmatter defaults).** `tier` is each element's explicit default
— equal to the class default except where bolded (security-audit, plan-retrospective deviate to `full`;
lessons-capture, lessons-housekeeping deviate to `minimal`):

| Element(s) | class | tier |
|---|---|---|
| init · outline · plan · execute · push · create-pr · ci-verify · branch-cleanup · record-metrics · print-phase-breakdown · archive | core | minimal |
| deploy-target · sync-plugin-cache *(meta-only)* | derived-state | minimal |
| finalize-step-sync-baseline | core | minimal |
| lessons-capture | core | **minimal** |
| lessons-housekeeping | prunable | **minimal** |
| refine · 4-plan task-decomposition · simplify · sonar-roundtrip | prunable | auto |
| outline/plan q-gate · self-review · automated-review · plugin-doctor *(meta)* | adversarial | auto |
| review-retrospective *(meta)* | prunable | auto |
| security-audit | adversarial | **full** |
| plan-retrospective *(meta)* | prunable | **full** |

`lessons-capture` and `lessons-housekeeping` at `minimal` are part of the floor (always eligible);
`lessons-housekeeping` is `prunable`, so it still smart-skips when the footprint touches no lesson's
component. `security-audit` and `plan-retrospective` only run at `full`. These shipped defaults live in
each element's frontmatter `lane:` block; `marshal.json` overrides per project (§5).

### 4.2 Profile resolution and the posture knob

- `evaluate_signals_pure` is extended to emit a `profile` projection over the signals it already
  computes; generic `auto` = that projection. Recipes also seed the profile (§4.9).
- `minimal` / `full` are overrides of the projection, modelled like the existing
  `planning_lane_override` / one-way `escalate` verbs.
- The `lane_selection: ask | auto` knob (default `ask`) lives in the `plan.phase-1-init.*` config block
  alongside `deep_lane`, matching the `finalize_without_asking` / `auto_merge_after_ci` family.
- `deep_lane: always|never` **composes** with the profile — it sets planning depth (its existing job);
  the profile independently governs finalize-step pruning. `deep_lane: always` does **not** force `full`.

### 4.3 Derivation & persistence — one script, two artifacts

The lane projection lives in `manage-execution-manifest` (the composer that already projects the step
set from the `marshal.json` keyed-map):

- **`full` and `minimal` are static** — pure config projections (`full` = every configured step;
  `minimal` = only the `core`/`derived-state` floor), needing no plan signals. `auto` is the same
  projection plus the §4.7 signal-gated predicates.
- A **`lanes preview` verb returns one TOON with all three resolved step sets**, driving the dialogue
  display and (with the `cost_size_token_table`, §4.6a) the cost preview:

  ```toon
  lanes:
    minimal:
      phase_6_steps[6]: [ push, create-pr, ci-verify, branch-cleanup, record-metrics, archive-plan ]
    auto:
      phase_6_steps[12]: [ ... ]      # full minus predicate-pruned prunable steps
    full:
      phase_6_steps[19]: [ ... ]      # every configured step
  ```

Persistence (existing division of labour):

| Artifact | Holds | Role |
|----------|-------|------|
| `status.json::metadata` | `planning_lane` + the chosen posture (`execution_profile`) + per-step `phase_steps` outcomes | the **decision** + progress |
| `execution.toon` (`.plan/local/plans/{plan_id}/`) | composed `phase_5.verification_steps` / `phase_6.steps` + `step_params` snapshot + `execution_log` | the **resolved flow** |

The posture decision is persisted to `status.json::metadata`; the resolved concrete flow is the
`execution.toon` manifest. `full`/`minimal` are not persisted — they are deterministic from config and
recomputed on demand by the same `lanes` verb, which guarantees the preview and the executed flow can
never diverge (one projection feeds both).

### 4.4 What the profile governs (planning depth AND finalize steps)

The lane today governs only planning depth (refine/outline via the planning.md lane-dispatch);
finalize-step selection is driven separately by aspect-classification in the composer. This feature
unifies both under one profile, so the profile drives:

- phase-2/3 depth (existing light/deep behavior), **and**
- phase-6 finalize-step selection (new — currently aspect-only).

The plan must wire both, or finalize stays on the aspect-only path.

### 4.5 Timing — compose at init, adapt at phase-4

The manifest is **born at init and adapted**, not born at phase-4. This co-locates the posture decision
with its materialization and makes the dialogue preview literally the persisted manifest (so
preview/execution cannot diverge for the config-only parts).

A few manifest fields are outputs of later phases and cannot exist at init:
`phase_5.verification_steps` (deliverables + domains), `phase_5.envelope_count` (task bin-packing), and
`auto`'s footprint-gated finalize prunes (sonar-skip / lessons-housekeeping-skip need the firm
`change_type`/`affected_files`). The posture and the finalize-step set are init-knowable — exact for
`minimal`/`full`, provisional only for `auto`'s footprint prunes.

Leaning on `compose` already being idempotent ("re-invocation overwrites"):

- **init**: record the posture into `status.metadata` and run `compose` to write `execution.toon` now —
  posture + finalize step set (exact for minimal/full; auto with init-time signals, footprint prunes
  provisional) + a `phase_5` placeholder. The dialogue preview is this manifest.
- **phase-4**: run `compose` again with firm signals — fill `phase_5.verification_steps` +
  `envelope_count` and re-apply `auto`'s footprint predicates. **No re-prompt.** The posture and the
  `minimal`/`full` shapes are fixed at init and never change; the only thing that can move is `auto`'s
  footprint-gated prune (e.g. sonar flips back on when the firm `affected_files` reveals a code delta the
  init guess missed). That is `auto` correcting itself with real signals, in the safe direction (more
  validation), so it is **logged** (with any cost delta), not re-approved.

### 4.6 The dialogue — concrete and quantitative

1. **Project-derived step list** — enumerate the actual configured steps (keyed-map +
   `implements:`-discovered finalizers) and show which each posture keeps/drops, e.g. *"full: 19 steps ·
   auto: 12 (skips sonar — no code-logic delta; skips lessons-housekeeping — footprint touches no lesson
   component) · minimal: 6."*
2. **Predicted cost** — computed from each resolved element's `cost_size` (§4.6a), summed via the
   `cost_size_token_table`, e.g. *"full ≈ 2.0M tok · auto ≈ 1.3M · minimal ≈ 0.9M."* This is available
   in **every** project (the table is a config default), not just the meta-project.
3. **Name what `minimal` gives up** — *"no security audit / no review retrospective — appropriate for
   docs/mechanical changes"* — so it is an informed downgrade.

### 4.6a Cost sizing — extend the existing model, don't invent one

A cost-size model already ships for **tasks**: the rubric `phase-4-plan/standards/cost-sizing.md`, the
config knob `plan.phase-5-execute.cost_size_token_table` (default `{S: 25K, M: 60K, L: 130K, XL: 260K}`,
validated in `_config_defaults.py`), and the deterministic deriver `manage-tasks derive-cost-size` with
its actual-vs-predicted calibration loop. This feature **extends that model to lane-elements** rather
than adding a parallel one:

- **Every phase / step / q-gate carries a `cost_size`** in its `lane:` frontmatter block (§4.1), on the
  existing `S/M/L/XL` scale. The dialogue cost-preview (§4.6 item 2) sums the resolved elements'
  `cost_size` through the `cost_size_token_table`.
- **Every project gets a cost preview — no corpus needed.** The table is a config default present in
  *every* project, so the preview is `Σ(element cost_size → table)` everywhere. The corpus medians are an
  optional *calibration* input, not a prerequisite.
- **The calibration loop is reused, not rebuilt.** §4.8's cost-preview-accuracy check (predicted vs
  actual from `execution_log`) feeds the *same* recalibration loop that already tunes the task table.
- **One home for the scale.** `cost-sizing.md` is promoted to the single owner of the T-shirt scale used
  by both tasks and lane-elements (a small generalization of its current task-only framing). The
  **scale is widened to six sizes** so deterministic ≈0-token steps and the heaviest elements get
  distinct labels. The central document defines:

  | size | token magnitude | covers |
  |------|-----------------|--------|
  | **XS** | ~5K | deterministic ≈0-token bookkeeping (push, branch-cleanup, archive, record-metrics, deploy-target, sync-plugin-cache) |
  | **S** | 25K | small agent steps (plugin-doctor, ci-verify) |
  | **M** | 60K | medium (init, refine, create-pr, simplify, lessons-capture, review-retrospective) |
  | **L** | 130K | heavy single steps (sonar, self-review, security-audit, automated-review, lessons-housekeeping, **plan-retrospective**, q-gate) |
  | **XL** | 260K | the planning phases (outline incl. 1st q-gate, plan) |
  | **XXL** | 520K+ | the largest elements — `execute` on a substantial plan; any element exceeding XL |

  `XS` and `XXL` are the additions to the existing `S/M/L/XL`; the four existing magnitudes are
  unchanged so the task-side deriver/bin-packer are unaffected. This widening touches `COST_SIZE_LABELS`
  + the config-table validation (§7) and is implemented with the rest of the feature, not ad-hoc.

**Prefill (default `cost_size` per element, seeded from the token analysis — order-of-magnitude):**

| Element | ~typical tokens | `cost_size` |
|---------|-----------------|-------------|
| push, branch-cleanup, record-metrics, archive, deploy-target, sync-plugin-cache | ≈0 (deterministic) | **XS** |
| plugin-doctor, ci-verify | ~40–50k | **S** |
| 1-init, refine, create-pr, simplify, lessons-capture, review-retrospective | ~50–95k | **M** |
| sonar-roundtrip, self-review, security-audit, automated-review, lessons-housekeeping, **plan-retrospective**, outline/plan q-gate | ~100–170k | **L** |
| 3-outline (incl. 1st q-gate), 4-plan | ~250–350k | **XL** |
| 5-execute | scales with the work | per-task (existing deriver); **XXL** on substantial plans |

On the unified six-size scale, `plan-retrospective` (~150–166k) is the **heaviest finalize *step*** but
lands at **L** — `XL`/`XXL` are reserved for the planning phases and `execute`, which are larger. If a
finalize-relative reading (where plan-retrospective tops the set) is wanted instead, that is a separate
per-population scale and conflicts with phases/execute sharing one axis — flagged, not assumed.

### 4.7 `auto`'s pruning rules (corpus-grounded, thresholds configurable)

`auto` keeps the adversarial validators and conditionally prunes prunable steps:

| Step | Prune when | Source signal |
|------|-----------|---------------|
| refine | confidence ≥ threshold / input is a complete spec | post-init confidence proxy |
| sonar-roundtrip | no code-logic delta (change_type ∈ {docs, tech_debt}, no production change) | footprint/aspect |
| lessons-housekeeping | footprint touches no lesson's component | references vs lesson corpus |
| 4-plan decomposition | linear change (single deliverable, no fan-out) | deliverable/task graph |

**The q-gate is never pruned by the lane** — it is adversarial, so it is always kept as a step. Its
re-run *efficiency* (the first pass always runs; a re-run fires only when the validated artifact changed;
the `q_gate_validation` knob `off | once | until_clean`) is a **standalone improvement specified in
[`05-single-improvements.md`](05-single-improvements.md) §1**, not part of this feature. The lane only
*composes* it: a posture may set the knob's default (e.g. `minimal` → `once`). The never-skip-the-first-
pass invariant (doc-validation: 99% confidence + a real q-gate finding) is the regression test for both.

**Out of scope.** The structural fixes from the synthesis — `ci-verify`→deterministic script and the
execute-envelope-loop fix ([`05`](05-single-improvements.md)), and the per-dispatch cost optimizations
([`06`](06-execution-context-dispatch.md)) — are **not** part of this feature.

### 4.8 Runtime routing-decision verification (plan-retrospective aspect)

A new `plan-retrospective` aspect grades, at finalize, every routing decision the run actually made —
recipe-match, aspect-classification, and the posture — so the mechanism self-corrects. It is the
per-plan analog of the corpus-level `recipe-match` / `track-selection-accuracy` / `token-economics`
audit checks, and feeds them.

Inputs (all present at retrospective time): `execution.toon` (resolved manifest + `execution_log`),
`status.json` (posture, `planning_lane`, the recompose-divergence log), findings JSONL, `metrics.md`.

It verifies and reports (mostly deterministic — predicate re-evaluation is script work; LLM only for the
judgment):

1. **Recipe-fit** — did the matched recipe's shape hold, or was a recipe missed / mis-matched against
   the realized work?
2. **Aspect-fit** — did the analysis/planning classification that dropped build/test steps hold?
3. **Pruned-step soundness** — re-evaluate each `auto`-pruned step's predicate against the final
   realized footprint; predicate-now-false ⇒ **mis-prune** flag (e.g. sonar skipped as "no code delta"
   but the merged diff touched production code). A wrongly-skipped step is the highest-value output.
4. **Kept-step yield** — did each adversarial step that ran produce findings? Chronic 0-yield informs
   calibration.
5. **Posture counterfactual** — chosen posture vs. the posture the realized signals would have selected:
   `OVER-PROVISIONED | UNDER-PROVISIONED | correct`.
6. **Cost-preview accuracy** — predicted token/wall vs. actual; the delta recalibrates the
   `cost_size_token_table` (and the optional corpus medians) the preview uses (§4.6a).
7. **Re-compose divergence** — did phase-4's firm-signal re-compose change `auto`'s footprint prunes vs.
   the init preview, and was it logged (§4.5)?

A recurring mis-prune (item 3) across plans is the file-worthy signal — it routes to threshold tuning
(the sonar / lessons-housekeeping prune predicates) through the existing lesson / `architecture enrich`
path, so the thresholds learn from outcomes rather than staying hard-coded.

`plan-retrospective` is already the heaviest finalize agent (~150k, per the synthesis), so this aspect's
verification stays deterministic (predicate re-evaluation in the script), reserving LLM cognition for the
OVER/UNDER judgment — it must not become the overhead it polices.

### 4.9 Relationship to recipes & the coverage cell

Recipe, lane, and coverage cell are **not separate outputs** — they all resolve into the one concrete
plan (deliverables + tasks + `execution.toon`). They are distinct **decision inputs** that converge on
that artifact, for different reasons and touching different parts of it:

| Decision input | Reason it fires | Which part of the plan it writes |
|----------------|-----------------|----------------------------------|
| **Recipe** | semantic match on the request | the *work* (deliverables/tasks) — and may seed the *ceremony* |
| **Lane / profile** | change-type/scope/confidence thresholds | the *ceremony* only (phases/finalize-steps) |
| **Coverage cell** (T×scope) | gathered at invocation; some recipes pin it | validator *depth* |

The single resolver is `manage-execution-manifest` (§4.3): it takes recipe + signals + posture + cell +
config and emits the one `execution.toon`. The gap today is only that the inputs are wired separately
and don't talk — a `doc-verify` recipe can't tell the lane to drop sonar. Coordinate them:

1. **Recipes declare a default profile** in the §4.1 vocabulary (posture + per-element overrides):
   `recipe-doc-verify` → `auto`, `sonar: off`; `recipe-security-audit` → keep all adversarial. The
   recipe — best-informed about intended shape — **seeds** the profile the resolver uses; `auto`/the
   dialogue refine it.
2. **One shared plan-shape vocabulary** — the §4.1 contract is the substrate; the inputs are different
   *sources* writing into it (signals → `auto`; recipe → declared profile). This also rationalizes the
   existing entanglement where a recipe and a finalize-step are the same capability in different modes
   (`recipe-security-audit` ↔ `finalize-step-security-audit`).
3. **The recipe's reach is wider than the lane's** — it writes work and may seed ceremony; the lane
   writes ceremony only. They are not symmetric inputs, so the recipe-seed leads where it has an opinion
   and the operator / `auto` refine from there.

**Precedence.** The three inputs resolve in this order, low → high:

1. **Recipe seeds** the starting shape (best-informed default, not a lock).
2. **Operator posture overrides** the seed (explicit human choice > recipe default).
3. **Coverage cell's adversarial-floor is non-negotiable** — its T-level sets a floor on validator
   presence/depth that neither recipe nor posture drops below.

The cell is a **floor, not a cap**: it can only *raise* the validator minimum, never cap breadth, so it
never fights `full` and only bites when something below it tries to prune a validator the T-level
requires. **Conflict rule** (e.g. a recipe pins T4 but the operator picks `minimal`): apply the floor
**last** — it re-adds the adversarial validators (at the cell's depth) that the posture pruned, while
the posture's *non-adversarial* prunes (sonar, lessons-housekeeping) stand. The result is a coherent
"minimal ceremony + full adversarial rigor" plan; the cell never *removes* a step.

When a recipe *pins* a cell and the operator *also* gathers one, the operator may override either way,
but **lowering a recipe's deliberate rigor-pin surfaces a notice** (the same warning pattern as
`derived-state`), so it is never a silent downgrade.

## 5. Meta-project caveat — what `minimal` must not silently drop

For plan-marshall itself, `deploy-target`, `sync-plugin-cache`, and the on-main executor regeneration
are correctness-required derived state (ADR-002), not optional ceremony — dropping them ships a broken
cache. They carry `lane.class: derived-state` (tier `minimal`, the floor), so they run under every
posture by default. An operator can still override one to `off`, but that emits a correctness warning
("dropping sync-cache ships a broken cache") — the distinction between optional ceremony and required
derived state is executable as a default-plus-warning, not a hard block.

**Meta-project `marshal.json`.** plan-marshall's own `marshal.json` sets the **default posture to
`auto`** (same as consumers — the meta-project is not exempt from right-sizing) and applies **no per-step
overrides**: `security-audit` and `plan-retrospective` keep their shipped `full` default for the
meta-project too. So the meta-project's only `marshal.json` lane entry is the posture default; every
element runs at its frontmatter default tier.

## 6. Open questions

None remaining — all resolved into the §4 design specs (minimal set §2; scope §4.7; re-confirm §4.5;
class taxonomy §4.1; `deep_lane` §4.2; cost-preview & scale §4.6a; three-input precedence §4.9) — and
the q-gate re-run + `ci-verify` decisions into the standalone [`05-single-improvements.md`](05-single-improvements.md).

## 7. Surface (touch-points for the eventual plan)

- **Lane-element contract** — a standards doc (`extension-api/standards/ext-point-lane-element.md` or
  sibling) defining the `lane.{class,tier,prunable_when,cost_size}` block, the class→default table, the
  resolution lattice, and the named prune predicates. Each phase/step element gains a `lane:` block
  (mirrors how finalize steps declare `implements:`); the plugin-doctor frontmatter validator gains a
  rule that every lane-participating element declares a valid `lane.class` (and `cost_size`).
- **Cost sizing (extend existing)** — promote `phase-4-plan/standards/cost-sizing.md` to the single home
  of the T-shirt scale used by both tasks and lane-elements, **widened to `XS/S/M/L/XL/XXL`** (§4.6a):
  add `XS` + `XXL` to `COST_SIZE_LABELS` (`_config_defaults.py`) and to the `cost_size_token_table`
  default + validation; the four existing magnitudes stay put so the `manage-tasks derive-cost-size`
  deriver/bin-packer are unaffected; extend the deriver's score→size bands for the two new ends. Reuse
  the existing calibration loop. Prefill each element's default `cost_size` from the §4.6a table.
- `manage-status/scripts/_cmd_planning_lane.py` — extend `evaluate_signals_pure` to emit the profile;
  persist the chosen posture to `status.json::metadata`.
- `phase-1-init/SKILL.md` — add the profile dialogue (mirror the Step 5c recipe-match prompt) + the
  `lane_selection` knob read; call `manage-execution-manifest lanes preview` for the all-three-lanes
  TOON + cost; persist the posture; call `compose` to write the init-time `execution.toon`.
- `manage-execution-manifest` — the single resolver and lane-derivation script: a `lanes preview` verb
  (static `full`/`minimal` from config; `auto` from config + signals) returning one TOON; `compose`
  reads each element's `lane:` block + per-element overrides + posture + signals, applies §4.1
  resolution, and writes the flow to `execution.toon`. `compose` runs twice — at init (provisional) and
  at end-of-phase-4 (idempotent re-compose), logging `auto`'s footprint refinement on the second call.
- `manage-config` — declare `lane_selection`, the per-element `lane` override knob, and the prune-
  predicate thresholds; a preview helper enumerating resolved-elements-per-posture.
- **Recipe frontmatter** — recipes gain an optional `lane:` default block; recipe-match seeds the profile
  from it (§4.9).
- `plan-retrospective` — the runtime routing-decision verification aspect (§4.8): grades recipe-fit +
  aspect-fit + the lane decisions; recurring mis-fits route to threshold/recipe tuning via the existing
  lesson / `architecture enrich` path.
- **Cost-preview data** — a per-change-type median table (seeded from the analysis; recomputable).
- **Tests** — `evaluate_signals_pure` profile projection, composer step-resolution per posture, the
  meta-project required-derived-state invariant (§5).
- **`marshal.json` (required).** Seed the per-element `lane` defaults and the meta-project overrides
  into the plan-marshall `marshal.json` keyed-map (the project-level source the composer reads). The
  *shipped* per-element default lives in each element's frontmatter `lane:` block; `marshal.json`
  carries the project/meta overrides (see §5 and the default table below, once gathered).
- **Documentation (required).** Every new/changed config knob this plan adds — `lane_selection`, the
  per-element `lane` override, the extended `cost_size_token_table` (`XS`/`XXL` ends), and the
  prune-predicate thresholds — MUST be reflected in `doc/user/configuration.adoc`. Also adapt/extend the
  concept docs: the new lane-element contract standard, `cost-sizing.md`, the affected phase SKILLs
  (`phase-1-init`, `phase-3-outline`, `phase-4-plan`, `manage-execution-manifest`), and
  `ref-workflow-architecture` where the routing/manifest flow is described.

## 8. Risks

- **`minimal` shipping broken derived state** — mitigated by the `derived-state` class at the `minimal`
  floor (§5); since configurability is a hard principle, the guard is a correctness warning on override,
  not a block.
- **Cost preview drifting from reality** — the medians are a snapshot; flag them as estimates and keep
  them recomputable, don't hard-code.
- **Over-pruning adversarial steps** — by default `auto` never drops a validator; only prunable
  steps are predicate-prunable; the q-gate is adversarial and never pruned by the lane. (Its re-run
  efficiency is [`05`](05-single-improvements.md) §1; the never-skip-the-first-pass invariant — the
  doc-validation run, 99% confidence + a real q-gate finding — is the shared regression test.)

## 9. Worked examples — the model applied to the corpus

Ten plans replayed through the model: the posture `auto` would recommend, what it would prune, what it
keeps, and a rough token estimate. **These are estimates.** Per-phase and `refine` numbers are actuals
from `metrics.md`; per-*step* finalize prunes (sonar ≈110k, lessons-housekeeping ≈100k,
ci-verify ≈100k, plan-retrospective ≈150k) are lesson-derived rough constants — order-of-magnitude. The
`auto` figures keep all adversarial steps (conservative); `minimal` would save more. The savings shown
combine the lane prunes (this feature) with the [`05`](05-single-improvements.md) single-improvements
(q-gate re-run efficiency, `ci-verify`→script) — the full optimization picture, not 04 alone.

| # | Plan | type / scope / LOC | actual tok | `auto` posture | pruned (est. saving) | kept (adversarial / floor) | est. new tot |
|---|------|--------------------|-----------|----------------|----------------------|-----------------------------|--------------|
| 1 | doc-validation-capability-split | tech_debt / multi_module / 457 | 2.26M | **auto** | refine 103k · q-gate re-run ~200k · sonar ~110k · lessons-hk ~100k · ci-verify→script ~100k → **~610k** | outline scope-validator 1st pass (caught Javadoc gap), automated-review, archive | **~1.65M (−27%)** |
| 2 | fix-escalate-ask-guard-ordering | bug_fix / surgical / 20 | 1.03M | **auto/minimal** | refine 97k · lessons-hk ~100k · ci-verify→script ~100k → **~300k** | self-/automated-review, archive | **~0.74M (−29%)** |
| 3 | fix-automated-review-merge-anyway | bug_fix / surgical / 11 | 1.04M | **auto/minimal** | refine 119k · lessons-hk ~100k · ci-verify→script ~100k → **~320k** | automated-review, archive | **~0.72M (−31%)** |
| 4 | seed-re-review-timeout-config-knobs | feature / single_module / 28 | 1.67M | **auto** | sonar ~110k · lessons-hk ~100k · refine 61k → **~270k** | self-/automated-review, archive | **~1.40M (−16%)** |
| 5 | fix-broken-relative-link-findings | bug_fix / multi_module / 41 | 1.63M | **auto** | sonar ~110k · refine 58k · q-gate re-run ~150k · lessons-hk ~100k → **~420k** | outline validator 1st pass, automated-review, archive | **~1.21M (−26%)** |
| 6 | harmonize-owasp-top-ten-taxonomy | tech_debt / single_module / 206 | 1.69M | **auto** | refine 193k · sonar ~110k · lessons-hk ~100k → **~400k** | outline validator 1st pass, archive | **~1.29M (−24%)** |
| 7 | measure-uncompressed-output | analysis / surgical / 245 | 1.59M | **auto** | sonar ~110k · lessons-hk ~100k · trim retro ~150k → **~360k** | automated-review, archive | **~1.23M (−23%)** |
| 8 | integrate-sonar-finalize | feature / multi_module / 1129 | 3.78M | **full** | lessons-hk ~100k only → **~100k from lane** | self-review, security-audit-finder (found secret-key leak), automated-review, derived-state | **~3.68M (−3% from lane)** |
| 9 | arch-gate-build-command | feature / multi_module / 1530 | 3.02M | **full** | lessons-hk ~100k → **~100k from lane** | full adversarial set, derived-state | **~2.92M (−3% from lane)** |
| 10 | restore-coverage-gate-80 | tech_debt / single_module / 10028 | 4.19M | **full / auto** | ~nothing prunable (real large change) → **~0** | full set | **~4.19M (≈0%)** |

What the examples show:

- **The model self-sorts the corpus.** Trivial / doc / config-heavy-finalize plans (#1–7) get `auto` and
  shed ~20–30% from lane pruning alone — more at `minimal`. Correctly-deep features (#8–9) get `full` and
  the model prunes almost nothing (~3%), because their cost is the *structural* floor (envelope-loop
  defeat, per-dispatch context, rework/staleness), which lane selection does not and should not touch.
  The genuine large change (#10) is left intact — being big is not penalized when it is efficient per LOC
  (418 tok/LOC).
- **It confirms the synthesis split.** Lane right-sizing is the lever for the over-ceremony class (#1–7);
  the structural fixes (`ci-verify`→script, the execute-envelope loop, self-consistent audits, a
  merge-queue) are the lever for the correctly-deep class (#8–9). Complementary, not substitutes.
- **The adversarial validators survive every prune.** #1 and #5 keep the outline-validator pass that
  found the real scope gap; #8 keeps the security-audit-finder that caught the secret-key leak. The
  model removes prunable overhead while protecting every step that has historically found a
  defect.
