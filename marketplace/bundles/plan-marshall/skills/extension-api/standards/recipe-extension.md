# Recipe Extension Contract

Extension hook for declaring domain-specific recipe definitions — predefined, repeatable transformations applied to a codebase.

## Purpose

Provides a hook for extensions to declare recipes — predefined transformations that already know WHAT to do and HOW. Unlike ad-hoc plans, recipes only need to discover WHERE to apply. This enables:

- Standards compliance sweeps (refactor to coding standards, package by package)
- Test quality improvements (refactor tests to testing standards)
- Security reviews, documentation updates, and other repeatable tasks
- Codebase-wide transformations with package-level granularity

---

## Lifecycle Position

The hook is invoked by `marshall-steward` during domain configuration:

```
1. Extension discovery and loading
2. get_skill_domains() → domain metadata
3. ➤ provides_recipes() → recipe definitions per domain
4. Recipes stored in marshal.json under skill_domains.{domain}.recipes
5. /plan-marshall action=recipe reads config → presents selection UI
6. Selected recipe drives phases 1-3 (init, refine, outline)
```

**Timing**: Called during `/marshall-steward` domain configuration (`skill-domains configure`). Recipes are persisted in `marshal.json` and consumed at plan-time by `/plan-marshall action=recipe`.

---

## Method Signature

```python
def provides_recipes(self) -> list[dict]:
    """Return domain-specific recipe definitions.

    Recipes are predefined, repeatable transformations that provide their own
    discovery, analysis, and deliverable patterns. Unlike ad-hoc plans, recipes
    already know WHAT to do and HOW — they only discover WHERE to apply.

    Returns:
        List of recipe dicts, each containing:
        - key: str           # Unique identifier (e.g., 'null-safety-compliance')
        - name: str          # Human-readable name
        - description: str   # Brief description for selection UI
        - skill: str         # Skill reference (e.g., 'pm-dev-java:recipe-null-safety')
        - default_change_type: str  # Default change_type for deliverables
        - scope: str         # 'single_module' | 'multi_module' | 'codebase_wide'

    Default implementation returns empty list (no recipes).
    """
    return []
```

---

## Return Structure

Each dict in the returned list must contain:

| Field | Type | Description |
|-------|------|-------------|
| `key` | str | Unique identifier — used as recipe key in marshal.json and status metadata |
| `name` | str | Human-readable name for selection UI |
| `description` | str | Brief description explaining what the recipe does |
| `skill` | str | Skill reference (`bundle:skill`) loaded during phase-3-outline |
| `default_change_type` | str | Change type for deliverables (e.g., `tech_debt`, `feature`) |
| `scope` | str | Scope hint: `single_module`, `multi_module`, or `codebase_wide` |
| `profile` | str | (Optional) Execution profile (e.g., `implementation`, `module_testing`). Used by custom recipes that need profile-specific behavior |
| `package_source` | str | (Optional) Package source field name (`packages` or `test_packages`). Used by custom recipes that iterate architecture packages |

**Note**: The built-in "Refactor to Profile Standards" recipe is provided by pm-workflow. Domains only need `provides_recipes()` for truly custom recipes that require domain-specific logic beyond profile-based refactoring.

---

## Storage in marshal.json

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
      ],
      "workflow_skill_extensions": { "triage": "..." }
    }
  }
}
```

---

## Resolution Commands

Two commands support recipe discovery at plan-time:

### list-recipes

Aggregates recipes from all configured domains:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  list-recipes
```

**Output (TOON)**:
```toon
status	success
count	2
recipes	[{"key": "refactor-to-standards", "name": "Refactor to Implementation Standards", "domain": "java", ...}]
```

### resolve-recipe

Resolves a specific recipe by key:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-recipe --recipe null-safety-compliance
```

**Output (TOON)**:
```toon
status	success
recipe_key	null-safety-compliance
recipe_name	Null Safety Compliance
recipe_skill	pm-dev-java:recipe-null-safety
default_change_type	tech_debt
scope	codebase_wide
domain	java
profile	implementation
package_source	packages
```

Fields `profile` and `package_source` are empty strings when not set on the recipe.

---

## Recipe Skill Interface

All recipe skills — built-in and custom — are loaded by phase-3-outline via the same `Skill: {recipe_skill}` call. This section defines the contract.

### Input Parameters

Phase-3-outline passes these input parameters to the recipe skill:

| Parameter | Type | Guaranteed | Description |
|-----------|------|------------|-------------|
| `plan_id` | string | Always | Plan identifier |
| `recipe_domain` | string | Built-in only | Domain key (e.g., `java`). Empty for custom recipes unless the extension sets `profile`/`package_source` on the recipe dict |
| `recipe_profile` | string | Built-in only | Profile name (e.g., `implementation`). Empty for custom recipes unless set |
| `recipe_package_source` | string | Built-in only | Architecture field to iterate (`packages` or `test_packages`). Empty for custom recipes unless set |

Custom recipes that need these values should declare `profile` and `package_source` on the recipe dict in `provides_recipes()`. The recipe workflow stores them in status metadata, and phase-3-outline passes them as input.

### Required Sinks

The recipe skill must write:

| Sink | Description |
|------|-------------|
| `solution_outline.md` | Deliverables grouped by module, written via `manage-solution-outline write` |

### Required Deliverable Properties

| Property | Source |
|----------|--------|
| `change_type` | Recipe's `default_change_type` (set by phase-3-outline before skill load) |
| `execution_mode` | `automated` |
| `domain` | Input `recipe_domain` or hardcoded |
| `module` | From architecture discovery |
| `profile` | Input `recipe_profile` or hardcoded |
| `skills` | Resolved dynamically via `resolve-domain-skills` (not hardcoded) |
| Affected files | From architecture data |

### Skill Resolution (Critical)

Recipe skills must **not** hardcode skill references. Instead, resolve skills dynamically:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-domain-skills --domain {domain} --profile {profile}
```

This returns core defaults + core optionals + profile defaults + profile optionals + project_skills. The resolved skill names are passed to each deliverable's `--skills` argument.

For the full flow with ASCII diagrams, see `pm-workflow:phase-3-outline` [references/recipe-flow.md](../../phase-3-outline/references/recipe-flow.md).

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

## Implementation Pattern

The built-in "Refactor to Profile Standards" recipe in pm-workflow handles the common case of refactoring code to comply with profile standards. Domains only need custom recipes for domain-specific logic:

```python
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Domain extension with custom recipes."""

    def provides_recipes(self) -> list[dict]:
        """Return domain-specific recipe definitions."""
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

---

## Built-in vs Custom Recipes

| Type | Source | When to use |
|------|--------|-------------|
| **Built-in** | pm-workflow `recipe-refactor-to-profile-standards` | Standard refactoring to profile standards (any domain/profile) |
| **Custom** | Domain `provides_recipes()` | Domain-specific transformations requiring custom discovery/analysis logic |

The built-in recipe handles: skill resolution, module listing, package iteration, neutral compliance analysis, and deliverable creation — all parameterized by domain and profile.

---

## Existing Implementations

All standard refactoring recipes are handled by the built-in pm-workflow recipe. No domain bundles currently register custom recipes.

Bundles returning `[]`: pm-dev-java, pm-dev-frontend, pm-dev-java-cui, pm-documents, pm-plugin-development, pm-requirements.

---

## Related Specifications

- [extension-contract.md](extension-contract.md) — Extension API contract
- [verify-steps.md](verify-steps.md) — Verify steps contract (similar pattern)
- [data-model.md](../../manage-plan-marshall-config/standards/data-model.md) — marshal.json structure
