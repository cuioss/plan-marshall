# Recipe Workflow

Workflow for creating plans from predefined recipes — repeatable transformations that already know WHAT to do and HOW.

**CRITICAL CONSTRAINT**: This workflow creates and manages **plans only**. NEVER implement tasks directly.

---

## Action: recipe

Create a plan from a predefined recipe. Recipes bypass change-type detection and provide their own discovery, analysis, and deliverable patterns.

### Step 1: List or Resolve Recipe

**If no `recipe` parameter provided** — list available recipes for selection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  list-recipes
```

Present the list to the user with numbered selection:

```
Available Recipes:

1. Refactor to Implementation Standards
   Refactor production code to comply with java-core and java-maintenance standards, package by package
   Domain: java | Scope: codebase_wide

2. Refactor to Test Standards
   Refactor test code to comply with junit-core standards, test-package by test-package
   Domain: java | Scope: codebase_wide

Select recipe (number):
```

If no recipes are available, inform the user and exit.

**If `recipe` parameter provided** — resolve directly:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-recipe --recipe {recipe_key}
```

If recipe not found, show error with available recipes.

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
