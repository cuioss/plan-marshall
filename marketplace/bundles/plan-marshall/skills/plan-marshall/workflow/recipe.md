---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

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
  skill-domains list
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

Use the selected recipe to create a plan. Compute the dispatch target via the role resolver:

```bash
target=$(python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-1-init)
```

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id none --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-1-init workflow=plan-marshall:phase-1-init/SKILL.md plan_id=none"
```

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: phase-1-init
    plan_id: none
    skills[1]:
    - plan-marshall:phase-1-init
    workflow: plan-marshall:phase-1-init/SKILL.md
    WORKTREE: .

    source: recipe
    content: {recipe_key}
```

The agent returns `plan_id` and `domains` in its TOON.

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

Continue through the standard phases — each phase is dispatched under its
role key per the same contract documented in [`planning.md`](planning.md)
("Action: init" → 2-Refine Phase) and [`planning-outline.md`](planning-outline.md)
("Action: outline"). The orchestrator resolves the dispatch target via
`effort resolve-target --role phase-{N}` and dispatches
`Task: plan-marshall:{target}` with `workflow=plan-marshall:phase-{N}-{name}/SKILL.md`.

1. **2-refine** — role key `phase-2-refine`; workflow `phase-2-refine/SKILL.md`.
   Recipe plans get automatic scope selection and confidence=100.
2. **3-outline** — role key `phase-3-outline`; workflow `phase-3-outline/SKILL.md`.
   Recipe plans skip change-type detection and Q-Gate, and load the recipe
   skill directly inside the envelope.
3. **4-plan** — role key `phase-4-plan`; workflow `phase-4-plan/SKILL.md`.
   Standard task creation from deliverables.

After completing phases 1-4, check `execute_without_asking` config:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan get --field execute_without_asking --audit-plan-id {plan_id}
```

- If false (default): STOP and wait for execute action
- If true: Auto-continue to execute phase

---

## Related

- `plan-marshall:extension-api` — `provides_recipes()` method in ExtensionBase
- `plan-marshall:phase-2-refine` — Recipe shortcut (scope selection only)
- `plan-marshall:phase-3-outline` — Recipe-aware routing (skip change-type detection)

## Output

Top-level orchestrator workflow. Conformance to the ext-point output contract:

```toon
status: success | error
display_detail: "<recipe {recipe_key} created plan {plan_id}>"
```

The orchestrator emits this shape when wrapped in a `Task: execution-context-{level}` dispatch. When entered interactively, progress is surfaced via `manage-logging` records on each phase boundary.
