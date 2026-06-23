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

If the user selects the built-in "Refactor to Profile Standards" recipe, run the multi-domain selection flow defined in [`recipe-refactor-to-profile-standards/workflow/selection-flow.md`](../../recipe-refactor-to-profile-standards/workflow/selection-flow.md). That document is the single source of truth for the selection mechanics — do **not** inline-copy the domain/profile selection screens here. A single recipe run covers ALL auto-detected domains × one chosen profile, with a per-domain user-selected standards-skill set.

The flow's three steps (auto-detect domains, DYNAMIC single-select profile + data-driven `package_source`, per-domain paginated skill multi-select) persist the multi-domain metadata field set (`recipe_domains`, `recipe_profile`, `recipe_package_source`, `recipe_selected_skills__{domain}`) and derive the profile-suffixed `plan_id` (`refactor-to-profile-standards-{profile}`). See the selection-flow document's **Metadata Field Contract** for the field shapes and Step 3 below for how `recipe.md` consumes them.

After running the selection flow, set the static recipe metadata for downstream use:

- `recipe_key` = `refactor-to-profile-standards`
- `recipe_name` = `Refactor to Profile Standards`
- `recipe_skill` = `plan-marshall:recipe-refactor-to-profile-standards`
- `default_change_type` = `tech_debt`
- `scope` = `codebase_wide`

### Step 2: Create Plan via Init Agent

Use the selected recipe to create a plan. Compute the dispatch target via the role resolver:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-1-init
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id none --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target={target} level={level} role=phase-1-init workflow=plan-marshall:phase-1-init/SKILL.md plan_id=none"
```

Dispatch. **For the built-in "Refactor to Profile Standards" recipe**, pass the profile-suffixed `plan_id` override (`refactor-to-profile-standards-{profile}`, derived in the selection flow's Step B3) as the `plan_id` prompt-body field — phase-1-init Step 2 already accepts an explicit `plan_id` override, so two parallel recipe runs for distinct profiles yield distinct, non-colliding plans (and distinct `feature/{plan_id}` branches). **For all other recipes**, pass `plan_id: none` (phase-1-init auto-generates the id):

```
Task: plan-marshall:{target}
  prompt: |
    name: phase-1-init
    plan_id: {profile_suffixed_plan_id_for_builtin_else_none}
    skills[1]:
    - plan-marshall:phase-1-init
    workflow: plan-marshall:phase-1-init/SKILL.md
    WORKTREE: .

    source: recipe
    content: {recipe_key}
```

Substitute `{profile_suffixed_plan_id_for_builtin_else_none}` with `refactor-to-profile-standards-{profile}` on the built-in path (the value derived in the selection flow's Step B3) and `none` on every other path. The agent returns `plan_id` and `domains` in its TOON.

### Step 3: Store Recipe Metadata

After plan creation, store recipe metadata in status:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field plan_source \
  --value recipe

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_key \
  --value {recipe_key}

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field recipe_skill \
  --value {recipe_skill}
```

**For built-in recipe only** — the multi-domain selection flow (Step 1a → [`selection-flow.md`](../../recipe-refactor-to-profile-standards/workflow/selection-flow.md)) ALREADY persisted the following `status.json` metadata fields during its Steps A/B/C; no re-write is required here. The canonical shapes are owned by the selection-flow document's **Metadata Field Contract** — do not restate them; this table names the consumed field set:

| Field | Shape | Persisted by |
|-------|-------|--------------|
| `recipe_domains` | Comma-separated auto-detected domain list (e.g. `java,javascript`) | selection-flow Step A |
| `recipe_profile` | Single chosen profile — any profile a detected domain exposes (NOT limited to `implementation`/`module_testing`) | selection-flow Step B1 |
| `recipe_package_source` | Architecture-iteration field, derived data-driven from the selected profile's declared `package_source` (defaults to `packages`) | selection-flow Step B2 |
| `recipe_selected_skills__{domain}` | One field per detected domain that exposes the chosen profile, holding a comma-separated list of user-selected skill notations | selection-flow Step C |

The generic recipe skill (`plan-marshall:recipe-refactor-to-profile-standards`) consumes this multi-domain field set at runtime. The legacy single-domain `recipe_domain` field is replaced by the comma-separated `recipe_domains` field — there is no per-domain `plan_id` or `recipe_domain` suffix, because a single run spans all detected domains and only the profile is the `plan_id` suffix axis.

### Step 3a: Gather + expand + persist the coverage cell (keyed on `coverage_gathering`)

Read the resolved recipe's `coverage_gathering` field (from the recipe dict resolved in Step 1 / Step 1a; defaults to `none` when the recipe omits it). Branch on its value:

- **`none`** (or absent) — skip coverage gathering entirely. No question is asked; the runtime stays at today's behavior (`inherit/inherit`). `recipe-lesson-cleanup` declares `none` because its forced-surgical scope would be contradicted by a coverage gather.
- **`required`** — run the standard two-question gather (scope + thoroughness) unconditionally. The operator always answers both dial questions; there is no skip path.
- **`optional`** — present a single PRE-STEP skip question first ("Configure coverage for this run?"). If the operator declines, the runtime stays at `inherit/inherit` WITHOUT asking the scope/thoroughness questions at all. If the operator proceeds, the standard two-question gather runs exactly as in the `required` case.

The three values are mutually distinct: `none` asks nothing, `required` always runs the two-question gather, `optional` gates the two-question gather behind one upfront yes/no.

For `required` (always) and for `optional` when the operator chose to proceed, run the contract's canonical `AskUserQuestion` (scope + thoroughness, coupling-constrained, `inherit` default per the [coverage-gathering contract](../../persona-plan-marshall-agent/standards/coverage-gathering-contract.md)), expand the identifier, and persist BOTH the identifier and the expanded instruction to status metadata alongside the existing `recipe_*` fields:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand \
  --thoroughness {thoroughness} --scope {scope}

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field coverage_thoroughness \
  --value {thoroughness}

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field coverage_scope \
  --value {scope}

python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} \
  --set \
  --field coverage_instruction \
  --value {expanded_instruction}
```

`coverage expand` enforces the coupling constraint and emits `error_type: coverage_coupling_violation` for an incoherent cell — re-prompt the gather on that error (do NOT re-implement the coupling math). The recipe skill consumes the persisted `coverage_instruction` at runtime per the contract.

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
- [`recipe-refactor-to-profile-standards/workflow/selection-flow.md`](../../recipe-refactor-to-profile-standards/workflow/selection-flow.md) — Built-in recipe multi-domain selection flow (Step 1a references it; Step 2 passes the profile-suffixed `plan_id`; Step 3 consumes the persisted metadata field set)

## Output

Top-level orchestrator workflow. Conformance to the ext-point output contract:

```toon
status: success | error
display_detail: "<recipe {recipe_key} created plan {plan_id}>"
```

The orchestrator emits this shape when wrapped in a `Task: execution-context-{level}` dispatch. When entered interactively, progress is surfaced via `manage-logging` records on each phase boundary.
