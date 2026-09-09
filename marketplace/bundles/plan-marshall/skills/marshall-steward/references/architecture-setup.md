# Architecture Setup Reference

Extracted architecture-related wizard logic covering extension config defaults, module discovery, build-command documentation, Maven-profile resolution, and the LLM architectural analysis (including the architecture-refresh tier knobs). Referenced by `wizard-flow.md` Step 8.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Apply Extension Defaults

Apply project-specific configuration defaults from domain extensions BEFORE discovery. Each extension's `config_defaults()` callback is invoked to set domain-specific values in `marshal.json`.

**Why before discovery**: This sets profile skip lists and mappings that the discovery step uses to filter profiles. Running this first ensures discovered modules contain only relevant profiles.

```bash
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery apply-config-defaults
```

**Output (TOON)**:
```toon
status	success
extensions_called	3
extensions_skipped	2
errors_count	0
```

| Field | Description |
|-------|-------------|
| `extensions_called` | Extensions that provided config_defaults() |
| `extensions_skipped` | Extensions without config_defaults() implementation |
| `errors_count` | Failures during callback execution |

**Contract**: Extensions use write-once semantics - they only set defaults if keys don't already exist in `marshal.json`. User-defined values are never overwritten.

**Example defaults set by extensions**:
- Profile skip lists (e.g., `release,sonar,license-cleanup`)
- Profile-to-canonical mappings (e.g., `pre-commit:quality-gate`)
- Build-specific timeout defaults

See `standards/extension-contract.md` in `extension-api` skill for the callback contract.

## Discover Project Architecture (Source of Truth)

Discover modules directly from filesystem via extension API. This writes the per-module architecture layout under `.plan/project-architecture/`: a top-level `_project.json` whose `modules` index is the single source of truth for "which modules exist", plus one subdirectory per module containing an LLM-curated `enriched.json` stub (seeded empty, filled by later enrichment runs). Per-module directories present on disk but absent from `_project.json["modules"]` MUST be ignored — the index is authoritative, not the filesystem. Derived module data (paths, packages, dependencies, file inventories) is intentionally NOT persisted to disk — it is computed on demand by `crawl_module_derived` against the live worktree on every read.

**Prerequisites**: Apply Extension Defaults (above) sets up profile skip lists and mappings in `run-configuration.json`, so discovered profiles are already filtered.

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**Output (TOON)**:
```toon
status	success
modules_discovered	10
output_dir	.plan/project-architecture/
```

This produces:

- `.plan/project-architecture/_project.json` — project metadata (`name`, `description`, `extensions_used`) and the module index.
- `.plan/project-architecture/{module}/enriched.json` — LLM-curated stub for each module (seeded empty by discover; populated by later enrichment runs).

Derived module data (paths, packages, dependencies, file inventories) is *not* written here — it is computed on demand by `crawl_module_derived` whenever a downstream caller asks for it.

**Verification** - Display discovered modules:
```text
Modules discovered: 10
  - bom (pom, maven)
  - oauth-sheriff-core (jar, maven)
  - oauth-sheriff-quarkus-parent (pom, maven)
  - oauth-sheriff-quarkus (jar, maven) [parent: oauth-sheriff-quarkus-parent]
  - oauth-sheriff-quarkus-deployment (jar, maven+npm) [parent: oauth-sheriff-quarkus-parent]
  ...
```

**Hybrid modules** are detected automatically when both pom.xml and package.json exist.

## Document Build Commands in the Agent-Instructions File

**Purpose**: Add resolved build commands to the project's agent-instructions file so agents invoke builds via canonical names, not hard-coded tool commands. The write target is the **active target's** agent-instructions file — `CLAUDE.md` on Claude, `AGENTS.md` on OpenCode — resolved through the shared per-target lookup (`marketplace_paths.agent_instructions_filename()`), never a hardcoded `CLAUDE.md`.

**Prerequisite**: Discovery completed (architecture API is available).

**Skip condition**: If the agent-instructions file already has a `### Build Commands` heading, skip this sub-operation.

**Conflict handling**: If the agent-instructions file contains hand-written build patterns (`mvn`, `mvnw`, `gradle`, `npm run`, `./pw`, "build command"), ask before writing. Name the patterns that were found in the question, so the user is deciding about text they can identify:

```text
AskUserQuestion:
  question: "Your agent-instructions file already describes how to build this project, in text somebody wrote by hand: {matched_patterns}. There is no way to tell from here whether that is still correct or left over from an earlier setup. Writing the resolved build commands over it would replace it. Should it?"
  header: "Build text"
  options:
    - label: "Replace existing (recommended)"
      description: "The hand-written text is overwritten with the build commands resolved for your modules, so agents call builds by canonical name rather than by a spelling that may no longer work. This is the only build-command edit that removes text you wrote"
    - label: "Keep existing"
      description: "Your agent-instructions file is left byte-for-byte as it is and no build-command section is written. Choose this if the text is deliberate; re-run the wizard later if you change your mind"
  multiSelect: false
```

On Keep existing, skip the rest of this sub-operation.

**Resolve available commands** for the default module across all canonical commands (`compile`, `quality-gate`, `module-tests`, `verify`, `integration-tests`, `e2e`, `coverage`, `benchmark`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command {canonical} --module default
```

Collect the `executable` value from each successful resolution. Track which canonical command names resolved on the default module (the "default commands set").

**Collect child-module-only commands**: For each non-default module, resolve the same canonical commands and keep any that resolved on the child module but NOT on default. These become child-module-only entries (e.g., `benchmark` or `e2e` exclusive to specific modules).

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve --command {canonical} --module {module_name}
```

**Add to the agent-instructions file** (the active target's file — `CLAUDE.md` on Claude, `AGENTS.md` on OpenCode) under the heading `### Build Commands` (in a "Development Notes" section) with bullets: a "Never hard-code" preamble, one bullet per resolved canonical command (`Compile`, `Quality gate`, `Tests`, `Full verify`, plus `Integration tests`, `E2E`, `Coverage`, `Benchmark` only when resolved on default), one bullet per child-module-only command in the form `{Canonical} ({module_name}): {executable} — only on {module_name}`, a reminder to use a 10-minute Bash timeout (600000ms — the Claude-target `harness bash-timeout-ceiling` default, resolved per active target), and a reminder to analyze each build's TOON result (`status`, `errors[N]{file,line,message,category}`, `log_file`).

Only include commands that resolved successfully.

## Review Unmatched Build Profiles (Maven Only)

**Condition**: Only if any Maven module was discovered.

Iterate the modules listed in `_project.json["modules"]` and load each module's derived data (computed on demand by `crawl_module_derived`) to look for profiles with `"canonical": "NO-MATCH-FOUND"` in `metadata.profiles`.

**If NO-MATCH-FOUND profiles exist**:

Load skill `pm-dev-java:manage-maven-profiles` and follow its workflow to:
1. Ask user about each unmatched profile (Ignore/Skip/Map)
2. Apply configuration via `manage-config ext-defaults` commands
3. Re-run discovery to apply changes:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**If no Maven modules OR no unmatched profiles** → continue to Resolve Profile Conflicts.

## Resolve Profile Conflicts (Maven Only)

**Condition**: Only if any Maven module was discovered.

Iterate the modules listed in `_project.json["modules"]` and inspect each module's derived data (computed on demand by `crawl_module_derived`) for cases where multiple profiles map to the same canonical command. The `commands` section in the derived payload is built from `_build_commands()` which detects conflicts — look for a `conflicts` key in any module's commands output.

Alternatively, inspect each module's `metadata.profiles` and group by canonical value. If any canonical has more than one profile mapped to it, a conflict exists.

**If conflicts exist** (e.g., both `pre-commit` and `sonar` map to `quality-gate`):

Ask the user which profile to use for each conflicting canonical command:

```text
AskUserQuestion:
  questions:
    - question: "More than one Maven profile in this project looks like the '{canonical}' build, so it is ambiguous which one to run. Which of them is it?"
      header: "Profiles"
      options:
        # For each conflicting profile (dynamic):
        - label: "{profile_id}"
          description: "Runs `mvn verify -P{profile_id}` whenever this project's {canonical} build is called for"
      multiSelect: false
```

After user selects, update the module's commands to use the chosen profile:
1. Store the user's choice via `manage-config ext-defaults set` with key `build.maven.profiles.map.canonical` and value `{profile_id}:{canonical}` (append to existing comma-separated mappings)
2. Re-run discovery to apply the explicit mapping:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover --force
```

**If no conflicts** → continue to Project Structure Analysis.

## Project Structure Analysis

Generate project structure knowledge for solution outline support.

**Prerequisites**: Discovery created the per-module architecture layout (`_project.json` plus per-module `enriched.json` stubs) under `.plan/project-architecture/`. Derived module data is computed on demand by `crawl_module_derived` whenever downstream readers need it.

### LLM Architectural Analysis

Invoke the analysis skill to read raw data and generate meaningful structure:

```text
Skill: plan-marshall:manage-architecture
```

The LLM analysis reads discovered data, samples documentation and source code, then enriches with:
- Semantic module responsibilities (not just names)
- Module purpose classification (library, extension, runtime, etc.)
- 2-4 key packages per module with descriptions
- Proposed skill domains
- Implementation tips and insights

**Output**: One `.plan/project-architecture/{module}/enriched.json` per module, each holding the LLM-augmented fields for that module. The top-level `_project.json` may also receive enriched project-level metadata (e.g., `description`, `description_reasoning`).

### User Refinement (Optional)

Display the generated structure and ask whether to accept as-is or refine module responsibilities. On refine, iterate modules with uncertain analysis, confirm each responsibility with the user, and persist the chosen text:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich module --name {module_name} --responsibility "{text}"
```

### Verify Structure

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
```

Verify that all modules have responsibilities and key packages. Missing fields indicate areas needing attention.

### Architecture Refresh Tier Knobs

Configure how the `phase-6-finalize` `architecture-refresh` step behaves on every plan finalize. Both knobs persist to `run-config.json` via the `plan-marshall:manage-run-config` `architecture-refresh` subcommand group documented in `manage-run-config/SKILL.md`. Defaults match the user-locked decision from Phase D (`tier_0=enabled`, `tier_1=prompt`).

This sub-operation is also the entry point reached when a returning user selects **Configuration → Full Reconfigure** from the maintenance menu, so the same prompts cover both first-run setup and ongoing maintenance.

**Question 1 — Tier 0 (deterministic refresh)**:

```text
AskUserQuestion:
  question: "plan-marshall keeps a map of how this project is laid out and uses it to find things. Each time a plan finishes, it can re-read the project and correct that map. Doing so is quick. Should it?"
  header: "Re-read"
  options:
    - label: "Enabled (recommended)"
      description: "Re-reads the project after every plan and records the changes, so the map never silently goes stale"
    - label: "Disabled"
      description: "Never re-reads it; the map drifts out of date as the project changes until you refresh it yourself"
  multiSelect: false
```

Map the selection to a `tier_0` value (`Enabled (recommended)` → `enabled`; `Disabled` → `disabled`) and persist:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config \
  architecture-refresh set-tier-0 --value {enabled|disabled}
```

**Question 2 — Tier 1 (LLM re-enrichment)**:

```text
AskUserQuestion:
  question: "Re-reading the project can show that a part of it changed enough that its written description no longer fits. Rewriting those descriptions takes noticeably longer than the re-read itself. What should happen when that comes up?"
  header: "Descriptions"
  options:
    - label: "Ask me each time (recommended)"
      description: "You are asked once, at the end of the plan that changed it, so you can weigh the extra time against the day you are having"
    - label: "Rewrite them automatically"
      description: "The out-of-date descriptions are rewritten and committed for you, and ship alongside the rest of the plan's work"
    - label: "Leave them alone"
      description: "Descriptions are never rewritten; the parts that had drifted are written down so you can catch up on them later"
  multiSelect: false
```

Map the selection to a `tier_1` value (`Ask me each time (recommended)` → `prompt`; `Rewrite them automatically` → `auto`; `Leave them alone` → `disabled`) and persist:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config \
  architecture-refresh set-tier-1 --value {prompt|auto|disabled}
```

**Note**: `change_type ∈ {bug_fix, verification}` skips Tier 1 regardless of this setting (see `phase-6-finalize/standards/architecture-refresh.md`). Both knobs are read at finalize time via the `architecture-refresh get-tier-0` / `get-tier-1` subcommands; neither is materialised in `run-config.json` until the user explicitly sets a value, so default behaviour is preserved on fresh projects.
