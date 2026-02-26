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

---

## Storage in marshal.json

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
  resolve-recipe --recipe refactor-to-standards
```

**Output (TOON)**:
```toon
status	success
recipe_key	refactor-to-standards
recipe_name	Refactor to Implementation Standards
recipe_skill	pm-dev-java:recipe-refactor-to-standards
default_change_type	tech_debt
scope	codebase_wide
domain	java
```

---

## Recipe Skill Contract

Each recipe references a skill that handles discovery, analysis, and deliverable creation during phase-3-outline. The recipe skill must follow this structure:

### Required Sections

1. **Skill Resolution**: Resolve skills dynamically from the configured profile (see below)
2. **Scope Selection**: Use module mapping from refine phase or discover all modules
3. **Discovery**: Scan source trees for applicable packages/files
4. **Analysis**: Assess current compliance level per package (read-only agents)
5. **Deliverable Creation**: Create one deliverable per scope unit (package, module)
6. **Outline Writing**: Write solution_outline.md with all deliverables

### Skill Resolution (Critical)

Recipe skills must **not** hardcode skill references. Instead, resolve skills dynamically from the configured profile using `resolve-domain-skills`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-domain-skills --domain {domain} --profile {profile}
```

This returns the aggregated skills for the profile: core defaults + core optionals + profile defaults + profile optionals + project_skills. The resolved skill names are passed to each deliverable's `--skills` argument.

This ensures recipes use the same skills as regular workflow tasks for the same profile, and automatically pick up any project-level skill customizations.

### Deliverable Properties

Each deliverable created by a recipe must include:

- `change_type`: From recipe's `default_change_type`
- `execution_mode`: `automated` (recipes are designed for agent execution)
- `domain`: From the recipe's domain key
- `module`: Module containing the scope unit
- `profile`: Task execution profile (e.g., `implementation`, `module_testing`)
- `skills`: Resolved from configured profile (not hardcoded)

---

## Phase Impact

| Phase | Normal Plan | Recipe Plan |
|-------|-------------|-------------|
| 1-init | Creates plan from task/issue/lesson | Creates plan with `source=recipe`, stores recipe metadata |
| 2-refine | Full quality analysis, iterative clarification | Scope selection only, auto-confidence=100 |
| 3-outline | Detect change_type → route by track → create deliverables | Load recipe skill → recipe handles discovery+analysis+deliverables |
| 4-plan | Standard | Standard (no changes) |
| 5-execute | Standard | Standard (no changes) |
| 6-finalize | Standard | Standard (no changes) |

---

## Implementation Pattern

```python
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Domain extension with recipes."""

    def provides_recipes(self) -> list[dict]:
        """Return domain-specific recipe definitions."""
        return [
            {
                'key': 'refactor-to-standards',
                'name': 'Refactor to Implementation Standards',
                'description': 'Refactor production code to comply with standards, package by package',
                'skill': 'pm-dev-java:recipe-refactor-to-standards',
                'default_change_type': 'tech_debt',
                'scope': 'codebase_wide',
            },
        ]
```

---

## Existing Implementations

| Bundle | Domain | Recipes | Details |
|--------|--------|---------|---------|
| pm-dev-java | java | 2 | `refactor-to-standards` (implementation), `refactor-to-test-standards` (module_testing) |

Bundles without recipes (returns `[]`): pm-dev-frontend, pm-dev-java-cui, pm-documents, pm-plugin-development, pm-requirements.

---

## Related Specifications

- [extension-contract.md](extension-contract.md) — Extension API contract
- [verify-steps.md](verify-steps.md) — Verify steps contract (similar pattern)
- [data-model.md](../../manage-plan-marshall-config/standards/data-model.md) — marshal.json structure
