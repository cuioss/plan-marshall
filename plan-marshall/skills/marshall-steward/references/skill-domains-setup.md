# Skill Domain Setup Reference

Extracted skill-domain wizard logic covering applicable-domain detection, domain configuration, active profiles, project-level skill attachment, bulk skills_by_profile population, recipe registration, and final verification. Referenced by `wizard-flow.md` Step 9.

Skill domains are determined from the architecture analysis results. The `extensions_used` field in `_project.json` (populated during the architecture step) contains the bundles whose extensions detected applicable modules in this project.

## Query architecture analysis for applicable domains

The architecture analysis already determined which extensions are applicable by calling each extension's `discover_modules()` method. Query the results:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture derived
```

Look for `extensions_used` in the output - this lists bundles that found modules in the project. If `extensions_used` is empty (no extensions detected any modules), skip the domain-configuration sub-operations below and continue to Verify Skill Domain Configuration.

## Discover available domains

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-available
```

The output lists `discovered_domains[N]{key,bundle,name,applicable}`. Match `extensions_used` bundles from the query above to discovered domain keys.

## Apply domain configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains configure --domains "{comma,separated,keys}"
```

This populates `skill_domains` in marshal.json with: the `system` domain (always) and each selected domain with bundle reference and workflow_skill_extensions (outline, triage, marker-detect). It also seeds `plan.phase-5-execute.verification_steps` with the built-in verify steps.

## Configure Active Profiles

Control which profiles are emitted during architecture enrichment. Ask the user to choose Default (recommended: `implementation,module_testing,quality`), All profiles (no filtering), or Custom (multiSelect from `implementation,module_testing,integration_testing,quality,documentation`). Apply the chosen list (skip apply entirely for "All profiles"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains active-profiles set --profiles {comma-separated selection}
```

## Discover and Attach Project-Level Skills

Scan `.claude/skills/` for project-level skills and let the user assign them to configured domains.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains discover-project
```

**Output (TOON)**:
```toon
status: success
count: 2
skills:
  - notation: project:sync-plugin-cache
    name: sync-plugin-cache
    description: Synchronize all marketplace bundles to the Claude plugin cache
  - notation: project:finalize-step-plugin-doctor
    name: finalize-step-plugin-doctor
    description: Finalize-phase wrapper that runs plugin-doctor against skills touched by the plan
```

If skills are found (`count > 0`), present them to the user with `AskUserQuestion`:
- List each discovered skill with its description
- For each skill, let the user select which configured domain to attach it to:
  - "system" = cross-domain (always loaded)
  - A specific domain (e.g., "documentation") = loaded during that domain's tasks
  - "skip" = do not attach

For each assignment, call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains attach-project --domain {domain} --skills {comma-separated project:skill notations}
```

If no project-level skills are found (`count == 0`), skip this sub-operation silently.

## Bulk Populate skills_by_profile

Populate `skills_by_profile` for every module × every applicable extension so that downstream `phase-4-plan` tasks always receive a non-empty skill list. This `enrich-all` invocation iterates across all discovered modules and all configured domain extensions in a single call, eliminating the need for per-module enrichment loops.

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture enrich all
```

**Output (TOON)**:

| Field | Description |
|-------|-------------|
| `modules_enriched` | Count of modules that received at least one `skills_by_profile` update |
| `pairs_applied` | Number of (module, domain) pairs where skills were successfully written |
| `pairs_skipped` | Number of (module, domain) pairs that were skipped (not applicable or already populated with identical content) |
| `errors` | Array of per-pair error entries; empty on a fully clean run |

**Handling errors**: If `errors` is non-empty, log the error list for review. The run is still considered successful because each (module, domain) pair is isolated — a failure on one pair does not block others from being populated. Do not abort the wizard.

**Idempotency**: The command is idempotent — re-running `/marshall-steward` is safe and produces `pairs_applied=0` on subsequent runs when nothing has changed, so the wizard can be executed repeatedly without side effects.

## Register Recipes (Discovery Only)

Recipes are deterministic plan templates that bypass the iterative refine → outline → Q-Gate pipeline. The wizard does not "configure" recipes — they self-register at runtime via three sources:

1. **Built-in** — `provides_recipes()` in `plan-marshall-plugin/extension.py` (always available).
2. **Project-local** — `recipe-*` skills under `.claude/skills/` (zero-config; just drop the skill).
3. **Extension-provided** — `provides_recipes()` callbacks from any active extension's domain bundle.

Enumerate the recipes currently visible to the steward to confirm the project picked up the expected ones:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-recipes
```

**Recipe-registration flow** (showing how a new recipe surfaces):

```text
       ┌──────────────────────────────────────────────┐
       │ Source 1: extension.provides_recipes()       │
       │   plan-marshall-plugin → refactor-to-...     │
       │   plan-marshall-plugin → lesson_cleanup      │
       └────────────────────┬─────────────────────────┘
                            │
       ┌──────────────────────────────────────────────┐
       │ Source 2: .claude/skills/recipe-*/SKILL.md   │
       │   (project-local recipes, no plugin.json)    │
       └────────────────────┬─────────────────────────┘
                            │
       ┌──────────────────────────────────────────────┐
       │ Source 3: extension.provides_recipes() from  │
       │   any active extension bundle                 │
       └────────────────────┬─────────────────────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │ _discover_all_recipes  │
                │ (manage-config helper) │
                └───────────┬────────────┘
                            │ output consumed by:
                            ▼
       ┌──────────────────────────────────────────────┐
       │ • manage-config list-recipes                 │
       │ • manage-config resolve-recipe --recipe KEY  │
       │ • marshall-steward Configuration → Recipes   │
       │ • phase-1-init --recipe KEY (explicit)       │
       │ • phase-1-init Step 5c (auto-suggest)        │
       └──────────────────────────────────────────────┘
```

**Two built-in recipes ship with plan-marshall**:

- `refactor-to-profile-standards` (codebase_wide, tech_debt) — Iterates packages across modules.
- `lesson_cleanup` (single_lesson, change_type derived from lesson kind) — Auto-suggested by `phase-1-init` Step 5c when `source == lesson` and the lesson body is doc-shaped.

**No wizard configuration is required for built-in recipes** — they are always available once the plugin is installed and the executor is generated. The wizard's only role is to surface them via `references/menu-recipes.md` so users know they exist. Project-local recipes (Source 2) require dropping a `recipe-*` skill under `.claude/skills/` and re-running `/marshall-steward` to regenerate the executor with the new notation.

See [`references/menu-recipes.md`](menu-recipes.md) for the full catalog and the procedure to add a new built-in recipe.

## Verify Skill Domain Configuration

Skill domains configure which implementation skills are loaded during plan execution. The `system` domain holds the base `defaults`/`optionals`; technical domains hold bundle reference and workflow_skill_extensions (outline, triage, marker-detect).

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains list
```

Confirm that each technical domain has a `bundle` reference. Profiles (core, implementation, module_testing, etc.) are loaded at runtime from `extension.py`.
