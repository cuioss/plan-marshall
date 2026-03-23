# Recipe Workflow

Workflow for creating plans from predefined recipes — repeatable transformations that already know WHAT to do and HOW.

**CRITICAL CONSTRAINT**: This workflow creates and manages **plans only**. NEVER implement tasks directly.

---

## Action: recipe

Create a plan from a predefined recipe. Recipes bypass change-type detection and provide their own discovery, analysis, and deliverable patterns.

### Step 1: List or Resolve Recipe

Collect recipes from all sources, then present via `AskUserQuestion`.

**Built-in recipes** (always available when domains are configured):
- "Refactor to Profile Standards" — Refactor code to comply with configured profile standards, package by package. Requires: configured domains.

**Domain recipes** (custom recipes registered via `provides_recipes()`) and **project recipes** (added via `skill-domains add-recipe`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  list-recipes
```

This returns both extension-provided and project-level recipes. Project recipes have `"source": "project"` in their metadata.

Present the combined list using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "Which recipe would you like to use?"
      header: "Recipes"
      options:
        # Always include built-in:
        - label: "Refactor to Profile Standards"
          description: "Refactor code to comply with configured profile standards, package by package"
        # For each domain/project recipe (dynamic):
        - label: "{recipe_name}"
          description: "{recipe_description} (source: {source})"
      multiSelect: false
```

If no domain or project recipes exist, only show the built-in recipe.

**If `recipe` parameter provided** — resolve directly:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-recipe --recipe {recipe_key}
```

If recipe not found, show error with available recipes.

### Step 1a: Built-in Recipe Selected

If the user selects the built-in "Refactor to Profile Standards" recipe:

1. **Select domain**: Query configured domains and present for selection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  list-domains
```

Present domain selection using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "Which domain should be refactored?"
      header: "Domain"
      options:
        # For each configured domain (dynamic):
        - label: "{domain_name}"
          description: "Domain from {source}"
      multiSelect: false
```

2. **Select profile**: Present profile selection using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "Which code should be refactored?"
      header: "Profile"
      options:
        - label: "Implementation"
          description: "Refactor production code"
        - label: "Module testing"
          description: "Refactor test code"
      multiSelect: false
```

3. **Derive package source** from profile:
   - `implementation` → `packages`
   - `module_testing` → `test_packages`

4. Set recipe metadata for downstream use:
   - `recipe_key` = `refactor-to-profile-standards`
   - `recipe_name` = `Refactor to Profile Standards`
   - `recipe_skill` = `plan-marshall:recipe-refactor-to-profile-standards`
   - `default_change_type` = `tech_debt`
   - `scope` = `codebase_wide`

### Step 2: Create Plan via Init Agent

Use the selected recipe to create a plan:

```
Task: plan-marshall:phase-agent
  Input: skill=plan-marshall:phase-1-init, source=recipe, content={recipe_key}
  Output: plan_id, domains array
```

### Step 3: Store Recipe Metadata

After plan creation, store recipe metadata in status:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field plan_source \
  --value recipe

python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_key \
  --value {recipe_key}

python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_skill \
  --value {recipe_skill}
```

**For built-in recipe only** — store additional fields for the generic recipe skill:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_domain \
  --value {selected_domain}

python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_profile \
  --value {selected_profile}

python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_package_source \
  --value {derived_package_source}
```

### Step 4: Continue Through Phases

Continue through the standard phases:

1. **2-refine**: Load `Skill: plan-marshall:phase-2-refine` with `plan_id`
   - Recipe plans get automatic scope selection and confidence=100
2. **3-outline**: Load `Skill: plan-marshall:phase-3-outline` with `plan_id`
   - Recipe plans skip change-type detection and Q-Gate, load recipe skill directly
3. **4-plan**: Load `Skill: plan-marshall:phase-4-plan` with `plan_id`
   - Standard task creation from deliverables

After completing phases 1-4, check `execute_without_asking` config:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan get --field execute_without_asking --trace-plan-id {plan_id}
```

- If false (default): STOP and wait for execute action
- If true: Auto-continue to execute phase

---

## Related

- `plan-marshall:extension-api` — `provides_recipes()` method in ExtensionBase
- `plan-marshall:phase-2-refine` — Recipe shortcut (scope selection only)
- `plan-marshall:phase-3-outline` — Recipe-aware routing (skip change-type detection)
