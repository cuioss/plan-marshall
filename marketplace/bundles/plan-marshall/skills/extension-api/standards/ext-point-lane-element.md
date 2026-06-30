# Extension Point: Lane Element

> **Type**: Frontmatter Contract | **Hook**: `lane:` frontmatter block | **Implementations**: every phase / finalize-step element | **Status**: Active

## Overview

The **lane-element contract** is the per-element substrate the execution-profile lane
selection feature resolves over. Every workflow element that the lane mechanism can keep or
prune — each phase skill, each phase-6 finalize step, each q-gate / adversarial validator —
**self-declares its lane membership** through a `lane:` frontmatter block. The operator-facing
postures `minimal` / `auto` / `full` are *cutoffs* over those self-classifying elements, so the
posture→steps mapping stays **derived, not maintained**: an element changes lane behavior by
editing its own frontmatter, never by editing a central keep/drop list.

This is the central standard that all downstream lane-selection deliverables — the config knobs,
the planning-lane profile projection, the `manage-execution-manifest` lane resolver, the
plugin-doctor validation rule, and the recipe lane seeds — **cross-reference rather than
inline-copy**. The enforcement-critical content (the closed `class` enum, the class→default
table, the resolution lattice, the named prune predicates, and the `cost_size` binding) lives
here and only here.

## The `lane:` frontmatter block

Each lane-participating element declares one block in its SKILL.md / step-doc YAML frontmatter:

```yaml
lane:
  class: derived-state | core | adversarial | prunable
  tier: minimal | auto | full            # optional — defaults from class
  prunable_when: <predicate-id>          # required for class: prunable; ignored otherwise
  cost_size: XS | S | M | L | XL | XXL   # required — drives the §cost dialogue preview
```

| Sub-field | Required | Rule |
|-----------|----------|------|
| `class` | Yes | The primary declaration. One of the **closed** enum `derived-state \| core \| adversarial \| prunable`. Drives the `tier` and `prunable?` defaults. |
| `tier` | No | The element's effective default cutoff on the `minimal ⊏ auto ⊏ full` lattice. Defaults from `class` (table below); set explicitly only to deviate (e.g. `security-audit` deviates to `full`). |
| `prunable_when` | Conditional | **Required** when `class: prunable` — names a predicate from the [Prune predicates](#prune-predicates) table. Ignored (and SHOULD be omitted) for any other class. |
| `cost_size` | Yes | One of the **closed** six-size scale `XS \| S \| M \| L \| XL \| XXL`. The scale is owned by [`phase-4-plan/standards/cost-sizing.md`](../../phase-4-plan/standards/cost-sizing.md); the lane dialogue sums each resolved element's `cost_size` through the `cost_size_token_table` to produce the per-posture cost preview. |

`class` is the primary declaration; `tier` and `prunable?` default from it.

## The closed `lane.class` enum

`class` is a **closed** four-value enum. A new element MUST pick exactly one; introducing a new
class value is a contract change to this document, not a per-element choice.

| `class` | default `tier` | prunable? | meaning | examples |
|---------|----------------|-----------|---------|----------|
| **derived-state** | `minimal` | no — a weakening override emits a correctness **warning** (only where the steps exist) | correctness-required derived output; dropping it ships a broken artifact | deploy-target, sync-plugin-cache |
| **core** | `minimal` | no | always-on plan machinery; the leanest floor | push, create-pr, ci-verify, branch-cleanup, record-metrics, archive |
| **adversarial** | `auto` | no | a validator that finds real defects; never predicate-pruned by the lane | outline scope-validator (1st pass), automated-review, self-review, security-audit-as-finder |
| **prunable** | `auto` | yes — via `prunable_when` | conditional overhead that a firm-signal predicate can skip | sonar-roundtrip, lessons-housekeeping, refine, 4-plan decomposition |

## The resolution lattice

`minimal` is the **floor** of the lattice `minimal ⊏ auto ⊏ full`. A `minimal`-tier element runs
under *every* posture (it is the leanest posture an operator can pick), so `core` /
`derived-state` elements are on by default in all three lanes — that is how "archiving is always
part of the plan" holds without a dedicated `always` level.

### Per-element resolution (at manifest composition)

For each element, the composer resolves in this order:

1. **effective tier** = per-element override (`marshal.json`) ▸ else declared `lane.tier` ▸ else
   class default. An explicit override **always wins**, including an `off` that drops a
   `derived-state` / `core` floor element (which additionally emits a correctness warning, but is
   honored — *user decision wins*).
2. **element runs iff** `effective_tier ⊑ posture` on `minimal ⊏ auto ⊏ full` (posture = the
   init-chosen global preset).
3. if effective tier is `ask` → surface this element **individually** in the init dialogue.
4. if `class == prunable` **and** the element's `prunable_when` predicate **holds at firm-signal
   time** → skip even when `effective_tier ⊑ posture`. By default `derived-state` / `core` /
   `adversarial` are never predicate-demoted (an operator may still opt one in via config).

So:

- `minimal` = "only the tier-`minimal` floor";
- `auto` = "run every element whose tier ⊑ `auto`, **minus** any `prunable` element whose
  predicate fires";
- `full` = "everything configured."

> **Overriding principle — everything is configurable (user decision wins).** The contract
> supplies *defaults*. No classification is a hard lock: an explicit project/user override always
> wins. For correctness-critical `derived-state` elements a weakening override surfaces a loud
> **warning** but is still honored — the operator decides, the system informs.

### Per-element override knob

Any element is pinned through the nested `marshal.json` step-param channel (the same shape
finalize-step params use), value ∈ `off | minimal | auto | full | ask`
(`off` = never run; `minimal` = force-keep in every posture; `ask` = always prompt):

```json
"plan": { "phase-6-finalize": { "steps": {
  "sonar-roundtrip":    { "lane": "minimal" },
  "plan-retrospective": { "lane": "full" },
  "security-audit":     { "lane": "ask" }
}}}
```

The shipped per-element default lives in each element's frontmatter `lane:` block; `marshal.json`
carries only the project / meta overrides.

## Prune predicates

`class: prunable` elements name one predicate in `prunable_when`. `auto` evaluates the predicate
against the firm footprint at compose time; a true predicate skips the element even when its tier
is in posture. The predicate set is the declarative source of `auto`'s conditional skips — there
is no hard-coded skip list.

| `prunable_when` | Prune when | Source signal |
|-----------------|-----------|---------------|
| `confidence_complete` | post-init confidence ≥ threshold / input is a complete spec | post-init confidence proxy |
| `no_code_delta` | no code-logic delta (`change_type ∈ {docs, tech_debt}`, no production change) | footprint / aspect |
| `footprint_no_lesson_component` | the footprint touches no lesson's component | references vs lesson corpus |
| `linear_change` | a linear change (single deliverable, no fan-out) | deliverable / task graph |

**The q-gate is never pruned by the lane** — it is `adversarial`, so it is always kept. Its
re-run *efficiency* (first pass always runs; a re-run fires only when the validated artifact
changed) is a standalone improvement, not part of this contract; the lane only *composes* it.

## Default lane tiers (shipped frontmatter defaults)

`tier` is each element's explicit default — equal to the class default except where **bolded**:

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

`lessons-capture` and `lessons-housekeeping` at `minimal` are part of the floor (always
eligible); `lessons-housekeeping` is `prunable`, so it still smart-skips when the footprint
touches no lesson's component. `security-audit` and `plan-retrospective` only run at `full`.

## Cost sizing

`cost_size` reuses — does not duplicate — the task cost-size model. The six-size T-shirt scale
(`XS / S / M / L / XL / XXL`) and its `cost_size_token_table` magnitudes are owned centrally by
[`phase-4-plan/standards/cost-sizing.md`](../../phase-4-plan/standards/cost-sizing.md). The lane
dialogue's cost preview is `Σ(resolved element cost_size → cost_size_token_table)`, available in
**every** project because the table is a config default (no corpus needed). The same actual-vs-
predicted calibration loop that tunes the task table also tunes the lane preview.

| size | token magnitude | covers |
|------|-----------------|--------|
| **XS** | ~5K | deterministic ≈0-token bookkeeping (push, branch-cleanup, archive, record-metrics, deploy-target, sync-plugin-cache) |
| **S** | 25K | small agent steps (plugin-doctor, ci-verify) |
| **M** | 60K | medium (init, refine, create-pr, simplify, lessons-capture, review-retrospective) |
| **L** | 130K | heavy single steps (sonar, self-review, security-audit, automated-review, lessons-housekeeping, plan-retrospective, q-gate) |
| **XL** | 260K | the planning phases (outline incl. 1st q-gate, plan) |
| **XXL** | 520K+ | the largest elements — `execute` on a substantial plan; any element exceeding XL |

`XS` and `XXL` are the two additions to the pre-existing `S/M/L/XL`; the four existing magnitudes
are unchanged, so the `manage-tasks derive-cost-size` deriver and the bin-packer are unaffected.

## Enforcement

A lane-participating element MUST declare a well-formed `lane:` block: a valid closed-enum
`class`, a `cost_size` from the closed six-size scale, and — when `class: prunable` — a
`prunable_when` naming a predicate from the [Prune predicates](#prune-predicates) table. The
plugin-doctor frontmatter validator owns the structural check (every lane-participating element
declares a valid `lane.class` and `cost_size`); this document is the source-of-truth the rule
reads for the closed enums and the predicate vocabulary.

## Related Specifications

- [ext-point-recipe.md](ext-point-recipe.md) — recipes declare an optional `lane:` default block that recipe-match seeds the profile from
- [marshal-json-reference.md](marshal-json-reference.md) — central marshal.json path reference (the per-element `lane` override + `lane_selection` knob)
- [`phase-4-plan/standards/cost-sizing.md`](../../phase-4-plan/standards/cost-sizing.md) — the single home of the six-size T-shirt scale shared by tasks and lane-elements
