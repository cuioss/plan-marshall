# First-Run Wizard Flow

Sequential structured setup for new projects. Execute steps in order.

The wizard splits into two sections: **Bootstrap** (Steps 1-4) runs before the executor exists and uses direct Python calls; **Configuration** (Steps 5 onwards) runs against the generated executor. The maintenance menu's "Full Reconfigure" re-enters this flow at Step 5 (Initialize marshal.json).

**Bootstrap error recovery** (Steps 1-4): If any bootstrap step fails, report the error and abort the wizard. The user must resolve the issue (e.g., file permissions, missing Python) before re-running `/marshall-steward --wizard`.

---

# Bootstrap (Steps 1-4)

## Step 1: Gitignore Setup (BOOTSTRAP)

Configure `.gitignore` for `.plan/` directory with tracked file exceptions.

**BOOTSTRAP**: Use a DIRECT Python call (no executor yet). Resolve the script path deterministically via `bootstrap_plugin resolve` (`${BOOTSTRAP}` was located in SKILL.md Prerequisites) and read `resolved_path` from the TOON as `{GITIGNORE_SETUP}`:

```bash
python3 "${BOOTSTRAP}" resolve --bundle plan-marshall --path skills/marshall-steward/scripts/gitignore_setup.py
```

Then invoke the resolved script directly:

```bash
python3 "{GITIGNORE_SETUP}"
```

**Output (TOON)**:
```toon
status	created
gitignore_path	/path/to/.gitignore
entries_added	4
```

The generated block looks like:

```
# Planning system (managed by /marshall-steward)
# Runtime state (plans, run-configuration, lessons-learned, memory, logs — managed by plan-marshall)
.plan/*
!.plan/marshal.json
!.plan/project-architecture/
.plan/local/worktrees/
```

The `.plan/*` rule already covers `.plan/local/` (where runtime state
lives); the documentation comment above it explains the layout for
human readers.

**Tracked Files**:
- `.plan/marshal.json` - Project configuration
- `.plan/project-architecture/` - Project architecture data

| status | Meaning |
|--------|---------|
| `created` | New .gitignore created with planning entries |
| `updated` | Existing .gitignore updated with planning entries |
| `unchanged` | Planning entries already present |

**NOTE**: `execute-script.py` is NOT tracked because it contains local absolute paths and must be regenerated per-machine.

---

## Step 2: Update Project Documentation (BOOTSTRAP)

**BOOTSTRAP**: Use a DIRECT Python call (executor not yet available). Resolve the script path deterministically via `bootstrap_plugin resolve` (`${BOOTSTRAP}` was located in SKILL.md Prerequisites) and read `resolved_path` from the TOON as `{DETERMINE_MODE}`:

```bash
python3 "${BOOTSTRAP}" resolve --bundle plan-marshall --path skills/marshall-steward/scripts/determine_mode.py
```

Then invoke the resolved script directly:

```bash
python3 "{DETERMINE_MODE}" fix-docs
```

Interpret the output:
- `fix_status: ok` → No action needed, continue.
- `fix_status: fixed` → Content was appended deterministically. The `fixes` field lists what was fixed (e.g., `plan_temp:CLAUDE.md,file_ops:CLAUDE.md`).

---

## Step 3: Ensure Executor Permission (BOOTSTRAP)

Add the executor permission to project-local settings so script execution doesn't prompt — but **consult the current permission state first**. This step is a consult-before-add gate: the steward MUST read the existing project permission state before widening the executor allow-list, and MUST NOT widen it without a prior consult. The widening is deterministic — driven by the consult result, not by an unconditional `ensure` write.

**BOOTSTRAP**: Use a DIRECT Python call (no executor yet). Resolve the script path deterministically via `bootstrap_plugin resolve` (`${BOOTSTRAP}` was located in SKILL.md Prerequisites) and read `resolved_path` from the TOON as `{PERMISSION_FIX}`:

```bash
python3 "${BOOTSTRAP}" resolve --bundle plan-marshall --path skills/tools-permission-fix/scripts/permission_fix.py
```

**Consult (mandatory, read-only) — read the current permission state before any widening.** Run `ensure-executor` in `--dry-run` mode against the project target. The dry run previews whether the executor permission is already present without modifying any settings file, so it is the read-only consult of the current allow-list state:

```bash
python3 "{PERMISSION_FIX}" ensure-executor --target project --dry-run
```

Interpret the consult result before deciding whether to widen:

| dry-run result | Meaning | Action |
|----------------|---------|--------|
| permission already present | The executor allow-list already covers `Bash(python3 .plan/execute-script.py *)` | No widening needed — record the consult and skip the write below. |
| permission absent | The executor permission is missing from project settings | Proceed to the widening write below — the consult has cleared the gate. |

**Widen only when the consult shows the permission is absent.** Do NOT issue the write unconditionally — the consult above is the gate that authorizes it. When the consult shows the permission is absent, invoke the resolved script to add it:

```bash
python3 "{PERMISSION_FIX}" ensure \
  --permissions "Bash(python3 .plan/execute-script.py *)" \
  --target project
```

**Output (TOON)**:
```toon
status	added
permission	Bash(python3 .plan/execute-script.py *)
target	project
settings_file	/path/to/.claude/settings.local.json
```

| status | Meaning |
|--------|---------|
| `added` | Permission added to project settings |
| `exists` | Permission already present |

This ensures script execution works without prompting, independent of global settings.

---

## Step 4: Generate Executor (BOOTSTRAP)

**BOOTSTRAP**: Use DIRECT Python call with glob (executor doesn't exist yet):

**Worktree detection**: Before invoking generate_executor, detect whether the wizard is running inside a git worktree (as opposed to the main checkout). Two signals:

1. The repo top-level path resolves to something under `.plan/local/worktrees/`:
   ```bash
   git -C . rev-parse --show-toplevel
   ```
   Capture this value as `REPO_ROOT`. If `REPO_ROOT` contains the `/.plan/local/worktrees/` segment, the wizard is running inside a worktree.

2. As a secondary check, `git -C . rev-parse --is-inside-work-tree` returns `true` when inside any working tree (not specific to worktrees, but combined with the path check above it confirms a valid git context).

When the wizard is running inside a worktree, pass the worktree absolute path to `generate_executor.py` via `--marketplace-root <REPO_ROOT>` so the generated executor's script mappings resolve against the worktree's `marketplace/bundles/` rather than the main checkout (or the plugin cache). When running against the main checkout, omit the flag and let the script auto-detect the plugin cache.

**Inside a worktree** (path under `.plan/local/worktrees/`): resolve the script path deterministically via `bootstrap_plugin resolve` (`${BOOTSTRAP}` was located in SKILL.md Prerequisites) and read `resolved_path` from the TOON as `{GENERATE_EXECUTOR}`:

```bash
python3 "${BOOTSTRAP}" resolve --bundle plan-marshall --path skills/tools-script-executor/scripts/generate_executor.py
```

**Refuse-or-scaffold guard (worktree only)**: a worktree executor-gen MUST NOT run until the worktree owns its own `.plan/local` directory. Without it, `generate_executor` climbs to the *main* checkout's `.plan/local` (the nearest ancestor that has one) and overwrites main's `.plan/execute-script.py`. Before invoking `generate_executor` from a worktree, run the guard:

```bash
python3 "{DETERMINE_MODE}" check-worktree-plan-local --repo-root "{REPO_ROOT}" --scaffold
```

(`{DETERMINE_MODE}` is the steward `determine_mode.py` resolved via `python3 "${BOOTSTRAP}" resolve --bundle plan-marshall --path skills/marshall-steward/scripts/determine_mode.py`, reading `resolved_path` from the TOON.) The guard returns:

| status | Meaning | Action |
|--------|---------|--------|
| `ok` | The worktree already owns `.plan/local` (or `REPO_ROOT` is the main checkout) | Proceed to generate the executor. |
| `scaffolded` | The worktree lacked `.plan/local`; the guard created it | Proceed to generate the executor. |
| `refuse` | The worktree lacks `.plan/local` and `--scaffold` was omitted | ABORT — do NOT generate; surface `detail` to the operator. |

With `--scaffold` (as shown), the guard creates the missing `<REPO_ROOT>/.plan/local` rather than refusing, so the wizard can proceed cleanly. The manual workaround when running the guard without `--scaffold` and it returns `refuse` is `mkdir -p <REPO_ROOT>/.plan/local`. Then invoke generate_executor directly with the worktree root captured above as `{REPO_ROOT}`:

```bash
python3 "{GENERATE_EXECUTOR}" generate --marketplace-root "{REPO_ROOT}"
```

**Outside a worktree** (main checkout, default path): resolve `{GENERATE_EXECUTOR}` the same way (via `python3 "${BOOTSTRAP}" resolve --bundle plan-marshall --path skills/tools-script-executor/scripts/generate_executor.py`, reading `resolved_path` from the TOON), then invoke it without the marketplace-root flag:

```bash
python3 "{GENERATE_EXECUTOR}" generate
```

**Output (TOON)**:
```toon
status	scripts_discovered	executor_generated	logs_cleaned
success	109	.plan/execute-script.py	0
```

The script auto-detects the plugin cache location and generates `.plan/execute-script.py` with all script mappings embedded. When `--marketplace-root` is supplied, mappings are anchored to the supplied path instead of the auto-detected cache.

**Verify syntax**:
```bash
python3 -m py_compile .plan/execute-script.py && echo "Executor syntax OK"
```

**Output**: "Executor ready with N script mappings"

**NOTE**: From this point on, all script calls use: `python3 .plan/execute-script.py {notation} ...`

---

# Configuration (Steps 5 onwards)

## STEWARD audit trail (applies to every Configuration step)

From Step 4 (executor present) onward, the wizard emits a **STEWARD audit entry** for every decision it makes — one entry per `AskUserQuestion` answer the operator gives AND one per auto-decision the wizard takes without prompting (auto-selected provider, detected default, skipped step). The entries use `manage-logging`'s first-class global/no-plan path (the wizard runs before any plan exists, so `--plan-id` is omitted) under the stable `[STEWARD] (plan-marshall:marshall-steward)` prefix — see `manage-logging` SKILL.md § "Global / no-plan logging path" and § "STEWARD audit namespace".

**One entry per answer / auto-decision — coalescing is forbidden.** Every individual operator answer and every individual auto-decision MUST produce its own separate audit entry. The wizard MUST NOT coalesce multiple answers or auto-decisions into a single combined entry, MUST NOT summarize a group of decisions (e.g. all of Step 11's per-step toggles) under one rolled-up line, and MUST NOT defer emission to a batch flush at the end of a step or at wizard completion. A multi-question `AskUserQuestion` call yields one entry per answered question; a multi-select answer that resolves N toggles yields N entries (one per toggle decided); a step that prompts once and then auto-decides twice yields three entries. The audit trail must be reconstructable down to each discrete decision, so the entry-to-decision mapping is strictly one-to-one — never one-to-many.

- **Operator answers** to an `AskUserQuestion` and **auto-decisions** are decision-class — log them with the `decision` subcommand (the file is the category, so no `[DECISION]` prefix; the `[STEWARD]` bracket names the namespace):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --level INFO \
    --message "[STEWARD] (plan-marshall:marshall-steward) {what was decided and why}"
  ```

- **Status/progress** notes (a step ran, a check passed) are work-class — log them with the `work` subcommand and a `[STEWARD]` category bracket:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --level INFO \
    --message "[STEWARD] (plan-marshall:marshall-steward) {what happened}"
  ```

This audit trail makes a plan-less steward run reconstructable from `.plan/logs/decision-{date}.log` and `.plan/logs/work-{date}.log`. Each Configuration step below that prompts or auto-decides emits at least one such entry; do NOT pass a fabricated plan id to force a global fallback — the omitted-`--plan-id` path is the supported global path.

## Step 5: Initialize Marshal.json

Initialize marshal.json early to establish the `skill_domains` structure needed by later steps.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config init
```

**If marshal.json already exists**:
- The command will fail with "marshal.json already exists"
- Check if existing config has required structure: `skill-domains list`
- If that fails with "skill_domains not configured", use `--force` to recreate:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config init --force
```

**Output**: "Created .plan/marshal.json with defaults"

**Note**: marshal.json contains configuration only. The module list comes from `_project.json["modules"]` (Step 8), which is the source of truth — per-module derived data is computed lazily off that index on demand by `crawl_module_derived`.

**Effort defaults are seeded at init**: `get_default_config()` seeds per-phase `effort` keys (`plan.<phase>.effort`) plus the plan-wide `plan.effort` fallback, mirroring the `balanced` named preset's expanded shape. A freshly-initialized project therefore gets per-phase model tuning out of the box — `effort resolve-target` resolves a concrete `execution-context-{level}` rather than silently falling back to `level: inherit`. The post-wizard **Effort menu** (see [effort-menu.md](../standards/effort-menu.md)) still tunes these after init via `apply-preset` or per-phase edits; init seeding and the menu are complementary (seed-then-tune), not redundant.

---

## Step 6: Project Default Base Branch

Seed `project.default_base_branch` so `phase-1-init` can populate `references.base_branch` without falling back to whatever branch happens to be checked out at plan-creation time. The value is the project's canonical base branch — typically `main` or `master` for legacy projects.

**On non-first-run invocations** the prompt is skipped when `project.default_base_branch` is already set:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  project get --field default_base_branch
```

If the call returns the default value (or `field_not_found` in the legacy schema), proceed with the prompt below.

**Resolve the suggested default** from `git symbolic-ref refs/remotes/origin/HEAD`. Parse the output `refs/remotes/origin/{branch}` for the `{branch}` suffix and use it as the default suggestion. If the symbolic ref is unset (fresh clone without an `origin/HEAD` tracking ref), fall back to `main` as the last-resort default:

```bash
git -C . symbolic-ref refs/remotes/origin/HEAD
```

Treat a non-zero exit as the unset case — silently fall through to `main`.

**Prompt the operator** via `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "What is this project's default base branch?"
      header: "Project Default Base Branch"
      description: |
        `phase-1-init` will seed `references.base_branch` for every new plan from this value. Per-plan overrides remain available via `manage-references set --field base_branch` after init.

        **Detected default** (from `git symbolic-ref refs/remotes/origin/HEAD`): {detected_default}
      options:
        - label: "{detected_default}"
          description: "Use the detected default"
        - label: "main"
          description: "Use main"
        - label: "Custom"
          description: "Enter a custom branch name"
      multiSelect: false
```

When the operator selects `Custom`, follow up with a free-text `AskUserQuestion` for the branch name. Persist the chosen value:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  project set --field default_base_branch --value {answer}
```

---

## Step 7: Discover and Activate Providers

See [provider-setup.md](provider-setup.md#provider-discovery-and-activation-step-7) for the full discovery and activation workflow; the CI sub-step auto-selects the CI provider on high-confidence detection with manual fallback.

---

## Step 8: Project Architecture

Apply extension config defaults, discover the project's module architecture, document build commands, resolve Maven-profile matters, and run the LLM architectural analysis (including the architecture-refresh tier knobs).

See [architecture-setup.md](architecture-setup.md) for the full workflow.

---

## Step 8b: Seed the Build Map

After the project architecture is discovered (the extension set AND the module set are now known), seed `build.map` so the file-to-build contract reflects the project's *applicable* registered domain extensions. **This is the sole authoritative seed point** — the build map is NOT seeded at Step 5 (`init`) or by `sync-defaults`, because applicability scoping needs the discovered modules to decide which domains apply, and those modules only exist after Step 8. On a clean first run this reports `action: seeded` (the block did not previously exist). The write-once guard makes this first explicit seed authoritative; a wizard re-run reports `action: preserved` and picks up newly-added domain extensions only for domains not already in the block.

See [build-map-setup.md](build-map-setup.md) for the seed/read commands, the `action` (`seeded` / `preserved` / `re-derived`) interpretation, the `--force` clean re-derivation, and the menu re-seed operation.

---

## Step 9: Configure Skill Domains

Determine applicable skill domains from the architecture analysis, configure the `system` and technical domains, set active profiles, register execute-task skills, attach project-level skills, bulk-populate `skills_by_profile`, register recipes, and verify the result.

See [skill-domains-setup.md](skill-domains-setup.md) for the full workflow.

---

## Step 10: Plan Phase Settings (Optional)

Ask the user to accept defaults (`branch=feature`, `compatibility=breaking`, `commit_and_push=true`) or configure each field interactively. If configuring, apply each choice via manage-config:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init set --field branch_strategy --value {direct|feature}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field compatibility --value {breaking|deprecation|smart_and_ask}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field commit_and_push --value {true|false}
```

---

## Step 11: Quality Pipeline Configuration (Optional)

Ask the user to accept defaults (all generic verify steps + 10 finalize steps, default iterations) or configure individually. The 10 default finalize steps (the `BUILT_IN_FINALIZE_STEPS` list in `_config_defaults.py`) are `pre-push-quality-gate`, `commit-push`, `create-pr`, `ci-verify`, `automated-review`, `sonar-roundtrip`, `lessons-capture`, `branch-cleanup`, `record-metrics`, and `archive-plan`. `pre-push-quality-gate` is a built-in default whose activation is derived from `build.map` — it activates whenever the live footprint touches a glob registered in the build_map (those globs are the explicit `(pattern, role)` routes each *applicable* extension declares via `classify_globs()`, seeded at Step 8b, not author-shipped static literals). CI completion is a dispatcher-resolved precondition (`requires: [ci-complete]` declared on `ci-verify`, `automated-review`, and `sonar-roundtrip` frontmatters), not a sibling step. If configuring, discover available steps and apply.

**Verification steps** (phase-5-execute) — discover the project's canonical verify steps, then per-step multi-select.

The phase-5-execute verification pipeline is configured through the `verification_steps` list under `plan.phase-5-execute`. Each entry is a parameterized canonical-verify step ID of the form `default:verify:{canonical}` — the step-id vocabulary (which canonicals exist, how each derives a matrix role, and the module-scoped vs whole-tree distinction) is owned by the central canonical-verify standard at [`../../phase-5-execute/standards/canonical_verify.md`](../../phase-5-execute/standards/canonical_verify.md). Do NOT inline-copy the step IDs here; consult that doc for the authoritative set.

**Discover the project's canonical verify steps.** The set of canonicals the wizard offers is derived from the project architecture discovered in Step 8 — the build system and its resolvable commands determine which canonicals apply (e.g. a project with no integration-test profile does not surface `default:verify:integration-tests`). Enumerate the available steps via `list-verify-steps` (which reflects the discovered architecture) rather than hard-coding a list:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-verify-steps
```

**Present the discovered steps for selection** and write the chosen `verification_steps` list. The default selection is the project's discovered whole-tree canonicals (the end-of-phase-5 sweep gates — typically `quality-gate`, `module-tests`, and `coverage`, plus any whole-tree `integration-tests` / `e2e` the architecture resolved); operators may decline individual steps via the multi-select. Persist the chosen list with `set-steps`, which writes the `verification_steps` key:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps {selection}
```

The `verification_steps` list feeds the whole-tree end-of-phase-5 sweep; the module-scoped per-deliverable build is configured separately via `per_deliverable_build` (see [data-model.md](../../manage-config/standards/data-model.md) § phase-5-execute). Whole-tree-only gates such as `integration-tests` / `e2e` belong in `verification_steps`, never in `per_deliverable_build` — see [`../../phase-5-execute/standards/canonical_verify.md`](../../phase-5-execute/standards/canonical_verify.md) § "Module-scoped vs whole-tree invocation".

**Finalize steps** (phase-6-finalize) — preset-first, with a Custom escape hatch. Present the finalize-step preset picker BEFORE the per-step `list-finalize-steps` / `set-steps` flow, mirroring the single-AskUserQuestion preset-picker pattern documented in [effort-menu.md](../standards/effort-menu.md) (do not inline-copy that flow — the normative contract lives there). The three preset descriptions are sourced verbatim from `FinalizeStepPresets.describe(name)` (`finalize_step_presets.py`), and the Custom option falls through to the existing per-step multi-select escape hatch.

Optionally detect the current preset first — deep-equality of `plan.phase-6-finalize.steps` against `FinalizeStepPresets.get(name)` for each name in `FinalizeStepPresets.all_names()` — and surface it as `Current: {name} preset` / `Current: custom (manually edited)`, mirroring effort-menu Step 1.

```
AskUserQuestion:
  question: "Finalize-step pipeline — pick a preset"
  header: "Finalize Steps"
  options:
    - label: "Apply local preset"
      description: <FinalizeStepPresets.describe("local")>
    - label: "Apply standard preset"
      description: <FinalizeStepPresets.describe("standard")>
    - label: "Apply full preset"
      description: <FinalizeStepPresets.describe("full")>
    - label: "Custom"
      description: "Pick individual steps via the per-step multi-select"
  multiSelect: false
```

On a preset choice (`local`, `standard`, or `full`), apply it and skip the per-step multi-select:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  finalize-steps apply-preset --preset {name}
```

On `Custom`, fall through to the per-step multi-select escape hatch. The Custom path is **deterministic**, not a free-form add-on builder — it MUST be driven entirely by the `list-finalize-steps` enumeration, with the discipline below:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-steps --steps {selection}
```

**Custom-path discipline (mandatory — no improvisation):**

- **Drive the multi-select from `list-finalize-steps` verbatim.** `list-finalize-steps` already enumerates the full set — built-in (`BUILT_IN_FINALIZE_STEPS`), project (`project:`), and bundle-optional skill steps. Present exactly those steps. The wizard MUST NOT invent thematic "Add-ons" questions, MUST NOT group steps into invented categories, and MUST NOT couple semantically-unrelated steps under one toggle (e.g. bundling `sonar-roundtrip` with `plan-retrospective`, which forces a nonsense "retrospective but not sonar" undo). When the discovered step count exceeds the `AskUserQuestion` 4-option cap, **paginate** the multi-select across successive `AskUserQuestion` calls over the same `list-finalize-steps` output — never collapse the set into improvised thematic groups to fit the cap.
- **Start from the full discovered set; remove only on explicit decline.** The selection MUST START from the complete built-in + project + bundle-optional set returned by `list-finalize-steps`. A step is REMOVED from the selection ONLY when the operator explicitly declines it. A built-in step (e.g. `default:finalize-step-print-phase-breakdown`) MUST NOT be silently omitted because it fits no invented group — every built-in is in the starting set and survives unless the operator declines it.
- **Thread prior decisions; pre-exclude, never re-ask.** Decisions already made earlier in the wizard (e.g. a `sonar-roundtrip` the operator declined at provider/credential setup) MUST be threaded into the Custom selection: the declined step and any step that `requires:` it are PRE-EXCLUDED from the offered set, never re-surfaced for a second decline. The Custom path reads the already-recorded decisions rather than re-prompting for an answer the operator has already given.

If `set-steps` returns `missing_order` or `order_collision`, resolve it at the **config layer** — the steward sequences the explicit `phase-6.steps` array directly. The `phase-6.steps` array is runtime-authoritative; a step's source `order:` frontmatter (frontmatter on built-in standards docs / `SKILL.md` for `project:` steps / extension `provides_*_steps()` return-dict for skill steps) only governs the seed/presentation sort `marshall-steward` applies when first writing the array. To resolve a collision or a missing order, set the desired sequence in the `phase-6.steps` array via `set-steps` and re-run.

The steward MUST NEVER mutate a shared skill's source `order:` frontmatter to resolve a config-layer ordering concern. Editing a shared skill's `order:` to break a sort tie leaves an uncommitted source mutation in the worktree that risks leaking into an unrelated plan's commit, and changes the global seed order for every project — a config-layer concern resolved by a source-layer side effect. Sequence the array, never the source.

For max iterations (verification default 5, finalize default 3):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-max-iterations --value {n}
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-max-iterations --value {n}
```

---

## Step 12: Review Gates (Optional)

Configure whether phase transitions pause for user review or auto-continue. The defaults are a partition, not "all pause": auto-continue is the default for `init_without_asking` (phase 1→2), `execute_without_asking` (phase 4→5), and `finalize_without_asking` (phase 5→6), all of which default to `true`. Only `plan_without_asking` (phase 3→4) and `loop_back_without_asking` (phase 6→5 reverse) default to `false` (pause).

Ask user which transitions should auto-continue (multi-select):
- "Init without asking" → init (phase 1) to refine (phase 2). Defaults to `true` (auto-continue).
- "Plan without asking" → outline (phase 3) to planning (phase 4). Defaults to `false` (pause).
- "Execute without asking" → planning (phase 4) to execution (phase 5). Defaults to `true` (auto-continue).
- "Auto-continue plan lifecycle (both directions)" → the symmetric `finalize_without_asking` + `loop_back_without_asking` pair. Forward direction: execution (phase 5) to finalize (phase 6). Reverse direction: finalize (phase 6) `loop_back` outcome → execute (phase 5) inline. Defaults differ deliberately: `finalize_without_asking` defaults to `true` (forward auto-continue is the common case), but `loop_back_without_asking` defaults to `false` (reverse loop-back surfaces a control return to the user so unattended runs cannot silently re-enter execute on a finalize-side fix). The "accept defaults" branch persists `finalize_without_asking=true` and `loop_back_without_asking=false`. Treat them as a paired gate — opting into both ("full unattended cycle") is supported and bounded by `phase-6-finalize.max_iterations`, but it is an explicit user choice, not the default.

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

The `loop_back_without_asking` knob is the structural counterpart to `finalize_without_asking`: forward gates the `5-execute → 6-finalize` transition, reverse gates the `6-finalize → 5-execute` inline re-dispatch when a phase-6-finalize step records `outcome: loop_back` (FIX disposition, `pr-comment-overflow`, sonar-roundtrip FIX). Defaults are intentionally asymmetric — `finalize_without_asking=true` (forward auto-continue) and `loop_back_without_asking=false` (reverse halt-and-prompt). Opt into `loop_back_without_asking=true` for the full unattended cycle in both directions. Reverse loop-back is also bounded by `phase-6-finalize.max_iterations` (default 3) — the dispatcher halts and prompts the user when the cap is reached even with the flag set.

---

## Step 13: Detect CI Provider and Configure Credentials (Optional)

Detect the CI provider, verify its CLI tool, and optionally configure credentials for external tools.

See [provider-setup.md](provider-setup.md#ci-provider-detection-step-13) for CI detection and [provider-setup.md](provider-setup.md#credential-setup-step-13-optional) for credential setup.

---

## Step 14: Permission Setup (Optional)

```
AskUserQuestion:
  question: "Configure permissions now?"
  options:
    - label: "Yes"
      description: "Set up global and project permissions"
      value: "yes"
    - label: "Later"
      description: "Skip permission setup for now"
      value: "no"
```

If yes, run these two commands sequentially — the first applies project-scope fixes; the second installs a narrow global allow rule for the `TERM_PROGRAM` detection pattern used by workflow auto-open / IDE hand-off steps (eliminates the `simple_expansion` permission prompt):

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-fixes --scope project
```

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure --permissions 'Bash(echo "TERM_PROGRAM=$TERM_PROGRAM")' --target global
```

The `ensure` subcommand is idempotent — re-running the wizard does not duplicate the entry.

---

## Step 15: Summary

Output final summary:

```toon
status: success
operation: wizard_complete

gitignore: configured
executor:
  path: .plan/execute-script.py
  script_count: 45
marshal:
  path: .plan/marshal.json
project_architecture:
  path: .plan/project-architecture/
  modules_count: 3
skill_domains:
  - documentation
  - plan-marshall-plugin-dev

next_steps:
  - Run /plan-marshall to create a new plan
  - Use /marshall-steward for maintenance tasks
```

After summary output, wizard is complete. Exit skill execution.
