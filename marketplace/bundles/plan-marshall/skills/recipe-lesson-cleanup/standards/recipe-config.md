# Recipe Configuration: lesson_cleanup

This document declares the `lesson_cleanup` recipe in the format consumed by `manage-config resolve-recipe`. The same fields are returned by the built-in `provides_recipes()` callback in `plan-marshall-plugin/extension.py` (Source 1 in `_discover_all_recipes`).

## Declaration

| Field | Value | Notes |
|-------|-------|-------|
| `key` | `lesson_cleanup` | Stable identifier passed to `phase-1-init` via `recipe_key` |
| `name` | `Lesson Cleanup` | Display name shown in steward menu and recipe list |
| `description` | `Convert a single lesson-learned into a deterministic surgical plan` | Shown in `manage-config list-recipes` output |
| `skill` | `plan-marshall:recipe-lesson-cleanup` | Fully-qualified skill notation loaded by `phase-3-outline` |
| `default_change_type` | _derived_ | See **Derived change_type** below — not a single fixed value |
| `scope` | `single_lesson` | Distinct from `codebase_wide` (used by `refactor-to-profile-standards`) |

## Derived change_type

Unlike most recipes, `lesson_cleanup`'s `default_change_type` is not a single fixed value — it is derived from the input lesson's `kind` field at recipe execution time. The mapping is documented as part of the recipe contract:

| Lesson kind | Derived change_type |
|-------------|---------------------|
| `bug` | `bug_fix` |
| `improvement` | `enhancement` |
| `anti-pattern` | `tech_debt` |

The `provides_recipes()` callback in `plan-marshall-plugin/extension.py` reports `default_change_type: tech_debt` as a placeholder so the recipe surfaces in tooling that expects a single value. The recipe itself overrides this per-execution based on the lesson kind. Consumers that need the actual change_type for a given lesson MUST call the recipe and read the output, not the static declaration.

## Inputs

| Parameter | Type | Required | Source |
|-----------|------|----------|--------|
| `plan_id` | string | Yes | Caller (phase-3-outline) |
| `lesson_id` | string | Yes | `phase-1-init` Step 5b moves the lesson into the plan directory; the recipe reads it from `lesson-{lesson_id}.md` |

No `recipe_domain`, `recipe_profile`, or `recipe_package_source` parameters — those exist on `refactor-to-profile-standards` because it iterates packages across modules. `lesson_cleanup` operates on a single lesson body, which is its own scope.

## Surgical scope contract

The recipe MUST set `scope_estimate: surgical` in the outline metadata. Downstream `phase-4-plan` reads this value and applies the surgical cascade rule for the derived `change_type`:

- `surgical + bug_fix` / `surgical + enhancement` / `surgical + tech_debt` all collapse to:
  - Phase 5 verification: `quality-gate` only
  - Phase 6 finalize: `commit-push`, `create-pr`, `lessons-capture` only (drops `automated-review`, `sonar-roundtrip`, `knowledge-capture`)

This is the entire reason this recipe exists — driving the smallest safe manifest for a single-lesson cleanup.

## Discovery

Because `lesson_cleanup` is a built-in (not a project-level `recipe-*` skill), it is registered via `provides_recipes()` in `plan-marshall-plugin/extension.py` and discovered as Source 1 in `_discover_all_recipes`. The recipe surfaces in:

- `manage-config list-recipes` output (alongside `refactor-to-profile-standards`)
- `manage-config resolve-recipe --recipe lesson_cleanup` returns the resolved declaration
- `marshall-steward` recipes section (see `references/menu-recipes.md`)

## Auto-suggest hook

`phase-1-init` auto-suggests this recipe when:

1. `source == lesson` (the user passed `--lesson-id`), AND
2. The lesson body is doc-shaped (no `.py` code blocks, no "test"/"refactor" verbs as primary subject).

When both hold, `phase-1-init` sets `plan_source=recipe` and `recipe_key=lesson_cleanup` in status metadata and emits a `Recipe auto-suggested` decision log entry. The user retains the option to override via explicit `--recipe-key` on subsequent runs.

See `phase-1-init/standards/workflow.md` § "Lesson auto-suggest hook" for the full heuristic and integration narrative.
