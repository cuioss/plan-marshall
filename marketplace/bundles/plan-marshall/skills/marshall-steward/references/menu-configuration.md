# Menu Option: Configuration

Sub-menu for skill domains and project structure configuration.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Table of Contents

- [Configuration Submenu](#configuration-submenu)
- [Routing](#routing)
- [Configuration: Plan Phase Settings](#configuration-plan-phase-settings)
- [Configuration: Review Gates](#configuration-review-gates)
- [Configuration: Quality Pipelines](#configuration-quality-pipelines)
- [Configuration: Skill Domains](#configuration-skill-domains)
- [Configuration: Project Structure](#configuration-project-structure)
- [Configuration: Terminal Title](#configuration-terminal-title)
- [Configuration: Enforcement Hook](#configuration-enforcement-hook)
- [Configuration: Derivation Resolvers](#configuration-derivation-resolvers)
- [Configuration: Display Timezone](#configuration-display-timezone)
- [Configuration: Merge Queue](#configuration-merge-queue)
- [Configuration: Commit Trailer](#configuration-commit-trailer)
- [Configuration: Recipes](#configuration-recipes)

---

## Configuration Submenu

The Configuration submenu has 14 options, which exceeds the `AskUserQuestion` 4-option cap. It is presented as a multi-page paginated menu following the "More actions..." pattern documented in `plan-marshall/workflow/planning.md` (§ Action: list): options are chunked into pages of ≤4, every non-final page reserves its 4th slot for a "More..." continuation that triggers the next page's `AskUserQuestion`, and the final page exposes a "Back" element returning to the Main Menu without quitting.

**Page 1** — first 3 options plus the "More..." continuation:

```text
AskUserQuestion:
  question: "This project's settings are already in place, so nothing here has to change. Which of them do you want to look at?"
  header: "Configure"
  options:
    - label: "Skill Domains"
      description: "Choose which coding standards this project's work is written and reviewed against"
      value: "skill-domains"
    - label: "Plan Phase Settings"
      description: "Change how a plan branches, how far it may break existing behaviour, and when it commits"
      value: "plan-phases"
    - label: "Project Structure"
      description: "See what was found in this project, re-detect it, or add your own notes to a module"
      value: "structure"
    - label: "More..."
      description: "Shows the next three entries: Quality Pipelines, Review Gates, and Credentials"
      value: "more-1"
```

**Page 2** — shown only when the user selects "More..." on Page 1 — the next 3 options plus the "More..." continuation:

```text
AskUserQuestion:
  question: "These are the next three settings groups. Which one do you want to look at?"
  header: "More config"
  options:
    - label: "Quality Pipelines"
      description: "Choose which checks run while work is being done and which run before it ships"
      value: "quality-pipelines"
    - label: "Review Gates"
      description: "Decide where a plan pauses for your approval and where it carries straight on"
      value: "review-gates"
    - label: "Credentials & Secrets"
      description: "Store the logins plan-marshall needs to reach outside services on your behalf"
      value: "credentials"
    - label: "More..."
      description: "Shows the next three entries: Terminal Title, Enforcement Hook, and Recipes"
      value: "more-2"
```

**Page 3** — shown only when the user selects "More..." on Page 2 — the next 3 options plus the "More..." continuation:

```text
AskUserQuestion:
  question: "Terminal Title and Enforcement Hook only take effect in Claude Code sessions; Recipes work wherever plan-marshall runs. Which one do you want to look at?"
  header: "More config"
  options:
    - label: "Terminal Title"
      description: "Makes each terminal tab show which plan is running in it and whether it is busy, waiting, or done"
      value: "terminal-title"
    - label: "Enforcement Hook"
      description: "Blocks a handful of known-bad commands while a plan is running, and stays out of the way otherwise"
      value: "enforcement-hook"
    - label: "Recipes"
      description: "Browse the ready-made plan templates for common jobs, so a routine change skips the questions"
      value: "recipes"
    - label: "More..."
      description: "Shows the next three entries: Derivation Resolvers, Display Timezone, and Merge Queue"
      value: "more-3"
```

> **Target-conditional rows.** The "Terminal Title" and "Enforcement Hook"
> options install wiring into the resolved **Claude** settings file and are
> meaningless on any other harness. They are present on the Claude target only;
> on a non-Claude target they are omitted from this page (its remaining options
> — Recipes and "More..." — continue to Page 4 unchanged). The flows they route
> to live in the Claude-only `marshall-steward-claude-wizards` skill.

**Page 4** — shown only when the user selects "More..." on Page 3 — the next 3 options plus the "More..." continuation:

```text
AskUserQuestion:
  question: "These three are remembered on this machine only, so a fresh clone falls back to the defaults. Which one do you want to look at?"
  header: "More config"
  options:
    - label: "Derivation Resolvers"
      description: "Choose which tools are used to work out how this project's parts depend on each other"
      value: "derivation-resolvers"
    - label: "Display Timezone"
      description: "Choose the timezone times are shown in; what is recorded never changes, only what you read"
      value: "display-timezone"
    - label: "Merge Queue"
      description: "Check whether your host can queue merges and turn it on, so branches land one at a time"
      value: "merge-queue"
    - label: "More..."
      description: "Shows the last entries: Commit Trailer, Full Reconfigure, and Back"
      value: "more-4"
```

**Page 5** — shown only when the user selects "More..." on Page 4 — the final options plus the "Back" element:

```text
AskUserQuestion:
  question: "These are the last entries. Pick one, or go back if none of them is what you were after."
  header: "More config"
  options:
    - label: "Commit Trailer"
      description: "Choose the co-author name and address that assistant-written commits are recorded under"
      value: "commit-trailer"
    - label: "Full Reconfigure"
      description: "Walks the whole setup again so you can revisit every answer; the one-time install work is not repeated"
      value: "wizard"
    - label: "Back"
      description: "Leaves everything as it is and returns you to the main menu"
      value: "back"
```

## Routing

| Selection | Action |
|-----------|--------|
| skill-domains | Execute "Configuration: Skill Domains" below |
| plan-phases | Execute "Configuration: Plan Phase Settings" below |
| structure | Execute "Configuration: Project Structure" below |
| more-1 | Present Configuration Page 2 `AskUserQuestion` |
| quality-pipelines | Execute "Configuration: Quality Pipelines" below |
| review-gates | Execute "Configuration: Review Gates" below |
| credentials | Execute "Configuration: Credentials & Secrets" below |
| more-2 | Present Configuration Page 3 `AskUserQuestion` |
| terminal-title | Claude only: load `Read ../marshall-steward-claude-wizards/references/menu-terminal-title.md` → Execute |
| enforcement-hook | Claude only: load `Read ../marshall-steward-claude-wizards/references/menu-enforcement-hook.md` → Execute |
| recipes | Load `Read references/menu-recipes.md` → Execute "Configuration: Recipes" below |
| more-3 | Present Configuration Page 4 `AskUserQuestion` |
| derivation-resolvers | Load `Read references/menu-derivation-resolvers.md` → Execute |
| display-timezone | Load `Read references/menu-display-timezone.md` → Execute |
| merge-queue | Load `Read references/merge-queue-setup.md` → Execute the provisioning flow |
| more-4 | Present Configuration Page 5 `AskUserQuestion` |
| commit-trailer | Load `Read references/menu-commit-trailer.md` → Execute |
| wizard | Load `Read references/wizard-flow.md` — skip to Step 5 (bootstrap already done) |
| back | Do nothing → Return to the Main Menu |

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

**Commit and push** (phase-5-execute): `true` (recommended — commit per-deliverable + push at finalize) or `false` (local-only run)
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field commit_and_push --value {true|false}
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
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get
```

Display current gate values, then ask user which transitions should auto-continue (multi-select):
- "Plan without asking" → outline to planning
- "Execute without asking" → planning to execution
- "Auto-continue plan lifecycle (both directions)" → the symmetric `finalize_without_asking` + `loop_back_without_asking` pair. Forward: execution to finalize. Reverse: a finalize `loop_back`, which re-enters execute inline on a `5-execute` target and replays the loop-back-marked finalize step in place on a `6-finalize` one (both bounded by `phase-6-finalize.max_iterations`). Both default to `true` — a finalize-side fix is corrective work inside a plan the user already approved, so both directions auto-continue and `max_iterations` is what terminates the cycle. The "apply defaults" branch persists the pair in a single pass; setting either to `false` to be asked at that boundary is an explicit user choice.

Apply each selection via manage-config:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init set --field init_without_asking --value {true|false}
```
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
  plan phase-6-finalize set --field finalize_without_asking --value {true|false}
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set --field loop_back_without_asking --value {true|false}
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

**Verification steps** (phase-5-execute): Discover available steps, present as multi-select, then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
```
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps {comma_separated_selected_steps}
```
Assert the `set-steps` response is `status: success`. A `missing_order` or `order_collision` error means a selected step's authoritative source (frontmatter on built-in standards docs / `SKILL.md` for `project:` steps) is missing or duplicates an `order` value — fix the source and re-run.

After `set-steps` completes for phase-5-execute, validate that every `project:` step in the new selection has a matching `Skill()` allow rule:
```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-missing-project-step-permissions \
  --marshal .plan/marshal.json \
  --scope project
```

If `missing` is non-empty, ask user:
```text
AskUserQuestion:
  question: "{N} of the checks you just selected are not yet allowed to run without asking, so execute would stop and prompt you for each one. Grant them now?"
  header: "Permissions"
  options:
    - label: "Yes (recommended)"
      description: "Adds the missing permissions to this project's settings, so execute runs these checks without interrupting you"
    - label: "No"
      description: "Leaves the settings alone; you will be asked to approve each of these checks every time execute reaches it"
  multiSelect: false
```

If yes, apply fixes:
```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-project-step-permissions \
  --marshal .plan/marshal.json \
  --settings .claude/settings.json
```

**Finalize steps** (phase-6-finalize): preset-first, with a Custom escape hatch. Present the finalize-step preset picker BEFORE the per-step `list-finalize-steps` / `set-steps` multi-select, mirroring the single-AskUserQuestion preset-picker pattern documented in [effort-menu.md](../standards/effort-menu.md) (do not inline-copy that flow — the normative contract lives there). The three preset descriptions are sourced verbatim from `FinalizeStepPresets.describe(name)` (`finalize_step_presets.py`), and the Custom option falls through to the existing per-step multi-select.

Optionally detect the current preset first — deep-equality of `plan.phase-6-finalize.steps` against `FinalizeStepPresets.get(name)` for each name in `FinalizeStepPresets.all_names()` — and surface it as `Current: {name} preset` / `Current: custom (manually edited)`. This comparison is performed here, in the wizard: unlike the effort menu's Step 1, which delegates to the deterministic `manage-config effort identify` recogniser, `finalize-steps` exposes no equivalent verb, so there is nothing to hand the deep-equality walk to.

```text
AskUserQuestion:
  question: "Finished work goes through a fixed sequence of shipping steps — committing, pushing, opening a pull request, reviewing, merging. Three ready-made sequences cover the usual cases. Which one fits this project?"
  header: "Shipping"
  options:
    - label: "Apply standard preset (recommended)"
      description: <FinalizeStepPresets.describe("standard")>
    - label: "Apply local preset"
      description: <FinalizeStepPresets.describe("local")>
    - label: "Apply full preset"
      description: <FinalizeStepPresets.describe("full")>
    - label: "Custom"
      description: "None of the three fits — you pick the individual steps yourself on the next screen"
  multiSelect: false
```

On a preset choice (`local`, `standard`, or `full`), apply it and skip the per-step multi-select:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  finalize-steps apply-preset --preset {name}
```

On `Custom`, fall through to the per-step multi-select escape hatch — discover available steps, present as multi-select, then apply:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
```

The `list-finalize-steps` output includes three sources: built-in (`default:*`), project-local (`project:*`), and **bundle-optional** (`{bundle}:{skill}` step docs declaring `implements: plan-marshall:extension-api/standards/ext-point-finalize-step` with `default_on: false`, surfaced via `extension_discovery.find_implementors`). Bundle-optional entries — such as `plan-marshall:plan-retrospective` — are intentionally absent from the default `plan.phase-6-finalize.steps` list, so operators must opt in explicitly: either by applying a preset whose `presets:` membership includes the step, or by selecting it in this custom multi-select. Example multi-select presentation (built-ins plus the opt-in retrospective):

```text
AskUserQuestion:
  question: "You chose to pick the shipping steps yourself. Every step you tick becomes eligible each time a plan finishes — a narrowly-scoped plan or a lighter execution profile can still leave one out — and every step you do not tick never runs at all. Which should this project use?"
  header: "Shipping"
  multiSelect: true
  options:
    - label: "default:push (recommended)"
      description: "Sends the finished branch to your git host, so the work exists somewhere other than this machine"
    - label: "default:create-pr"
      description: "Opens a pull request for the branch, so the change can be reviewed and merged the usual way"
    - label: "plan-marshall:automatic-review"
      description: "Waits for your build and review bots to finish on the pull request, then works through what they reported"
    - label: "default:lessons-capture (recommended)"
      description: "Writes down what went wrong or surprised it, so a later plan does not repeat the same mistake"
    - label: "plan-marshall:plan-retrospective (Opt-in)"
      description: "Produces a written review of how the plan itself ran — useful when tuning, noise otherwise"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-steps --steps {comma_separated_selected_steps}
```
Assert the `set-steps` response is `status: success`. A `missing_order` or `order_collision` error means a selected step's authoritative source (frontmatter on built-in standards docs / `SKILL.md` for `project:` and bundle-optional steps) is missing or duplicates an `order` value — fix the source and re-run.

After `set-steps` completes for phase-6-finalize, repeat the same project-step validation and auto-fix flow described above for phase-5-execute — the same `detect-missing-project-step-permissions` and `apply-project-step-permissions` calls cover both phases.

**PR merge strategy**: Ask user for the merge strategy used when merging PRs during branch cleanup (default: squash):

```text
AskUserQuestion:
  questions:
    - question: "When a plan's pull request is merged, its commits can land on the main branch in three different shapes. Which does this project use?"
      header: "PR Merge"
      options:
        - label: "squash (recommended)"
          description: "The whole branch lands as a single commit; the individual commit messages are discarded"
        - label: "merge"
          description: "Every commit lands as written, plus a merge commit recording where the branch joined"
        - label: "rebase"
          description: "Every commit lands as written, one after another, with no merge commit"
      multiSelect: false
```

`pr_merge_strategy` is a step-owned param of the `default:branch-cleanup` step in the keyed-map `steps` structure. The wizard writes it to the marshal.json keyed map (the global-config default) via the one-stop `step set` verb:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize step set --step-id default:branch-cleanup --param pr_merge_strategy --value {squash|merge|rebase}
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

**Adversarial infra elements (lane:ask) — MANDATORY.** Two adversarial finalize
elements seed with a `lane: ask` override — `plan-marshall:automatic-review`
(PR-review bots) and `default:sonar-roundtrip` (the Sonar new-code roundtrip).
This update-config pass ALWAYS surfaces them so their inclusion is resolved to a
concrete answer; an UNRESOLVED `ask` whose provider is absent is dropped at
compose by the drop-when-no-provider safety net, but a resolved answer persisted
here is never dropped. Enumerate the ask-tier elements (read them from the verb —
do NOT hard-code the ids):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  finalize-steps list-ask-lane
```

For **EACH** id in the returned `ask_steps`, prompt the operator and persist the
answer — one `AskUserQuestion` and one `set-lane` write per element:

```text
AskUserQuestion:
  question: "Nothing in this project's setup says whether it has {automated pull-request reviewers | a Sonar code-quality service}, and guessing wrong either wastes a wait or skips a real check. Does it?"
  header: "Reviewers"
  options:
    - label: "Yes"
      description: "Plans wait for it and act on what it reports, except on the quickest runs"
    - label: "Yes, always"
      description: "Plans wait for it and act on what it reports on every run, however small"
    - label: "No"
      description: "Plans never wait for it; nothing here is checked against it"
  multiSelect: false
```

Persist the answer (`No` → `off`; `Yes` → `standard`; `Yes, always` → `full`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  finalize-steps set-lane --step-id {element_id} --lane {off|standard|full}
```

When `ask_steps` is empty (every ask element was already resolved on a prior
run), skip the prompts — there is nothing left to resolve.

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
  question: "Scanning this project turned up the languages marked (detected) below, but only you know which ones the work here should actually be held to. Which standards should apply?"
  header: "Standards"
  multiSelect: true
  options:
    # Pre-select domains from extensions_used
    # Show all available domains, mark applicable ones
    - label: "Java Development (detected)"
      description: "Java work is written and reviewed against the Java conventions: naming, null-safety, dependency injection, and JUnit tests"
    - label: "Documentation (detected)"
      description: "Documentation is written and reviewed against the AsciiDoc conventions, including how decisions are recorded"
    - label: "JavaScript Development"
      description: "JavaScript work is written and reviewed against the modern JS conventions, with ESLint and Jest expectations"
    - label: "Plugin Development"
      description: "Work on plan-marshall's own components is held to the conventions those components must follow"
```

**Step 4: Configure selected domains**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains configure --domains "java,documentation"
```

This configures:
- `system` domain (always) with task_executors
- Each selected domain with bundle reference and workflow_skill_extensions
- Seeds the built-in verify steps into `plan.phase-5-execute.verification_steps`

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

The Project Structure operation list has 5 options, which exceeds the `AskUserQuestion` 4-option cap. It is presented as a paginated menu following the "More..." pattern documented in `plan-marshall/workflow/planning.md` (§ Action: list): the first page presents 3 operations plus a "More..." continuation, and the second page presents the remaining operations.

**Page 1** — first 3 operations plus the "More..." continuation:

```yaml
AskUserQuestion:
  question: "plan-marshall keeps a picture of how this project is laid out and uses it to decide where new code belongs. What do you want to do with it?"
  header: "Structure"
  options:
    - label: "View"
      description: "Shows the parts of the project it found and what it believes each one is for"
    - label: "Edit Module"
      description: "Correct or add to what it believes about one part — what it is for, and anything worth knowing when working in it"
    - label: "Manage Placement"
      description: "Change the rules that decide where a new file of a given kind is put"
    - label: "More..."
      description: "Shows the remaining two entries: Regenerate and Re-seed Build Map"
  multiSelect: false
```

**Page 2** — shown only when the user selects "More..." on Page 1:

```yaml
AskUserQuestion:
  question: "These are the two remaining entries, both of which re-read the project instead of editing it by hand. What do you want to do?"
  header: "Structure"
  options:
    - label: "Regenerate"
      description: "Reads the project again from its build files and rebuilds the picture of how it is laid out"
    - label: "Re-seed Build Map"
      description: "Refreshes which files belong to which build after a new language or toolchain was added"
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
  question: "This project already carries written descriptions of what each part is for — some added automatically, some possibly by you. Re-reading the project can either keep them or clear them. Which should it do?"
  header: "Notes"
  options:
    - label: "Keep enrichment (recommended)"
      description: "The layout is re-read, but every existing description is left exactly as it is"
    - label: "Reset enrichment"
      description: "Every existing description is discarded and written again from scratch; anything you wrote by hand is lost"
  multiSelect: false
```

**Step 2: Run discovery**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**Step 3: Initialize enrichment (if reset or new)**

If user chose "Reset enrichment" or no enrichment existed:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture init --force --reset
```

`--reset` is required here because "Reset enrichment" is the intentional blank-all path: it discards existing curated enrichment and re-seeds every module's `enriched.json` as the empty stub. Plain `init --force` (without `--reset`) preserves existing enrichment and would not honor the user's reset choice.

**Step 4: LLM Architectural Analysis (automatic)**

Invoke the analysis skill to auto-populate enrichment with semantic descriptions:

```text
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
  question: "Each part of the project now has a written description of what it is for, produced by reading the code and docs. Those descriptions are shown above. Do any of them need correcting?"
  header: "Descriptions"
  options:
    - label: "Accept all (recommended)"
      description: "Keeps the descriptions as written and finishes; you can correct any of them later from this same menu"
    - label: "Refine"
      description: "Takes you through the parts one at a time so you can reword the ones that got it wrong"
  multiSelect: false
```

If user chooses "Refine", use the "Edit Module" operation flow.

This regenerates the per-module architecture layout under `.plan/project-architecture/` from current build file definitions: a refreshed `_project.json` (the source of truth for the module index) plus an `enriched.json` stub per indexed module. Per-module `enriched.json` files are preserved when "Keep enrichment" was selected and reset only when "Reset enrichment" was selected. Derived module data is not persisted — it is computed on demand by `crawl_module_derived`.

### Operation: Re-seed Build Map

Re-seed `build.map` after a domain extension is added or updated. The seed is write-once — an existing block is preserved — so re-seeding picks up newly-registered domains without clobbering operator corrections.

See [build-map-setup.md](build-map-setup.md) § "Menu Mode: Re-Seed After an Extension Change" for the seed/read commands and the `action` (`seeded` / `preserved`) interpretation.

---

---

## Configuration: Credentials & Secrets

Manage credentials for external tool authentication (SonarCloud, etc.). System-authenticated providers (CI tools like `gh`/`glab` and `git`) are managed via Step 13 of the wizard and the Health Check menu. This section covers token/basic-auth providers only. All provider `skill_name` values use bundle-prefixed format (e.g., `plan-marshall:workflow-integration-sonar`).

### Credentials Submenu

```text
AskUserQuestion:
  question: "Some steps reach outside services on your behalf and need a login to do it. What do you want to do with those logins?"
  header: "Logins"
  options:
    - label: "Configure new"
      description: "Sets up a login for a service that has none yet; you paste the secret into a file it creates"
      value: "configure"
    - label: "Edit existing"
      description: "Changes the address or sign-in method already stored for a service"
      value: "edit"
    - label: "List"
      description: "Shows which services have a login stored; the secrets themselves are never printed"
      value: "list"
    - label: "Verify"
      description: "Tries the stored login against the service and reports whether it still works"
      value: "verify"
    - label: "Remove"
      description: "Deletes the stored login for a service; steps that need it will stop working"
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
     plan phase-6-finalize add-step --step default:sonar-roundtrip
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

> **Claude only.** This section routes to the Claude-only wizard skill
> `marshall-steward-claude-wizards`. On a non-Claude target the option is absent
> from the Configuration page and this branch is never reached.

Configure the dynamic terminal-title integration so each terminal tab shows the active plan-marshall phase and live status (running / waiting / done / complete, plus the lock/build glyph) for the Claude Code session running in it. The title is a three-way split: `manage-status` persists the state into `status.json` (the single source of persisted title state), the pure `plan-marshall:manage-terminal-title` composer renders `{icon} {glyph} {body}`, and `plan-marshall:platform-runtime` (`session render-title`) reads `status.json` and emits per target. See [Terminal title integration](../../plan-marshall/SKILL.md#terminal-title-integration) in the plan-marshall skill for the runtime contract and `manage-terminal-title/standards/terminal-title-architecture.md` for the full architecture.

Load and execute the dedicated reference:

```text
Read ../marshall-steward-claude-wizards/references/menu-terminal-title.md
```

After completion, return to Main Menu.

---

## Configuration: Enforcement Hook

> **Claude only.** This section routes to the Claude-only wizard skill
> `marshall-steward-claude-wizards`. On a non-Claude target the option is absent
> from the Configuration page and this branch is never reached.

Configure the conditional PreToolUse enforcement hook. When enabled, the hook deterministically blocks four mechanically-checkable hard-rule violation families (shell-construct compounds, Bash file-ops, generated-executor edits, hard-coded build commands) — but ONLY when the call originates inside a plan-marshall plan context, failing open everywhere else. The opt-in is orthogonal to the terminal-title wiring: enabling one does not enable the other. See [`../../platform-runtime/standards/pretooluse-enforcement.md`](../../platform-runtime/standards/pretooluse-enforcement.md) for the canonical contract.

Load and execute the dedicated reference:

```text
Read ../marshall-steward-claude-wizards/references/menu-enforcement-hook.md
```

After completion, return to Main Menu.

---

## Configuration: Derivation Resolvers

Inspect and change which module-edge **derivation resolvers** run in this checkout — the resolvers whose `(from, to)` pairs become the edge set behind the `graph` / `path` / `neighbors` / `impact` queries. The binding is machine-local (a resolver's availability and cost depend on locally-installed tooling) and persists to the `derivation_resolvers` section of the git-ignored run-configuration store, beside `language_servers`. ⛔ An unconfigured project runs **every** discovered resolver: this menu switches a resolver off, it does not switch derivation on. See [`../../manage-run-config/standards/run-config-standard.md`](../../manage-run-config/standards/run-config-standard.md) § "Derivation-Resolvers Section".

Load and execute the dedicated reference:

```text
Read references/menu-derivation-resolvers.md
```

After completion, return to Main Menu.

---

## Configuration: Display Timezone

Inspect and change the IANA timezone plan-marshall renders operator-facing timestamps in. The binding is machine-local — it persists to the git-ignored run-configuration store beside the other machine-local bindings — and it changes only how an already-recorded instant is DISPLAYED; nothing is re-stamped and no artifact is rewritten. An unconfigured project renders in `UTC`.

Load and execute the dedicated reference:

```text
Read references/menu-display-timezone.md
```

After completion, return to Main Menu.

---

## Configuration: Merge Queue

Probe and (optionally) enable the platform merge queue — GitHub merge queue or
GitLab merge train — via the provider-agnostic `ci repo merge-queue` verbs, then
persist the `use_merge_queue` opt-in. The step is idempotent and non-clobbering:
an already-configured project surfaces nothing and mutates nothing.

Load and execute the dedicated reference:

```text
Read references/merge-queue-setup.md
```

After completion, return to Main Menu.

---

## Configuration: Commit Trailer

Inspect and change the co-author identity every assistant-authored commit is recorded under. The identity names the SYSTEM that produced the commit, not the assistant or the vendor behind it, and it does not vary by target. The binding is machine-local — it persists to the git-ignored run-configuration store beside the other machine-local bindings — so a fresh clone and every cloud session resolve to the `plan-marshall` default. Changing it governs the next commit onwards; history is untouched.

Load and execute the dedicated reference:

```text
Read references/menu-commit-trailer.md
```

After completion, return to Main Menu.

---

After any configuration completes, return to Main Menu.

---

## Configuration: Recipes

Browse and inspect the recipes available in this project. Recipes are deterministic plan templates that bypass the iterative refine → outline → Q-Gate pipeline for well-understood transformations.

The full catalog and the contract for adding new recipes lives in [`references/menu-recipes.md`](menu-recipes.md). Load that reference and execute its workflow:

```text
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
