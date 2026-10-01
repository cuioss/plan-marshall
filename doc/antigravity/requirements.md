# Multi-Target Distribution, Selective Bundle Installation & Harness-Aware Steward Requirements

**Document ID**: `REQ-SPEC-MULTI-TARGET-001`  
**Status**: Ground-Truth Verified against `main` (PR `#1646`, PR `#1662`, PR `#1663`)  
**Target Harnesses**: Google Antigravity, OpenCode, Claude Code

---

## 1. Ground-Truth Baseline (Already Implemented — Excluded from Scope)

The following capabilities are already implemented on `main` and are **removed from active scope**:

1. **Antigravity & OpenCode Target Compilers (`marketplace/targets/{antigravity,opencode}/`)**:
   - Complete target packages (`target.py`, `emitter.py`, `frontmatter.py`, `variant_emitter.py`, `mapping.json`, `frontmatter-rules.json`, `templates/user-invocable-command.md`, `templates/install.sh`) and ADR-021 `level_pins` agent variant generation.
2. **Dist-Branch Consumer Installation Structure (Archived in `done/`)**:
   - `install.sh` and `README.adoc` emission for `target/antigravity`, `target/opencode`, and `target/claude`.
   - CI publication matrix in `.github/workflows/claude-distribute.yml` publishing `dist-claude`, `dist-opencode`, and `dist-antigravity`.
   - `dist-manifest.json` emission in `marketplace/targets/generate.py` at the root of each target output directory containing `version`, `source_sha`, `executor_scripts_fingerprint`, `executor_changed_at_version`, `config_seed_fingerprint`, and `config_changed_at_version`.
3. **Empirical Target Resolution & Flat-Layout Skill Identity (PR `#1646`)**:
   - `marketplace/bundles/plan-marshall/skills/script-shared/scripts/target_context.py` implements `detect_target_from_env()` (`ANTIGRAVITY_AGENT` $\to$ `'antigravity'`, `OPENCODE`/`OPENCODE_PID` $\to$ `'opencode'`, `CLAUDE_CODE_SESSION_ID` $\to$ `'claude'`), the 3-tier `resolve_target(cwd)` cascade (`env` $\to$ `marshal_json` `runtime.target` $\to$ `fallback`), and `resolve_context(target, marketplace_root, cwd)`.
   - `marketplace/targets/skill_identity.py` and `marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py` stamp every emitted flat `SKILL.md` (`target/antigravity/skills/{bundle}-{skill}/SKILL.md` and `target/opencode/skill/{bundle}-{skill}/SKILL.md`) with:
     ```yaml
     metadata:
       bundle: <bundle>
       skill: <skill>
     ```
     and provide `read_flat_skill_identity(skill_dir)` for unambiguous bundle attribution without prefix-splitting heuristics.
   - `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` already provides `project_initial_setup` and `project_install_hook` (`.agents/hooks.json`), and `opencode_runtime.py` provides `opencode_enforcement_apply`.
4. **`marshall-steward` Local Harness Configuration & Verification (`REQ-STEW-1..4`, PR `#1662`)**:
   - `determine_mode.py` actively checks the runtime harness via `target_context.resolve_target()` and provides `check-harness` to verify schema, checksum freshness, and executor readiness against `.plan/local/harness/{target}.json`.
   - `configure_harness.py` deterministically configures local harness state, invoking target-specific setup hooks with zero conversational LLM prompts and zero git pollution.
   - Linked git worktrees inherit `.plan/local/harness/{target}.json` via `resolve_main_anchored_path()`.
   - Integrated into `marshall-steward` preflight, wizard completion, and health checks.
5. **Selective Bundle Installation, Atomic Updates & Safe Uninstall Lifecycle (`REQ-INST-1..6`, PR `#1663`)**:
   - Target emitters generate `bundle-components.json` mapping each bundle to its emitted skills, agents, and commands.
   - `install.sh` supports selective flags (`--all`, `--core-only`, `-b/--bundles`, `--without-bundles`), group aliases, automatic dependency closures, and `/dev/tty` interactive selection.
   - Persistent manifests (`.install-manifest.json` and `.plan-marshall-manifest.json`) and configuration tailoring (`plugin.json` and `opencode.json`, with custom agent preservation).
   - Atomic update (`-U, --update`) with pre-update snapshot under `.install-backup/`, obsolete file pruning, and automatic rollback on failure.
   - Safe uninstallation (`--uninstall`) and selective bundle removal (`--uninstall --bundles`).

---

## 2. Requirement Area 1: Selective Bundle Installation, Update & Uninstall Lifecycle (`REQ-INST-1..6`) — IMPLEMENTED & VERIFIED

**Implementation Plan**: `doc/antigravity/plans/selective-bundle-installer.md` (Archived in `doc/antigravity/done/selective-bundle-installer.md`; Merged in PR `#1663`)  
**Status**: Implemented, Verified & Merged (41 unit/integration tests in `test/marketplace/targets/{antigravity,opencode}/test_emitter.py`)

### 2.1 Problem Statement & Ground-Truth Gap (Resolved)
The prior wholesale component copying in `marketplace/targets/{antigravity,opencode}/templates/install.sh` has been completely replaced with a deterministic, selective lifecycle engine:
- **Bundle Bloat Eliminated**: Consumers can install only the needed domain modules or core runtime.
- **Component Attribution for Agents & Commands**: Emitters generate `bundle-components.json` with per-bundle relative paths for `skills`, `agents`, and `commands`.
- **Update State Preserved**: Re-running `install.sh -U` / `--update` detects the existing manifest, remembers previously installed bundles, creates `.install-backup/`, prunes obsolete files, and rolls back on failure.
- **Safe & Non-Destructive OpenCode Uninstall**: OpenCode `--uninstall` removes tracked `managed_files` from the manifest (or `bundle-components.json` inventory fallback) and cleans empty parent directories under `skill/`, strictly preserving third-party user skills.

### 2.2 Bundle Hierarchy, Aliases & Dependency Resolution
- **Core Bundle (Mandatory)**: `plan-marshall` (plus target harness bundle `plan-marshall-{target}` when present in the distribution).
- **Selectable Domain Bundles**:
  - `pm-dev-java`: Core Java, JUnit 5, CDI/Quarkus, ArchUnit gate, Maven profiles.
  - `pm-dev-java-cui`: CUI Java standards (CuiLogger, OpenRewrite, CUI HTTP). *Depends on `pm-dev-java`.*
  - `pm-dev-python`: Python 3.10+, pytest, pyprojectx, import-linter gate.
  - `pm-dev-frontend`: JS/TS, CSS, Lit, ESLint, Jest, JS arch gate.
  - `pm-dev-frontend-cui`: CUI JS/Maven integration. *Depends on `pm-dev-frontend`.*
  - `pm-dev-oci`: OCI container standards and security.
  - `pm-documents`: AsciiDoc, documentation and diagram verification.
  - `pm-plugin-development`: Marketplace plugin creation, doctor, maintenance.
  - `pm-requirements`: Requirements engineering and traceability.
- **Dependency Closure**:
  - `pm-dev-java-cui` $\to$ `pm-dev-java`
  - `pm-dev-frontend-cui` $\to$ `pm-dev-frontend`
- **Group Aliases**:
  - `all`: All bundles in the distribution (default for non-interactive runs without bundle flags).
  - `core`: Mandatory core (`plan-marshall` + target harness bundle only).
  - `java`: `pm-dev-java`, `pm-dev-java-cui`
  - `python`: `pm-dev-python`
  - `frontend`: `pm-dev-frontend`, `pm-dev-frontend-cui`
  - `oci`: `pm-dev-oci`
  - `docs`: `pm-documents`
  - `reqs`: `pm-requirements`
  - `plugin-dev`: `pm-plugin-development`

### 2.3 Installation Manifest Schema
- **Paths**:
  - Antigravity: `${TARGET_DIR}/.install-manifest.json`
  - OpenCode: `${TARGET_DIR}/.plan-marshall-manifest.json`
- **Schema** (strictly no timestamps):
  ```json
  {
    "schema_version": 1,
    "target": "antigravity",
    "scope": "global",
    "installed_ref": "dist-antigravity",
    "dist_manifest_sha": "<sha256-of-dist-manifest.json>",
    "core": "plan-marshall",
    "installed_bundles": [
      "plan-marshall",
      "pm-dev-python"
    ],
    "managed_files": [
      "skills/plan-marshall-plan-marshall/SKILL.md",
      "skills/pm-dev-python-python-core/SKILL.md",
      "agents/plan-marshall-execution-context.md",
      "commands/plan-marshall-plan-marshall.md"
    ]
  }
  ```

### 2.4 Requirements & Implementation Verification (`REQ-INST-1..6`)

- **`REQ-INST-1` (Bundle Attribution & Dependency Closure)**:
  - *Verification Status*: **Complete & Verified** (PR `#1663`).
  - *Implementation Details*: `marketplace/targets/antigravity/emitter.py` and `marketplace/targets/opencode/emitter.py` write `bundle-components.json` at `output_dir / 'bundle-components.json'` mapping each bundle to its relative component paths (`skills`, `agents`, `commands`). Core `plan-marshall` is mandatory; target harness core bundles (`plan-marshall-{target}`) are protected when present; closures `pm-dev-java-cui` $\to$ `pm-dev-java` and `pm-dev-frontend-cui` $\to$ `pm-dev-frontend` are automatically resolved during installation and checked during selective uninstallation.
- **`REQ-INST-2` (Interactive `/dev/tty` Selection & Python 3 Helper)**:
  - *Verification Status*: **Complete & Verified** (PR `#1663`).
  - *Implementation Details*: `install.sh` explicitly opens and reads `/dev/tty` (`[ -t 0 ] || [ -r /dev/tty ]`) when run interactively (supporting `curl ... | bash` pipelines), displaying `[A]ll (default)`, `[C]ore only`, or a comma-separated list of bundles/aliases. In non-interactive environments (CI, or when `PLAN_MARSHALL_NON_INTERACTIVE=1`), it cleanly defaults to `--all`. An embedded Python 3 stdlib helper handles parsing, resolution, and filtering with zero external CLI dependencies (no `jq`).
- **`REQ-INST-3` (Non-Interactive CLI Flags)**:
  - *Verification Status*: **Complete & Verified** (PR `#1663`).
  - *Implementation Details*: Flags `--all`, `--core-only`, `-b` / `--bundles <csv>`, and `--without-bundles <csv>` are implemented in both Antigravity and OpenCode `install.sh`. Flag validation fails closed with exit code 2 on unknown bundle names, attempts to exclude the core bundle, or excluding a base bundle while its dependent child is requested.
- **`REQ-INST-4` (Persistent Installation Manifest & Manifest Tailoring)**:
  - *Verification Status*: **Complete & Verified** (PR `#1663`).
  - *Implementation Details*: Antigravity writes `${TARGET_DIR}/.install-manifest.json` and prunes `plugin.json` (`"bundles"` array). OpenCode writes `${TARGET_DIR}/.plan-marshall-manifest.json` and prunes `opencode.json` commands and agents. The manifest schema matches the specification with strictly zero timestamps.
  - *Adaptation Confirmed in Implementation*: OpenCode config tailoring strictly preserves user-defined custom agents and commands (any components not part of `bundle-components.json`).
- **`REQ-INST-5` (Atomic Update `--update` / `-U`)**:
  - *Verification Status*: **Complete & Verified** (PR `#1663`).
  - *Implementation Details*: `-U` / `--update` detects existing manifests and defaults to the previously installed bundle set unless overridden. Supports `--without-bundles` overlay during updates. Creates a temporary backup in `${TARGET_DIR}/.install-backup/` containing all managed files, configuration, and manifest; prunes obsolete files; installs new files; and automatically restores all files from backup upon any failure before exiting.
  - *Adaptation Confirmed in Implementation*: Installed target directories containing `.install-manifest.json` or `.plan-marshall-manifest.json` are excluded from being detected as local source distribution trees during updates, and `TARGET_DIR` is automatically inferred from `SCRIPT_DIR` for installed scripts.
- **`REQ-INST-6` (Safe & Selective Uninstallation)**:
  - *Verification Status*: **Complete & Verified** (PR `#1663`).
  - *Implementation Details*: Antigravity full `--uninstall` cleanly removes `${TARGET_DIR}`. OpenCode full `--uninstall` removes all paths listed in `managed_files` from `.plan-marshall-manifest.json` (falling back to `bundle-components.json` inventory if the manifest is absent) and cleans empty parent directories under `skill/`, without touching third-party user skills or custom agents. Selective uninstallation (`install.sh --uninstall --bundles <csv>`) validates closures (refusing removal of core or base bundles whose children remain installed), deletes only the specified bundle files, and tailors the manifest and configuration.

---

## 3. Requirement Area 2: Harness-Specific Bundles & Zero-Token Target Rules (`REQ-HBNDL-1..6`) — IMPLEMENTED & VERIFIED

**Implementation Plan**: `doc/antigravity/plans/harness-bundles-target-rules.md`  
**Status**: Implemented & Verified (`feature/harness-bundles-target-rules`)  
**Test Evidence**: 308 passing tests across `test_component_targets.py` (112 tests), `test_analyze_target_scope.py` (130 tests), and emitter test suites for Antigravity, OpenCode, and Claude (66 tests).

### 3.1 Problem Statement & Ground-Truth Gap (Resolved)
- Bundle-level target scoping is fully implemented in `marketplace/targets/component_targets.py` and enforced across Claude, OpenCode, and Antigravity target emitters.
- Target-specific operational rules for Antigravity and OpenCode are packaged into first-class target-scoped bundles (`plan-marshall-antigravity` with `targets: ["antigravity"]`, and `plan-marshall-opencode` with `targets: ["opencode"]`).
- Installer scripts (`install.sh`) automatically emit zero-token rules into `<workspace>/.agents/rules/plan-marshall-target-rules.md` (Antigravity) and `<workspace>/.opencode/rules/plan-marshall-target-rules.md` (OpenCode) when `--workspace` or `--emit-rules` is passed, and cleanly clean them up on uninstallation.
- `plugin-doctor` validates bundle-level `"targets"` in `.claude-plugin/plugin.json` and flags bundle-to-component contradictions.

### 3.2 Requirements & Implementation Verification (`REQ-HBNDL-1..6`)

- **`REQ-HBNDL-1` (Bundle-Level Target Scoping in `component_targets.py` & Emitters)**:
  - *Verification Status*: **Complete & Verified**.
  - *Implementation Details*: Extended `marketplace/targets/component_targets.py` with `read_bundle_target_scope(bundle_dir: Path) -> frozenset[str] | None` and `bundle_emits_to(bundle_dir: Path, target_name: str) -> bool`. Enforces fail-closed validation (`TargetScopeError` on unknown target names, empty list, non-component-tree target, or non-string items). Invariant enforced: component targets must be a subset of enclosing bundle targets.
  - *Target Integration*: Filtered across Claude (`target.py`, `equality_check.py`, `marketplace_json_gen.py`, `plugin_json_gen.py`), OpenCode (`opencode/emitter.py`), and Antigravity (`antigravity/emitter.py`).
  - *Test Coverage*: 112 tests passing in `test/marketplace/targets/test_component_targets.py`.
- **`REQ-HBNDL-2` (`plugin-doctor` Bundle Target Scope Support)**:
  - *Verification Status*: **Complete & Verified**.
  - *Implementation Details*: Extended `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_target_scope.py` with `_validate_bundle_plugin_json` (`targets_empty`, `targets_unknown`) and `_find_bundle_contradictions` (`targets_contradiction`).
  - *Test Coverage*: 130 tests passing in `test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py`.
- **`REQ-HBNDL-3` (Harness Bundles `plan-marshall-antigravity` & `plan-marshall-opencode`)**:
  - *Verification Status*: **Complete & Verified**.
  - *Implementation Details*: Created `marketplace/bundles/plan-marshall-antigravity/` (`"targets": ["antigravity"]`) and `marketplace/bundles/plan-marshall-opencode/` (`"targets": ["opencode"]`). Both registered in `marketplace/.claude-plugin/marketplace.json`. Each provides `skills/target-rules/SKILL.md` (`mode: knowledge`), `README.md`, and normative standards (`standards/antigravity-rules.md`, `standards/opencode-rules.md`).
  - *Mutual Exclusivity*: Verified via `generate --target all --output .plan/temp/all-targets` and unit tests in `test_emitter.py`.
- **`REQ-HBNDL-4` (Antigravity Target Rules Content)**:
  - *Verification Status*: **Complete & Verified**.
  - *Implementation Details*: `marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md` codifies:
    1. Antigravity tool invariants (`run_command`, `view_file`, `write_to_file`, `replace_file_content`, `ask_question`, `invoke_subagent`, `send_message`, `manage_task`, `schedule`).
    2. Terminal sandbox discipline (one command per call, no shell file inspection, explicit working directory).
    3. Reactive background task & subagent handling (never poll `status` in a loop; rely on reactive wakeups).
    4. `.plan/` script-only access via `python3 .plan/execute-script.py`.
    5. Artifact isolation in `<appDataDir>/brain/<conversation-id>/`.
- **`REQ-HBNDL-5` (OpenCode Target Rules Content)**:
  - *Verification Status*: **Complete & Verified**.
  - *Implementation Details*: `marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md` codifies OpenCode tool mappings (`bash`, `read`, `edit`, `glob`, `grep`, `question`, `task`, `skill`), flat deployed layout conventions (`~/.config/opencode/skills/` / `.opencode/skills/`), single-command-per-call discipline, and `.plan/` script-only access.
- **`REQ-HBNDL-6` (Zero-Token Native Rule Delivery & Fail-Safe Entrypoints)**:
  - *Verification Status*: **Complete & Verified**.
  - *Implementation Details*: Updated `marketplace/targets/antigravity/templates/install.sh` and `marketplace/targets/opencode/templates/install.sh` with `--emit-rules` support and `sync_workspace_rules` in Python. Automatically copies target rules into `<workspace>/.agents/rules/plan-marshall-target-rules.md` (Antigravity) and `<workspace>/.opencode/rules/plan-marshall-target-rules.md` (OpenCode) when `--workspace` or `--emit-rules` is set. Full and selective uninstalls cleanly remove the rule file.
  - *Test Coverage*: Validated by integration tests in `test/marketplace/targets/antigravity/test_emitter.py` (`test_antigravity_workspace_rule_emission`) and `test/marketplace/targets/opencode/test_emitter.py` (`test_opencode_workspace_rule_emission`).

---

## 4. Requirement Area 3: `marshall-steward` Harness-Aware Run & Script-Only Local Harness Configuration (`REQ-STEW-1..4`) — IMPLEMENTED & VERIFIED

**Implementation Plan**: `doc/antigravity/plans/steward-harness-config.md` (Archived in `doc/antigravity/done/steward-harness-config.md`; Merged in PR `#1662`)  
**Status**: Implemented, Verified & Merged (11 unit tests in `test/plan-marshall/marshall-steward/test_harness_config.py`)

### 4.1 Problem Statement & Ground-Truth Gap (Resolved)
The prior gap where `determine_mode.py` only checked for `.plan/execute-script.py` and `.plan/marshal.json` regardless of the active runtime harness has been resolved:
- **Active Target Identification**: `determine_mode.py` delegates harness detection to `target_context.resolve_target()`.
- **Harness State Schema**: Per-checkout harness readiness is tracked in `.plan/local/harness/{target}.json`.
- **Deterministic Script Configuration**: `configure_harness.py` configures harness state deterministically without conversational LLM prompt overhead.

### 4.2 Local Harness State Schema (`.plan/local/harness/{target}.json`)
- **Location**: `.plan/local/harness/{target}.json` (e.g. `.plan/local/harness/antigravity.json`, `.plan/local/harness/opencode.json`, `.plan/local/harness/claude.json`).
- **Schema** (strictly no timestamps):
  ```json
  {
    "schema_version": 1,
    "harness": "antigravity",
    "target_source": "env",
    "dist_manifest_sha": "<sha256-of-dist-manifest-or-executor-script>",
    "checks": {
      "rules_emitted": true,
      "harness_paths_valid": true,
      "executor_ready": true
    },
    "settings": {
      "auto_sandbox_elevation": false
    }
  }
  ```

### 4.3 Requirements & Implementation Verification (`REQ-STEW-1..4`)

- **`REQ-STEW-1` (Active Harness Verification via `target_context` in `determine_mode.py`)**:
  - *Verification Status*: **Complete & Verified** (PR `#1662`).
  - *Implementation Details*: `determine_mode.py` imports and delegates active target detection to `target_context.resolve_target()` / `target_context.resolve_context()` from `plan-marshall:script-shared` (PR `#1646`), supporting optional `--harness` override. Subcommand `determine_mode.py check-harness [--harness {target}]` inspects `.plan/local/harness/{target}.json`, verifies schema validity, checks `dist_manifest_sha` freshness, and checks `checks.executor_ready` and `checks.harness_paths_valid`. `determine_mode.py mode` returns `harness`, `target_source`, `harness_configured`, and `harness_reason`.
- **`REQ-STEW-2` (Deterministic Script-Only `configure_harness.py`)**:
  - *Verification Status*: **Complete & Verified** (PR `#1662`).
  - *Implementation Details*: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py` is implemented and registered in the executor. It runs deterministically with zero conversational LLM prompts: resolves active target via `target_context.resolve_context()`, invokes target-specific `platform-runtime` setup hooks, emits/updates `.plan/local/harness/{target}.json`, and produces zero git pollution (guaranteed by `.plan/.gitignore`).
- **`REQ-STEW-3` (Worktree Inheritance)**:
  - *Verification Status*: **Complete & Verified** (PR `#1662`).
  - *Implementation Details*: Routes `.plan/local/harness/{target}.json` resolution through `marketplace_paths.resolve_main_anchored_path(f'harness/{target}.json')`, enabling linked worktrees under `.plan/local/worktrees/{plan_id}` to inherit the main repository checkout's configured harness state without duplicated configuration.
- **`REQ-STEW-4` (`marshall-steward` Wizard, Menu Preflight & Health Check Integration)**:
  - *Verification Status*: **Complete & Verified** (PR `#1662`).
  - *Implementation Details*: Preflight in Menu Mode runs `configure_harness` when `harness_configured: false`; Wizard Mode executes `configure_harness` as part of setup completion; Health Check includes `check-harness` status. Documented in `marshall-steward/SKILL.md` and reference flows (`references/wizard-flow.md`, `references/menu-healthcheck.md`), tested in `test_harness_config.py`.

---

## 5. Traceability Matrix

| Plan File | Requirement IDs | Status | Key Landed / Affected Paths |
| :--- | :--- | :--- | :--- |
| `doc/antigravity/done/selective-bundle-installer.md` | `REQ-INST-1..6` | **Merged & Done** (PR `#1663`) | `marketplace/targets/{antigravity,opencode}/emitter.py`, `marketplace/targets/{antigravity,opencode}/templates/install.sh`, `test/marketplace/targets/{antigravity,opencode}/test_emitter.py`, `doc/user/install-{antigravity,opencode}.adoc` |
| `doc/antigravity/done/steward-harness-config.md` | `REQ-STEW-1..4` | **Merged & Done** (PR `#1662`) | `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/{determine_mode.py,configure_harness.py}`, `marketplace/bundles/plan-marshall/skills/marshall-steward/{SKILL.md,references/}`, `test/plan-marshall/marshall-steward/test_harness_config.py` |
| `doc/antigravity/plans/harness-bundles-target-rules.md` | `REQ-HBNDL-1..6` | **Implemented & Verified** (`feature/harness-bundles-target-rules`) | `marketplace/targets/component_targets.py`, `marketplace/targets/{claude,opencode,antigravity}/`, `marketplace/bundles/plan-marshall-{antigravity,opencode}/`, `marketplace/.claude-plugin/marketplace.json`, `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/` |
