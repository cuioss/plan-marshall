# 01 — Routing v2: route informal requests onto cheap paths

**Headline workstream. Depends on [02 audit recipes](02-audit-recipes.md) for routing targets.**

## Problem

The only request router today is `planning-lane route`
(`marketplace/bundles/plan-marshall/skills/manage-status/`, implemented in
`_cmd_planning_lane.py`), called inline at phase-1-init Step 8b. It is deterministic
and zero-token, but it only resolves **light vs deep** — both lanes still traverse
refine → outline → plan → execute → finalize. There is no path that says "this
request is a known shape, run the focused thing and skip the pipeline."

The cost this leaves on the table is downstream re-dispatch, not the routing
decision itself: roughly 860K tokens of re-dispatch waste across 54 plans
(~16K/plan), concentrated in phase-2-refine confidence-loop fragmentation
(`.plan/context_effective_dispatch.md`). The fix is not a smarter classifier; it
is a path that avoids the heavy loop entirely for known-shape work.

## Approach

Add a **recipe-match routing tier** ahead of the light/deep decision:

- **Tier 0 (exists):** lesson auto-suggest heuristic (phase-1-init Step 5c) already
  routes doc-shaped lessons to `recipe-lesson-cleanup`. This is the pattern to
  generalize.
- **Tier 1 (new):** recipe-match. Score the informal request against the recipe
  registry (`manage-config list-recipes` already returns every extension + project
  recipe with key / name / description / scope / change_type). Heuristic-first
  (keyword + intent overlap, reusing the auto-suggest scoring); escalate to a
  single bounded LLM classification pass only when the heuristic is ambiguous.
  High confidence (≥ 0.7) → propose the recipe via `AskUserQuestion`; auto-route
  when config permits.
- **Tier 2 (exists):** `planning-lane` light/deep for everything that is not a
  recipe match.

The token/wall-time win comes from the matched recipe running in a single envelope
(guaranteed by [02](02-audit-recipes.md)), not from optimizing the heavy path.

## Key design decisions

- **No always-on LLM router.** Heuristic-first with one bounded fallback pass —
  preserves the zero-token property `planning-lane` has today.
- **Reuse, do not reinvent.** The recipe registry (`ext-point-recipe.md`),
  `list-recipes`, and the auto-suggest scoring already exist. Tier 1 is a
  generalization of the lesson-cleanup auto-suggest to the whole recipe set.
- **Secondary target:** the confidence-loop re-dispatch fragmentation (the real
  860K-token cost) is reduced because routed recipes run in one envelope.

## Affected surface

- `phase-1-init/SKILL.md` — generalize Step 5c into a recipe-match step; sequence
  it ahead of the Step 8b planning-lane call.
- `manage-status` planning-lane (sequencing only).
- `manage-config` recipe-resolution verbs (read-only reuse).
- New scoring helper (heuristic) — likely a small router script or a `manage-config`
  verb.
- Docs: `ref-workflow-architecture` phase-lifecycle, recipe workflow.

## Open decisions

- **Where the recipe-match tier lives:** inside phase-1-init vs a dedicated `route`
  verb on the `/plan-marshall` command entry. **Recommendation:** a dedicated
  verb so it is reusable and unit-testable; phase-1-init calls it.

## Documentation to update (deliverables of this plan)

- `doc/concepts/planning-workflow.adoc` — the recipe-match tier ahead of the
  light/deep lane decision; how a request bypasses refine → outline → plan.
- `doc/concepts/recipes.adoc` — recipes as routing targets.
- `doc/concepts/token-management.adoc` — the single-envelope token/wall-time win.
- `doc/user/commands.adoc` — any new `route` verb / changed `/plan-marshall` entry
  behaviour.
- `doc/user/configuration.adoc` — any new routing/auto-route config knob.

## On completion

Delete this document and remove the `01` row from
[`README.md`](README.md); this is part of the plan's finalize.

## Scope

Medium. Blocked on [02](02-audit-recipes.md).
