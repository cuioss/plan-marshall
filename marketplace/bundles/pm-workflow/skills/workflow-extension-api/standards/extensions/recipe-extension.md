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
| 3-outline | Detect change_type → route by track → create deliverables | Built-in: inline generic recipe workflow. Custom: load recipe skill → recipe handles discovery+analysis+deliverables |
| 4-plan | Standard | Standard (no changes) |
| 5-execute | Standard | Standard (no changes) |
| 6-finalize | Standard | Standard (no changes) |

---

## Recipe Skill Contract

Each recipe references a skill (via `recipe.skill`) that handles the outline phase. The recipe skill must provide:

### Required Workflow Sections

1. **Skill Resolution**: Resolve skills dynamically from the configured profile using `resolve-domain-skills --domain {domain} --profile {profile}`. This ensures recipes use the same skills as regular workflow tasks and pick up project-level customizations.

2. **Module Listing**: Query available modules via `architecture modules` command. Let user confirm/filter modules.

3. **Package Discovery**: For each selected module, query full module details via `architecture module --name {module} --full`. Use packages from the architecture data to build package inventory.

4. **Deliverable Creation**: Create one deliverable per package. No separate analysis step — the task executor loads the profile skills and handles both analysis and fixing in a single pass. Each deliverable must include:
   - `change_type`: From recipe's `default_change_type`
   - `execution_mode`: `automated`
   - `domain`: From the recipe's domain key
   - `module`: Module containing the scope unit
   - `profile`: Task execution profile (e.g., `implementation`, `module_testing`)
   - `skills`: Resolved from configured profile (not hardcoded)
   - Affected files list

5. **Outline Writing**: Write `solution_outline.md` with all deliverables, grouped by module.

### Granularity Convention

Recipes should create one deliverable per package (not per file, not per module). This provides:
- Focused enough scope for quality agent runs
- Small enough units to complete reliably
- Natural grouping for code review

---

## Discovery and Resolution Flow

```
1. /plan-marshall action=recipe
2. list-recipes → aggregate from all configured domains
3. User selects recipe (or provides --recipe key)
4. resolve-recipe → returns recipe metadata
5. plan-init-agent creates plan with source=recipe
6. phase-2-refine: scope selection only, confidence=100
7. phase-3-outline: loads recipe skill → discovery → analysis → deliverables
8. phase-4-plan: standard task creation
```

---

## marshal.json Storage

Recipes are stored under `skill_domains.{domain}.recipes`:

```json
{
  "skill_domains": {
    "java": {
      "bundle": "pm-dev-java",
      "recipes": [
        {
          "key": "refactor-to-standards",
          "name": "Refactor to Implementation Standards",
          "description": "Refactor production code to comply with java-core and java-maintenance standards",
          "skill": "pm-dev-java:recipe-refactor-to-standards",
          "default_change_type": "tech_debt",
          "scope": "codebase_wide"
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

## Built-in vs Custom Recipes

| Type | Source | When to use |
|------|--------|-------------|
| **Built-in** | pm-workflow `recipe-refactor-to-profile-standards` | Standard refactoring to profile standards (any domain/profile) |
| **Custom** | Domain `provides_recipes()` | Domain-specific transformations requiring custom discovery/analysis logic |

The built-in recipe is always available when domains are configured. It handles skill resolution, module listing, package iteration, neutral compliance analysis, and deliverable creation — all parameterized by domain and profile selected at invocation time.

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
