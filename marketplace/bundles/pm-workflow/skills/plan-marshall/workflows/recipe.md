# Recipe Workflow

Workflow for creating plans from predefined recipes — repeatable transformations that already know WHAT to do and HOW.

**CRITICAL CONSTRAINT**: This workflow creates and manages **plans only**. NEVER implement tasks directly.

---

## Action: recipe

Create a plan from a predefined recipe. Recipes bypass change-type detection and provide their own discovery, analysis, and deliverable patterns.

### Step 1: List or Resolve Recipe

Present two categories of recipes to the user:

**Built-in recipes** (always available when domains are configured):

```
Built-in Recipes:

1. Refactor to Profile Standards
   Refactor code to comply with configured profile standards, package by package
   Requires: configured domains
```

**Domain recipes** (custom recipes registered via `provides_recipes()`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  list-recipes
```

Present the combined list to the user with numbered selection. If no domain recipes exist, only show the built-in recipe.

**If `recipe` parameter provided** — resolve directly:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-recipe --recipe {recipe_key}
```

If recipe not found, show error with available recipes.

### Step 1a: Built-in Recipe Selected

If the user selects the built-in "Refactor to Profile Standards" recipe:

1. **Select domain**: Query configured domains and present for selection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  list-domains
```

2. **Select profile**: Ask user to choose between:
   - `implementation` — Refactor production code
   - `module_testing` — Refactor test code

3. **Derive package source** from profile:
   - `implementation` → `packages`
   - `module_testing` → `test_packages`

4. Set recipe metadata for downstream use:
   - `recipe_key` = `refactor-to-profile-standards`
   - `recipe_name` = `Refactor to Profile Standards`
   - `recipe_skill` = `pm-workflow:recipe-refactor-to-profile-standards`
   - `default_change_type` = `tech_debt`
   - `scope` = `codebase_wide`

### Step 2: Create Plan via Init Agent

Use the selected recipe to create a plan:

```
Task: pm-workflow:plan-init-agent
  Input:
    description: "{recipe_name}: {recipe_description}"
    source: recipe
    source_id: {recipe_key}
  Output: plan_id, domains array
```

### Step 3: Store Recipe Metadata

After plan creation, store recipe metadata in status:

```bash
python3 .plan/execute-script.py pm-workflow:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field plan_source \
  --value recipe

python3 .plan/execute-script.py pm-workflow:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_key \
  --value {recipe_key}

python3 .plan/execute-script.py pm-workflow:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_skill \
  --value {recipe_skill}
```

**For built-in recipe only** — store additional fields for the generic recipe skill:

```bash
python3 .plan/execute-script.py pm-workflow:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_domain \
  --value {selected_domain}

python3 .plan/execute-script.py pm-workflow:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_profile \
  --value {selected_profile}

python3 .plan/execute-script.py pm-workflow:manage-status:manage_status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_package_source \
  --value {derived_package_source}
```

### Step 4: Continue Through Phases

Continue through the standard phases:

1. **2-refine**: Load `Skill: pm-workflow:phase-2-refine` with `plan_id`
   - Recipe plans get automatic scope selection and confidence=100
2. **3-outline**: Load `Skill: pm-workflow:phase-3-outline` with `plan_id`
   - Recipe plans skip change-type detection, load recipe skill directly
3. **4-plan**: Load `Skill: pm-workflow:phase-4-plan` with `plan_id`
   - Standard task creation from deliverables

After completing phases 1-4, check `execute_without_asking` config:
- If false (default): STOP and wait for execute action
- If true: Auto-continue to execute phase

---

## Related

- `plan-marshall:extension-api` — `provides_recipes()` method in ExtensionBase
- `pm-workflow:phase-2-refine` — Recipe shortcut (scope selection only)
- `pm-workflow:phase-3-outline` — Recipe-aware routing (skip change-type detection)
