# Extension Point: Recipe

> **Type**: Workflow Skill Extension | **Hook Method**: `provides_recipes()` | **Implementations**: 4 | **Status**: Active

## Overview

Recipe extensions declare predefined, repeatable transformations that bypass change-type detection and provide their own discovery, analysis, and deliverable patterns. Recipes are presented to users via `/plan-marshall action=recipe` and execute deterministic architecture-to-deliverable mappings.

## Implementor Requirements

### Implementor Frontmatter

All recipe implementor skills must include in their SKILL.md frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-recipe
```

### Project Recipe Frontmatter

Project recipes — `recipe-*` skills under `.claude/skills/` — declare their discovery
metadata through SKILL.md YAML frontmatter keys. This frontmatter channel is the
project-recipe counterpart to `provides_recipes()`: extension recipes return their
discovery metadata from the `provides_recipes()` dict, while project recipes declare
it as frontmatter keys.

| Frontmatter Key | Required | Description |
|-----------------|----------|-------------|
| `recipe_domain` | Yes | Domain key for the recipe. **A project recipe whose frontmatter omits `recipe_domain` is silently skipped from discovery** — this is the intentional containment that keeps a half-authored recipe out of the recipe list. |
| `recipe_profile` | No | Target profile (`implementation`, `module_testing`). Omit when the recipe does not constrain a profile. |
| `recipe_package_source` | No | Package source (`packages`, `test_packages`). Omit when the recipe does not constrain a package source. |

Canonical project-recipe frontmatter block:

```yaml
---
name: recipe-example
description: One-line recipe description shown during recipe selection
implements: plan-marshall:extension-api/standards/ext-point-recipe
recipe_domain: plan-marshall-plugin-dev
recipe_profile: implementation
recipe_package_source: packages
---
```

**Frontmatter is the sole source of truth for these keys.** The discovery scanner reads
`recipe_domain` / `recipe_profile` / `recipe_package_source` from frontmatter only — it
does **not** read the markdown body for them. A body-table row or prose mention of any of
these keys is structurally inert and never shadows the frontmatter value.

### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_recipes(self) -> list[dict]:
        return [
            {
                'key': 'refactor-to-profile-standards',
                'name': 'Refactor to Profile Standards',
                'description': 'Refactor code to comply with configured profile standards',
                'skill': 'plan-marshall:recipe-refactor-to-profile-standards',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
            },
        ]
```

## Runtime Invocation Contract

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | str | Yes | Plan identifier |
| `recipe_domain` | str | No | Domain key (user-selected or recipe-declared) |
| `recipe_profile` | str | No | Target profile (`implementation`, `module_testing`) |
| `recipe_package_source` | str | No | Package source (`packages`, `test_packages`) |

The `recipe_domain` / `recipe_profile` / `recipe_package_source` values are recipe-declared:
project recipes declare them as frontmatter keys (see [Project Recipe Frontmatter](#project-recipe-frontmatter)),
while extension recipes return them from `provides_recipes()`. A user-supplied value at plan
creation time overrides the recipe-declared default where the recipe omits the key.

### Pre-Conditions

- Recipe resolved via `resolve-recipe --recipe {key}`
- Plan initialized via phase-1-init
- Domain extension loaded (for extension-sourced recipes)

### Post-Conditions

- `solution_outline.md` written with module-grouped deliverables
- Recipe metadata stored in `status.json` (`recipe_key`, `recipe_skill`, `recipe_domain`, etc.)
- Each deliverable has scope, affected files, verification commands

### Lifecycle

```
1. /plan-marshall action=recipe
2. list-recipes discovers all recipes (extension + project)
3. User selects recipe
4. phase-1-init creates plan with recipe metadata
5. phase-2-refine: recipe shortcut (confidence=100, track=complex)
6. phase-3-outline: recipe detection → load recipe skill
7. Recipe skill: discovery, deliverable creation, solution_outline.md
```

### Recipe Discovery Sources

Recipes are discovered from two sources (in order):

1. **Extension `provides_recipes()`** — domain bundle recipes (source: `extension`)
2. **Project `recipe-*` skills in `.claude/skills/`** — project-level recipes (source: `project`); metadata declared via frontmatter keys (`recipe_domain` required; `recipe_profile`/`recipe_package_source` optional). See [Project Recipe Frontmatter](#project-recipe-frontmatter).

## Hook API

### Python API

```python
def provides_recipes(self) -> list[dict]:
    """Return recipe definitions this extension provides.

    Default: []
    """
```

### Return Structure

Each recipe dict returned by `provides_recipes()`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | str | Yes | Unique recipe identifier — used in `resolve-recipe --recipe {key}` |
| `name` | str | Yes | Human-readable display name for UI |
| `description` | str | Yes | Description shown during recipe selection |
| `skill` | str | Yes | Fully-qualified skill reference (`bundle:recipe-skill`) |
| `default_change_type` | str | Yes | Change type for phase-3-outline (e.g., `tech_debt`, `feature`) |
| `scope` | str | Yes | Scope indicator (`codebase_wide`, `module`) |
| `profile` | str | No | Target profile — omit if user selects at plan creation time |
| `package_source` | str | No | Package source — omit if user selects at plan creation time |
| `coverage_gathering` | str | No | Whether the recipe workflow gathers a coverage cell per the [coverage-gathering contract](../../dev-agent-behavior-rules/standards/coverage-gathering-contract.md): `required` (always gather), `optional` (offer with an `inherit` escape), `none` (never gather). Defaults to `none` when omitted. `recipe.md` keys its contract gather + expand + persist hook on this field. `recipe-lesson-cleanup` declares `none` (forced-surgical scope). |

**Auto-assigned fields** (do NOT include in return value):

| Field | Value | Source |
|-------|-------|--------|
| `domain` | First domain key from `get_skill_domains()` | Auto-extracted |
| `source` | `'extension'` | Auto-assigned |

## Resolution

```bash
# List all recipes from all sources
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-recipes

# Resolve a specific recipe by key
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-recipe --recipe {key}
```

## Current Implementations

| Bundle | Skill | Recipe Key |
|--------|-------|------------|
| plan-marshall | recipe-refactor-to-profile-standards | refactor-to-profile-standards |
| pm-documents | recipe-doc-verify | doc-verify |
| pm-documents | recipe-verify-architecture-diagrams | verify-architecture-diagrams |
| pm-dev-java-cui | recipe-cui-logging-enforce | cui-logging-enforce |
