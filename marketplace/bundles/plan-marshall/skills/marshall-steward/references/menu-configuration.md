# Menu Option: Configuration

Sub-menu for skill domains and project structure configuration.

## Table of Contents

- [Configuration Submenu](#configuration-submenu)
- [Routing](#routing)
- [Configuration: Plan Phase Settings](#configuration-plan-phase-settings)
- [Configuration: Review Gates](#configuration-review-gates)
- [Configuration: Quality Pipelines](#configuration-quality-pipelines)
- [Configuration: Skill Domains](#configuration-skill-domains)
- [Configuration: Project Structure](#configuration-project-structure)
- [Configuration: Terminal Title](#configuration-terminal-title)
- [Configuration: Recipes](#configuration-recipes)

---

## Configuration Submenu

```
AskUserQuestion:
  question: "What would you like to configure?"
  options:
    - label: "Skill Domains"
      description: "Configure implementation skills per domain"
      value: "skill-domains"
    - label: "Plan Phase Settings"
      description: "Branching, compatibility, commit strategy"
      value: "plan-phases"
    - label: "Project Structure"
      description: "View, regenerate, and enrich architecture data"
      value: "structure"
    - label: "Quality Pipelines"
      description: "Verification and finalize step pipelines"
      value: "quality-pipelines"
    - label: "Review Gates"
      description: "Auto-continue between phases or pause for review"
      value: "review-gates"
    - label: "Credentials & Secrets"
      description: "Manage external tool credentials"
      value: "credentials"
    - label: "Terminal Title"
      description: "Dynamic terminal tab title + statusline (hook-driven)"
      value: "terminal-title"
    - label: "Recipes"
      description: "Browse built-in plan recipes (lesson_cleanup, refactor-to-profile-standards)"
      value: "recipes"
    - label: "Full Reconfigure"
      description: "Re-run setup wizard from Step 5 onwards (skips bootstrap steps 1-4)"
      value: "wizard"
```

## Routing

| Selection | Action |
|-----------|--------|
| skill-domains | Execute "Configuration: Skill Domains" below |
| plan-phases | Execute "Configuration: Plan Phase Settings" below |
| quality-pipelines | Execute "Configuration: Quality Pipelines" below |
| review-gates | Execute "Configuration: Review Gates" below |
| structure | Execute "Configuration: Project Structure" below |
| credentials | Execute "Configuration: Credentials & Secrets" below |
| terminal-title | Load `Read references/menu-terminal-title.md` → Execute |
| recipes | Load `Read references/menu-recipes.md` → Execute "Configuration: Recipes" below |
| wizard | Load `Read references/wizard-flow.md` — skip to Step 5 (bootstrap already done) |

> **Note**: Recipe registration affects which menu items appear here. A recipe whose extension is not active in the project is hidden from selection lists. See `references/menu-recipes.md` for the full catalog of built-in and project-local recipes and how to add new ones.

---

## Configuration: Plan Phase Settings

Configure plan phase settings using manage-config. Show current values first:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get
```

Display current values, then ask user which settings to change:

**Branch strategy** (phase-1-init): `feature` (recommended) or `direct`
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init set --field branch_strategy --value {direct|feature}
```

**Backward compatibility** (phase-2-refine): `breaking` (recommended), `deprecation`, or `smart_and_ask`
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field compatibility --value {breaking|deprecation|smart_and_ask}
```

**Commit strategy** (phase-5-execute): `per_deliverable` (recommended), `per_plan`, or `none`
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field commit_strategy --value {per_deliverable|per_plan|none}
```

**Rebase on execute start** (phase-5-execute): `true` (recommended, default) or `false`. Controls whether phase-5-execute runs a sync-with-main step before the task loop.
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field rebase_on_execute_start --value {true|false}
```

**Rebase strategy** (phase-5-execute): `merge` (recommended, default) or `rebase`. Used by the sync-with-main step — `merge` runs `git merge --no-edit origin/{base}` (PR-safe, no history rewrite); `rebase` runs `git rebase origin/{base}` (rewrites history, requires force-push when a PR is already open).
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field rebase_strategy --value {merge|rebase}
```

**Confidence threshold** (phase-2-refine, menu-only): `95` (recommended), `90`, or `100`
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field confidence_threshold --value {95|90|100}
```

---

## Configuration: Review Gates

Show current values first:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-3-outline get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get
```

Display current gate values, then ask user which transitions should auto-continue (multi-select):
- "Plan without asking" → outline to planning
- "Execute without asking" → planning to execution
- "Finalize without asking" → execution to finalize

Apply each selection via manage-config:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-3-outline set --field plan_without_asking --value {true|false}
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan set --field execute_without_asking --value {true|false}
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field finalize_without_asking --value {true|false}
```

---

## Configuration: Quality Pipelines

Show current config first:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get
```

Display current values, then configure pipelines using manage-config:

**Verification steps** (phase-5-execute): Discover available steps, present as multi-select, resolve order (see **Order resolution sub-flow** below), then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps {comma_separated_selected_steps}
```
Assert the `set-steps` response is `status: success`. A non-success response means the pre-flight order resolution missed a case — re-run the sub-flow for the reported `step` or `steps`.

After `set-steps` completes for phase-5-execute, validate that every `project:` step in the new selection has a matching `Skill()` allow rule:
```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-missing-project-step-permissions \
  --marshal .plan/marshal.json \
  --scope project
```

If `missing` is non-empty, ask user:
```
AskUserQuestion:
  question: "{N} project-step(s) in your phase-5-execute selection lack matching Skill() allow rules. Add them?"
  options:
    - label: "Yes"
      description: "Add missing rules to project settings to avoid permission prompts"
    - label: "No"
      description: "Skip (may cause permission prompts during execute)"
```

If yes, apply fixes:
```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-project-step-permissions \
  --marshal .plan/marshal.json \
  --settings .claude/settings.json
```

**Finalize steps** (phase-6-finalize): Discover available steps, present as multi-select, resolve order (see **Order resolution sub-flow** below), then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
```

The `list-finalize-steps` output includes four sources: built-in (`default:*`), project-local (`project:*`), extension-provided, and **bundle-optional** (`OPTIONAL_BUNDLE_FINALIZE_STEPS`). Bundle-optional entries — such as `plan-marshall:plan-retrospective` — surface in the multi-select but are intentionally absent from the default `plan.phase-6-finalize.steps` list, so operators must opt in explicitly by selecting them here. Example multi-select presentation (built-ins plus the opt-in retrospective):

```
AskUserQuestion:
  question: "Which finalize steps to include?"
  header: "Finalize Steps"
  multiSelect: true
  options:
    - label: "default:commit-push (Recommended)"
      description: "Commit and push changes"
    - label: "default:create-pr"
      description: "Create pull request"
    - label: "default:automated-review"
      description: "CI automated review"
    - label: "default:knowledge-capture (Recommended)"
      description: "Capture learnings to memory"
    - label: "default:lessons-capture (Recommended)"
      description: "Record lessons learned"
    - label: "plan-marshall:plan-retrospective (Opt-in)"
      description: "Capture a structured retrospective of the completed plan"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-steps --steps {comma_separated_selected_steps}
```
Assert the `set-steps` response is `status: success`. A non-success response means the pre-flight order resolution missed a case — re-run the sub-flow for the reported `step` or `steps`.

After `set-steps` completes for phase-6-finalize, repeat the same project-step validation and auto-fix flow described above for phase-5 — the same `detect-missing-project-step-permissions` and `apply-project-step-permissions` calls cover both phases.

#### Order resolution sub-flow

Run this sub-flow between `list-*-steps` and `set-steps` so the latter never errors with `missing_order` or `order_collision`. It is invoked for both `phase-5-execute` (verify steps) and `phase-6-finalize` (finalize steps); substitute `{phase}` with the appropriate section.

1. Filter the `list-*-steps` output to the user-selected `{selected_steps}`. For each selected step, read its `order` value.
2. **Missing order** — For every selected step whose `order` is `null`, prompt the user:
   ```
   AskUserQuestion:
     question: "Step '{step_ref}' has no declared order. Pick an integer to position it in the {phase} pipeline."
     options:
       - label: "Before built-ins (0)"          # runs first
       - label: "Mid-pipeline (500)"            # common default slot
       - label: "End of pipeline (2000)"        # runs last
       - label: "Custom..."                      # user types integer
   ```
   Persist the chosen value:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan {phase} set-step-order-override --step {step_ref} --order {value}
   ```
3. **Order collision** — Group the remaining selected steps by resolved `order`. For every group with >1 entry, prompt:
   ```
   AskUserQuestion:
     question: "Steps '{step_a}' and '{step_b}' both resolve to order={N} in {phase}. How should we disambiguate?"
     options:
       - label: "Keep {step_a}'s order ({N}); reassign {step_b}"
       - label: "Keep {step_b}'s order ({N}); reassign {step_a}"
       - label: "Set both to new values"
   ```
   Apply the user's choice via one or two `set-step-order-override` calls — the reassigned step(s) need fresh values that do not collide with any other selected step.
4. Loop steps 2 and 3 until every selected step has a distinct resolved order. Only then call `set-steps` — which now sorts by `order` — and assert `status: success`.
5. If a previously persisted override is no longer needed (e.g., the user removed the step from the selection and wants to reset its order), clear it explicitly:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan {phase} remove-step-order-override --step {step_ref}
   ```

**PR merge strategy**: Ask user for the merge strategy used when merging PRs during branch cleanup (default: squash):

```
AskUserQuestion:
  questions:
    - question: "Which merge strategy should be used when merging PRs?"
      header: "PR Merge"
      options:
        - label: "squash (Recommended)"
          description: "Squash all commits into one before merging"
        - label: "merge"
          description: "Create a merge commit preserving all commits"
        - label: "rebase"
          description: "Rebase commits onto the base branch"
      multiSelect: false
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set --field pr_merge_strategy --value {squash|merge|rebase}
```

**Max iterations**: Ask user for verification iterations (default 5) and finalize iterations (default 3):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-max-iterations --value {5|3|10}
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-max-iterations --value {3|1|5}
```

---

## Configuration: Skill Domains

Skill domains configure which implementation skills are loaded for different code types. Applicable domains are determined from architecture analysis results.

### Reconfigure Skill Domains

**Step 1: Get applicable domains from architecture analysis**

Query `extensions_used` from the architecture analysis (populated during project discovery):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture derived
```

Look for `extensions_used` in the output - these are bundles that detected modules in this project.

**Step 2: Map bundles to domain keys**

Get all available domains with bundle mappings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get-available
```

Bundle to domain key mapping:
- `pm-dev-java` → `java`
- `pm-dev-java-cui` → `java-cui`
- `pm-dev-frontend` → `javascript`
- `pm-plugin-development` → `plan-marshall-plugin-dev`
- `pm-documents` → `documentation`
- `pm-requirements` → `requirements`

**Step 3: User domain selection**

Present AskUserQuestion with applicable domains pre-selected:

```yaml
AskUserQuestion:
  question: "Confirm skill domains for this project:"
  header: "Skill Domains"
  multiSelect: true
  options:
    # Pre-select domains from extensions_used
    # Show all available domains, mark applicable ones
    - label: "Java Development (detected)"
      description: "Java code patterns, CDI, JUnit (pm-dev-java)"
    - label: "Documentation (detected)"
      description: "AsciiDoc, ADRs (pm-documents)"
    - label: "JavaScript Development"
      description: "Modern JS, ESLint, Jest (pm-dev-frontend)"
    - label: "Plugin Development"
      description: "Claude Code components (pm-plugin-development)"
```

**Step 4: Configure selected domains**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains configure --domains "java,documentation"
```

This configures:
- `system` domain (always) with task_executors
- Each selected domain with bundle reference and workflow_skill_extensions
- Auto-appends extension verify steps to `plan.phase-5-execute.steps`

**Note**: The `configure` command replaces all existing domains with the selected ones.

### List Domains

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains list
```

### View Domain Configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains get --domain java
```

### Resolve Domain Skills (for task planning)

Aggregate core + profile skills with descriptions for LLM skill selection:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config resolve-domain-skills \
  --domain java --profile implementation
```

### Update Domain Skills

Update skills for a specific profile:

```bash
# Update implementation profile skills
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config skill-domains set \
  --domain java \
  --profile implementation \
  --defaults "pm-dev-java:java-core" \
  --optionals "pm-dev-java:java-cdi,pm-dev-java:java-maintenance"
```

---

## Configuration: Project Structure

Manage project structure knowledge including module metadata, placement rules, and conventions.

### Step 1: Select Operation

```yaml
AskUserQuestion:
  question: "What would you like to do with project structure?"
  header: "Operation"
  options:
    - label: "View"
      description: "Display current project structure"
    - label: "Edit Module"
      description: "Update module metadata (layer, responsibility, tips)"
    - label: "Manage Placement"
      description: "Add or update placement rules"
    - label: "Regenerate"
      description: "Re-detect structure from project files"
  multiSelect: false
```

### Operation: View

Display current project architecture:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
```

Shows all modules with their purpose, responsibilities, and key packages.

### Operation: View Module Details

**Step 1: List modules**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

**Step 2: Get module details**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture module --module "{module}"
```

For full details including reasoning:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture module --module "{module}" --full
```

### Operation: Enrich Module

Add learned information to a module:

```bash
# Update responsibility
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich module --name "{module}" --responsibility "{description}"

# Add tip
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich tip --module "{module}" --tip "{tip text}"

# Add insight
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich insight --module "{module}" --insight "{insight text}"

# Add best practice
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich best-practice --module "{module}" --practice "{practice text}"
```

### Operation: Regenerate

Regenerate project architecture from build files with optional enrichment.

**Step 1: Check for existing enrichment**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init --check
```

If status is `exists`, ask user:

```yaml
AskUserQuestion:
  question: "Existing enrichment data found. How should we proceed?"
  header: "Enrichment"
  options:
    - label: "Keep enrichment"
      description: "Rediscover modules but preserve LLM-added descriptions"
    - label: "Reset enrichment"
      description: "Start fresh with empty enrichment"
  multiSelect: false
```

**Step 2: Run discovery**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**Step 3: Initialize enrichment (if reset or new)**

If user chose "Reset enrichment" or no enrichment existed:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init --force
```

**Step 4: LLM Architectural Analysis (automatic)**

Invoke the analysis skill to auto-populate enrichment with semantic descriptions:

```
Skill: plan-marshall:manage-architecture
```

The LLM reads discovered data, samples documentation and source code, then enriches with:
- Semantic module responsibilities
- Module purpose classification (infrastructure, domain-standards, tooling, etc.)
- Key packages per module with descriptions

**Step 5: Offer refinement (optional)**

After automatic analysis completes, offer user the option to refine:

```yaml
AskUserQuestion:
  question: "LLM analysis complete. Would you like to refine any descriptions?"
  header: "Refinement"
  options:
    - label: "Accept all"
      description: "Use LLM-generated descriptions as-is"
    - label: "Refine"
      description: "Review and adjust specific modules"
  multiSelect: false
```

If user chooses "Refine", use the "Edit Module" operation flow.

This regenerates `.plan/project-architecture/derived-data.json` from current build file definitions.

---

---

## Configuration: Credentials & Secrets

Manage credentials for external tool authentication (SonarCloud, etc.). System-authenticated providers (CI tools like `gh`/`glab` and `git`) are managed via Step 14 of the wizard and the Health Check menu. This section covers token/basic-auth providers only. All provider `skill_name` values use bundle-prefixed format (e.g., `plan-marshall:workflow-integration-sonar`).

### Credentials Submenu

```
AskUserQuestion:
  question: "What would you like to do with credentials?"
  options:
    - label: "Configure new"
      description: "Set up credentials for an external tool"
      value: "configure"
    - label: "Edit existing"
      description: "Update URL, token, or password for a configured tool"
      value: "edit"
    - label: "List"
      description: "Show configured credentials (no secrets)"
      value: "list"
    - label: "Verify"
      description: "Test connectivity for a configured tool"
      value: "verify"
    - label: "Remove"
      description: "Remove credentials for a tool"
      value: "remove"
```

### Routing

| Selection | Action |
|-----------|--------|
| configure | Two-phase workflow (see below) |
| edit | Two-phase workflow (see below) |
| list | `python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list` |
| verify | `python3 .plan/execute-script.py plan-marshall:manage-providers:credentials verify --skill {skill}` |
| remove | `python3 .plan/execute-script.py plan-marshall:manage-providers:credentials remove --skill {skill}` |

For `edit`, `verify`, and `remove`: if `--skill` is not known, first run `list` to show available skills, then ask the user which one to operate on.

### Configure Workflow

Non-secret values collected via `AskUserQuestion`. Secrets entered by user editing the credential file directly.

1. Discover providers:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list-providers
   ```
2. Ask scope via `AskUserQuestion`: "Global" (shared across projects) or "Project" (this project only). Default: global.
3. Collect URL, auth type via `AskUserQuestion` (use provider defaults as recommended)
4. If provider has `extra_fields` (check `list-providers` output): auto-detect from CI config, confirm with user
5. Run configure to create credential file with placeholder secrets (include `--scope` from step 2):
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials configure \
     --skill {skill} --url {url} --auth-type {auth_type} --scope {scope} \
     --extra organization={org} project_key={project_key}
   ```
6. If `needs_editing: true`: tell user to open `{path}` and replace placeholders with real secrets. Wait for confirmation, then check:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials check --skill {skill} --scope {scope}
   ```
7. Optionally verify:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials verify --skill {skill} --scope {scope}
   ```
8. Run ensure-denied:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials ensure-denied --target project
   ```
9. If the configured skill was `plan-marshall:workflow-integration-sonar`, check and add sonar-roundtrip:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan phase-6-finalize get
   ```
   If `default:sonar-roundtrip` not in steps:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan phase-6-finalize add-step --step default:sonar-roundtrip --after default:automated-review
   ```

### Edit Workflow

Non-secret field updates via CLI args. For secret changes, user edits the credential file directly.

1. Collect URL and auth type changes via `AskUserQuestion`
2. Run edit via executor with CLI args:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials edit \
     --skill {skill} --url {url} --auth-type {auth_type}
   ```
3. If `needs_editing: true`: tell user to edit `{path}` for secret changes, then run check:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials check --skill {skill}
   ```

---

## Configuration: Terminal Title

Configure the dynamic terminal-title + statusline integration so each terminal tab shows the active plan-marshall phase and live status (running / waiting / idle / done) for the Claude Code session running in it. See [Terminal title integration](../../plan-marshall/SKILL.md#terminal-title-integration) in the plan-marshall skill for the runtime contract.

Load and execute the dedicated reference:

```
Read references/menu-terminal-title.md
```

After completion, return to Main Menu.

---

After any configuration completes, return to Main Menu.

---

## Configuration: Recipes

Browse and inspect the recipes available in this project. Recipes are deterministic plan templates that bypass the iterative refine → outline → Q-Gate pipeline for well-understood transformations.

The full catalog and the contract for adding new recipes lives in [`references/menu-recipes.md`](menu-recipes.md). Load that reference and execute its workflow:

```
Read references/menu-recipes.md
```

For runtime enumeration of all recipes currently visible to the steward (built-in, project-local, and extension-provided), use:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-recipes
```

To inspect a single recipe's resolved declaration:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-recipe --recipe {recipe_key}
```

After completion, return to Main Menu.
