# Recipe Extension Contract

Workflow-perspective contract for recipe extensions — predefined, repeatable transformations applied to a codebase.

## Purpose

Recipes are a **plan source** (like task, issue, or lesson) that provide predefined WHAT+HOW. Unlike ad-hoc plans where the LLM analyzes a free-form request, recipes already know what transformation to apply — they only discover WHERE.

Use cases:

- Refactoring production code to comply with coding standards
- Refactoring test code to comply with testing standards
- Security reviews across all modules
- Documentation improvement sweeps
- Any repeatable, standards-based transformation

---

## Phase Impact

| Phase | Normal Plan | Recipe Plan |
|-------|-------------|-------------|
| 1-init | Creates plan from task/issue/lesson | Creates plan with `source=recipe`, stores recipe metadata |
| 2-refine | Full quality analysis, iterative clarification | Scope selection only, auto-confidence=100 |
| 3-outline | Detect change_type → route by track → create deliverables → Q-Gate | Load recipe skill → recipe creates deliverables (no Q-Gate — deterministic output) |
| 4-plan | Standard | Standard (no changes) |
| 5-execute | Standard | Standard (no changes) |
| 6-finalize | Standard | Standard (no changes) |

---

## Recipe Skill Interface

All recipe skills — built-in and custom — are loaded by phase-3-outline via the same mechanism. This section defines the contract between phase-3-outline (caller) and any recipe skill (callee).

### Input Parameters

Phase-3-outline loads the recipe skill with:

```
Skill: {recipe_skill}
  Input:
    plan_id: {plan_id}
    recipe_domain: {recipe_domain or empty}
    recipe_profile: {recipe_profile or empty}
    recipe_package_source: {recipe_package_source or empty}
```

| Parameter | Type | Guaranteed | Description |
|-----------|------|------------|-------------|
| `plan_id` | string | Always | Plan identifier |
| `recipe_domain` | string | Built-in only | Domain key (e.g., `java`). Empty for custom recipes unless the extension sets it |
| `recipe_profile` | string | Built-in only | Profile name (e.g., `implementation`). Empty for custom recipes unless the extension sets it |
| `recipe_package_source` | string | Built-in only | Architecture field to iterate (`packages` or `test_packages`). Empty for custom recipes unless the extension sets it |

Custom recipe skills that need domain/profile/package_source should either:
- Declare `profile` and `package_source` on the recipe dict in `provides_recipes()` (recipe.md Step 3 stores them in metadata, phase-3-outline passes them)
- Or hardcode the values if the recipe is domain-specific

### Required Sinks

The recipe skill must write these artifacts before returning:

| Sink | Written via | Description |
|------|-------------|-------------|
| `solution_outline.md` | `pm-workflow:manage-solution-outline:manage-solution-outline write` | Deliverables grouped by module |
| Deliverables in outline | Embedded in solution_outline.md | One per scope unit (typically per package) |

### Required Deliverable Properties

Each deliverable created by a recipe must include:

| Property | Source | Description |
|----------|--------|-------------|
| `change_type` | Recipe's `default_change_type` | Set by phase-3-outline before skill load |
| `execution_mode` | `automated` | Recipes are designed for agent execution |
| `domain` | Input `recipe_domain` or hardcoded | Domain key for task routing |
| `module` | Architecture discovery | Module containing the scope unit |
| `profile` | Input `recipe_profile` or hardcoded | Task execution profile |
| `skills` | Resolved dynamically | From `resolve-domain-skills` (not hardcoded) |
| Affected files | Architecture data | Explicit file list per deliverable |

### Workflow Sections

Recipe skills typically follow these sections (order may vary for custom recipes):

1. **Skill Resolution**: `resolve-domain-skills --domain {domain} --profile {profile}`
2. **Module Listing**: `architecture modules` — present to user for filtering
3. **Package Discovery**: `architecture module --name {module} --full` — iterate the package source field
4. **Deliverable Creation**: One per package, no separate analysis step
5. **Outline Writing**: Write `solution_outline.md`

### Granularity Convention

Recipes should create one deliverable per package (not per file, not per module). This provides:
- Focused enough scope for quality agent runs
- Small enough units to complete reliably
- Natural grouping for code review

For the full flow with ASCII diagrams, see [phase-3-outline references/recipe-flow.md](../../phase-3-outline/references/recipe-flow.md).

---

## Discovery and Resolution Flow

```
1. /plan-marshall action=recipe
2. Present built-in recipe + list-recipes (custom from domains)
3. User selects recipe
   - Built-in: user also selects domain + profile
   - Custom: resolve-recipe returns metadata
4. plan-init-agent creates plan with source=recipe
5. Store metadata in status (recipe_key, recipe_skill, recipe_domain, ...)
6. phase-2-refine: scope selection only, confidence=100
7. phase-3-outline Step 2.5: loads recipe skill with input parameters
8. Recipe skill writes deliverables + solution_outline.md
9. phase-4-plan: standard task creation (no Q-Gate — recipe output is deterministic)
```

---

## marshal.json Storage

Custom recipes (from `provides_recipes()`) are stored under `skill_domains.{domain}.recipes`. The built-in recipe is not stored in marshal.json — it is always available.

```json
{
  "skill_domains": {
    "java": {
      "bundle": "pm-dev-java",
      "recipes": [
        {
          "key": "null-safety-compliance",
          "name": "Null Safety Compliance",
          "description": "Add JSpecify annotations across all packages",
          "skill": "pm-dev-java:recipe-null-safety",
          "default_change_type": "tech_debt",
          "scope": "codebase_wide",
          "profile": "implementation",
          "package_source": "packages"
        }
      ]
    }
  }
}
```

---

## Status Metadata

Recipe plans store these metadata fields in status:

| Field | Value | Set By |
|-------|-------|--------|
| `plan_source` | `recipe` | recipe workflow (Step 3) |
| `recipe_key` | Recipe key string | recipe workflow (Step 3) |
| `recipe_skill` | Skill reference | recipe workflow (Step 3) |
| `recipe_domain` | Domain key (e.g., `java`) | recipe workflow (Step 3) — built-in recipe only |
| `recipe_profile` | Profile name (e.g., `implementation`) | recipe workflow (Step 3) — built-in recipe only |
| `recipe_package_source` | `packages` or `test_packages` | recipe workflow (Step 3) — built-in recipe only |
| `track` | `complex` | phase-2-refine (Step 1.6) |
| `confidence` | `100` | phase-2-refine (Step 1.6) |
| `change_type` | From `default_change_type` | phase-3-outline (Step 2.5) |

---

## Built-in vs Custom vs Project Recipes

| Type | Source | `source` field | When to use |
|------|--------|----------------|-------------|
| **Built-in** | pm-workflow `recipe-refactor-to-profile-standards` | — (not stored) | Standard refactoring to profile standards (any domain/profile) |
| **Custom** | Domain `provides_recipes()` | absent | Domain-specific transformations requiring custom discovery/analysis logic |
| **Project** | `skill-domains add-recipe` CLI | `"project"` | Project-specific recipes for projects without domain extensions |

The built-in recipe is always available when domains are configured. It handles skill resolution, module listing, package iteration, neutral compliance analysis, and deliverable creation — all parameterized by domain and profile selected at invocation time.

Project-level recipes enable projects that have `.claude/skills/` but no domain extension to define recipes via CLI commands (`add-recipe` / `remove-recipe`). They are stored with `"source": "project"` and preserved across `skill-domains configure` runs.

## Extension API

Custom recipes are declared via `provides_recipes()` in `extension.py`. Only use this for recipes that need domain-specific logic beyond what the built-in recipe provides:

```python
def provides_recipes(self) -> list[dict]:
    return [
        {
            'key': 'null-safety-compliance',
            'name': 'Null Safety Compliance',
            'description': 'Add JSpecify annotations across all packages',
            'skill': 'pm-dev-java:recipe-null-safety',
            'default_change_type': 'tech_debt',
            'scope': 'codebase_wide',
            'profile': 'implementation',
            'package_source': 'packages',
        },
    ]
```

See `plan-marshall:extension-api` standards/recipe-extension.md for the full extension API contract.

---

## Related

- [extension-mechanism.md](extension-mechanism.md) — Outline extension mechanism
- [triage-extension.md](triage-extension.md) — Triage extension contract
- `plan-marshall:extension-api` — ExtensionBase with `provides_recipes()`
- `pm-workflow:phase-3-outline` — Recipe detection in Step 2.5
- `pm-workflow:phase-3-outline` [references/recipe-flow.md](../../phase-3-outline/references/recipe-flow.md) — Visual flow diagrams (built-in vs custom)
