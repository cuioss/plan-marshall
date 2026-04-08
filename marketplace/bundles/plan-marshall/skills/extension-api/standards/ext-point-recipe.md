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
2. **Project `recipe-*` skills in `.claude/skills/`** — project-level recipes (source: `project`)

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
