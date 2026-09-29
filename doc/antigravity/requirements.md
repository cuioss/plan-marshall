# Multi-Target Distribution, Selective Bundle Installation & Harness-Aware Steward Requirements

**Document ID**: `REQ-SPEC-MULTI-TARGET-001`  
**Status**: Ground-Truth Verified against `main` + PR `#1646`  
**Target Harnesses**: Google Antigravity, OpenCode, Claude Code

---

## 1. Ground-Truth Baseline (Already Implemented — Excluded from Scope)

The following capabilities are already implemented on `main` and incoming PR `#1646` (`fix(runtime): align OpenCode layout, target resolution, and fail-closed`) and are **removed from active scope**:

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

---

## 2. Remaining Requirement Area 1: Selective Bundle Installation, Update & Uninstall Lifecycle (`REQ-INST-1..6`)

**Implementation Plan**: `doc/antigravity/plans/selective-bundle-installer.md`

### 2.1 Problem Statement & Ground-Truth Gap
Currently, `marketplace/targets/antigravity/templates/install.sh` and `marketplace/targets/opencode/templates/install.sh` copy all emitted skills, agents, and commands wholesale:
- **Bundle Bloat**: Consumers install all 10 marketplace bundles (Java, Java-CUI, Python, Frontend, Frontend-CUI, OCI, Documents, Plugin-Development, Requirements) even when working on a single-language repository.
- **Component Attribution for Agents & Commands**: While PR `#1646` stamps `metadata.bundle` into every emitted flat `SKILL.md`, emitted `agents/` and `commands/` files also need deterministic bundle attribution in `dist-manifest.json` (or `plugin.json`) so partial bundle installs and selective uninstalls filter `skills/`, `agents/`, and `commands/` accurately.
- **No Update State Preservation**: Re-running `install.sh` overwrites the installation without remembering which bundles were previously selected or backing up on failure.
- **Broken OpenCode Uninstall**: `marketplace/targets/opencode/templates/install.sh` `prune_managed_components()` only globs `plan-marshall-*`, leaving behind all `pm-dev-*`, `pm-documents-*`, `pm-plugin-development-*`, and `pm-requirements-*` skills and commands on `--uninstall`.

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
- **Schema**:
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

### 2.4 Requirements (`REQ-INST-1..6`)
- **`REQ-INST-1` (Bundle Attribution & Dependency Closure)**:
  - Emitters (`antigravity/emitter.py`, `opencode/emitter.py`) or `dist-manifest.json` must record the per-bundle component inventory (`skills`, `agents`, `commands`) alongside `#1646`'s `SKILL.md` `metadata.bundle` block so every emitted file maps deterministically to its owning bundle.
  - `plan-marshall` (and `plan-marshall-{target}` if present) are mandatory. Selecting `pm-dev-java-cui` or `pm-dev-frontend-cui` automatically includes `pm-dev-java` or `pm-dev-frontend`.
- **`REQ-INST-2` (Interactive `/dev/tty` Selection & Python 3 Helper)**:
  - When invoked interactively without bundle selection flags, `install.sh` checks `/dev/tty` (`[ -t 0 ]` or readable `/dev/tty` for `curl ... | bash` pipelines) and presents an interactive selector (`[A]ll (default)`, `[C]ore only`, or comma-separated domain aliases/bundles). When `/dev/tty` is unavailable (headless CI), it defaults to `--all`.
  - JSON parsing, dependency resolution, file filtering, manifest generation, and `plugin.json`/`opencode.json` tailoring are delegated to an embedded Python 3 helper in `install.sh` (stdlib only, no `jq` dependency).
- **`REQ-INST-3` (Non-Interactive CLI Flags)**:
  - Support `--all`, `--core-only`, `-b` / `--bundles <csv>`, and `--without-bundles <csv>` in both Antigravity and OpenCode `install.sh`.
- **`REQ-INST-4` (Persistent Installation Manifest & Manifest Tailoring)**:
  - Write `.install-manifest.json` (Antigravity) / `.plan-marshall-manifest.json` (OpenCode) recording `installed_bundles`, `dist_manifest_sha`, and `managed_files`.
  - Prune Antigravity's installed `plugin.json` (`bundles` array) and OpenCode's `opencode.json` (`agent` map) to reflect only the installed bundles.
- **`REQ-INST-5` (Atomic Update `--update` / `-U`)**:
  - Add `-U` / `--update` to `install.sh`. Reads existing manifest to preserve the prior `installed_bundles` selection (unless overridden by `--bundles`/`--all`/`--core-only`), backs up existing `TARGET_DIR` state to a temporary staging directory, prunes obsolete files from the prior manifest, installs new files, and rolls back on failure.
- **`REQ-INST-6` (Safe & Selective Uninstallation)**:
  - Fix OpenCode `prune_managed_components()` to remove all paths listed in `.plan-marshall-manifest.json`, falling back when no manifest exists to pruning all known bundle prefixes (`plan-marshall-*`, `pm-dev-java-*`, `pm-dev-java-cui-*`, `pm-dev-python-*`, `pm-dev-frontend-*`, `pm-dev-frontend-cui-*`, `pm-dev-oci-*`, `pm-documents-*`, `pm-plugin-development-*`, `pm-requirements-*`) across `skills/`, `agents/`, `commands/` (and singular `skill/`, `agent/`, `command/`) without touching unmanaged user files.
  - Support selective uninstallation (`install.sh --uninstall --bundles <csv>`) that removes only the specified non-core bundles (refusing if a remaining installed child bundle depends on the removed base bundle unless the child is also removed) and updates the manifest and `plugin.json`/`opencode.json`.

---

## 3. Remaining Requirement Area 2: Harness-Specific Bundles & Zero-Token Target Rules (`REQ-HBNDL-1..8`)

**Implementation Plan**: `doc/antigravity/plans/harness-bundles-target-rules.md`

### 3.1 Problem Statement & Ground-Truth Gap
- `marketplace/targets/component_targets.py` supports `targets:` scoping on individual components (`SKILL.md`, `agents/*.md`, `commands/*.md`) and skill-internal `.md` files, but does not yet support bundle-level `"targets": [...]` scoping in `{bundle}/.claude-plugin/plugin.json`.
- Target-specific operational rules for Antigravity and OpenCode are not yet packaged as first-class target-scoped bundles (`plan-marshall-antigravity`, `plan-marshall-opencode`) or delivered into native zero-token rule locations (`.agents/rules/plan-marshall-target-rules.md` for Antigravity, `AGENTS.md` for OpenCode).
- Note on Ground-Truth Boundary: Build-time emitter templates (`templates/install.sh` and `templates/user-invocable-command.md`) are already owned and tested under `marketplace/targets/{target}/templates/` and remain there; meta-project developer sync skills (`.agents/skills/sync-antigravity/` and `.claude/skills/sync-plugin-cache/`) remain project-local.

### 3.2 Requirements (`REQ-HBNDL-1..8`)
- **`REQ-HBNDL-1` (Bundle-Level Target Scoping in `component_targets.py` & Emitters)**:
  - Extend `marketplace/targets/component_targets.py` with `read_bundle_target_scope(bundle_dir: Path) -> frozenset[str] | None` and `bundle_emits_to(bundle_dir: Path, target_name: str) -> bool` reading `"targets"` from `.claude-plugin/plugin.json` with the same fail-closed validation (`TargetScopeError` on unknown target, empty list, non-component-tree-only target, or non-string items).
  - Enforce `bundle_emits_to(bundle_dir, target_name)` across all three component-tree targets (`claude`, `opencode`, `antigravity`), including `ClaudeTarget` equality checks and `marketplace_json_gen.py` so a bundle scoped to `["antigravity"]` is omitted from `target/claude/` and `target/opencode/`.
- **`REQ-HBNDL-2` (`plugin-doctor` Bundle Target Scope Support)**:
  - Update `pm-plugin-development:plugin-doctor` to validate bundle-level `"targets"` in `.claude-plugin/plugin.json` and validate tool declarations inside target-scoped bundles against the target's `mapping.json`.
- **`REQ-HBNDL-3` (Harness Bundles `plan-marshall-antigravity` & `plan-marshall-opencode`)**:
  - Create `marketplace/bundles/plan-marshall-antigravity/` (`"targets": ["antigravity"]`) and `marketplace/bundles/plan-marshall-opencode/` (`"targets": ["opencode"]`), registered in `marketplace/.claude-plugin/marketplace.json`.
  - Each bundle provides `skills/target-rules/SKILL.md` and `standards/harness-rules.md`.
- **`REQ-HBNDL-4` (Antigravity Target Rules Content)**:
  - `plan-marshall-antigravity:target-rules` codifies:
    1. Complete Antigravity tool invariants (`run_command`, `view_file`, `write_to_file`, `replace_file_content`, `find_by_name`, `grep_search`, `ask_question`, `manage_task`, `invoke_subagent`, `send_message`, `schedule`, `search_web`, `read_url_content`).
    2. Terminal sandbox discipline (`BypassSandbox: false` first, one command per call, no `&&`/`;`/`|`/`$()`/heredocs).
    3. Reactive background task & subagent handling (never poll `manage_task status` in a loop).
    4. `.plan/` script-only access via `python3 .plan/execute-script.py`.
    5. Artifact isolation (`<appDataDir>/brain/` artifacts kept separate from repository source and `.plan/` state).
- **`REQ-HBNDL-5` (OpenCode Target Rules Content)**:
  - `plan-marshall-opencode:target-rules` codifies OpenCode tool mappings, singular-to-plural deployed skill resolution (`~/.config/opencode/skills/` / `.opencode/skills/`), one-command-per-call discipline, and `.plan/` script-only access.
- **`REQ-HBNDL-6` (Zero-Token Native Rule Delivery & Fail-Safe Entrypoints)**:
  - Update `install.sh` (workspace mode) and harness setup to emit the active harness's `target-rules` into `.agents/rules/plan-marshall-target-rules.md` (Antigravity) or `.opencode/rules/plan-marshall-target-rules.md` (OpenCode) so rules enter system context with zero runtime `Read`/`view_file` calls.
  - Entrypoint skills (`plan-marshall`, `plan-orchestrator`, `marshall-steward`) rely passively on native agentfiles/rules and never fail if optional rule files are absent.

---

## 4. Remaining Requirement Area 3: `marshall-steward` Harness-Aware Run & Script-Only Local Harness Configuration (`REQ-STEW-1..4`)

**Implementation Plan**: `doc/antigravity/plans/steward-harness-config.md`

### 4.1 Problem Statement & Ground-Truth Gap
- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py` currently checks only whether `.plan/execute-script.py` and `.plan/marshal.json` exist (`mode: menu, reason: both_exist`).
- If a repository was initialized under Claude Code (so `marshal.json` exists) and is later opened in Antigravity or OpenCode (or vice versa), `determine_mode.py` does not check whether the *active* harness (resolved via PR `#1646`'s `target_context.resolve_target()`) has been locally configured on this checkout.
- Per-checkout harness readiness must be tracked in git-ignored `.plan/local/harness/{target}.json` and configured deterministically via Python script (`configure_harness.py`) without burning conversational LLM tokens.

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

### 4.3 Requirements (`REQ-STEW-1..4`)
- **`REQ-STEW-1` (Active Harness Verification via `target_context` in `determine_mode.py`)**:
  - `determine_mode.py` must delegate active target detection to `target_context.resolve_target()` / `target_context.resolve_context()` from `plan-marshall:script-shared` (PR `#1646`), accepting an optional `--harness` (`claude`, `opencode`, `antigravity`) override.
  - Add subcommand `determine_mode.py check-harness [--harness {target}]` that inspects `.plan/local/harness/{target}.json`, verifies schema validity, checks `dist_manifest_sha` freshness against the installed target's `dist-manifest.json` (or `.plan/execute-script.py` SHA fallback), and verifies `checks.executor_ready` and `checks.harness_paths_valid`.
  - Extend `determine_mode.py mode` output with `harness`, `harness_source`, `harness_configured` (`true`/`false`), and `harness_reason` so `marshall-steward` sees harness readiness in a single call.
- **`REQ-STEW-2` (Deterministic Script-Only `configure_harness.py`)**:
  - Create `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py` registered in the executor as `plan-marshall:marshall-steward:configure_harness`.
  - Runs deterministically without LLM prompt interaction:
    1. Resolves active target via `target_context.resolve_context()`.
    2. Invokes the target's existing `platform-runtime` setup hook (`project_initial_setup` / `project_install_hook` for Antigravity, `opencode_enforcement_apply` for OpenCode, or permission/hook check for Claude) when applicable.
    3. Emits/updates `.plan/local/harness/{target}.json` with `dist_manifest_sha` and check results.
    4. Ensures zero git worktree pollution (never writes to tracked files without explicit steward wizard invocation; `.plan/local/harness/` is covered by `.plan/.gitignore`).
- **`REQ-STEW-3` (Worktree Inheritance)**:
  - Update `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git_workflow.py` (`worktree-setup`) so plan worktrees under `.plan/local/worktrees/{plan_id}` inherit `.plan/local/harness/` from the main repository checkout.
- **`REQ-STEW-4` (`marshall-steward` Wizard, Menu Preflight & Health Check Integration)**:
  - Update `marshall-steward/SKILL.md`, `standards/wizard-flow.md`, and `standards/healthcheck-flow.md`:
    - In Menu Mode preflight: when `determine_mode.py mode` reports `harness_configured: false`, automatically run `plan-marshall:marshall-steward:configure_harness` before showing the menu and report a one-line status confirmation.
    - In Wizard Mode: run `configure_harness` as part of initial setup completion.
    - In Health Check Mode: include `check-harness` status in the health report.

---

## 5. Traceability Matrix

| Plan File | Requirement IDs | Target Branch | Key Affected Paths |
| :--- | :--- | :--- | :--- |
| `doc/antigravity/plans/selective-bundle-installer.md` | `REQ-INST-1..6` | `feature/selective-bundle-installer` | `marketplace/targets/{antigravity,opencode}/emitter.py`, `marketplace/targets/{antigravity,opencode}/templates/install.sh`, `test/marketplace/targets/{antigravity,opencode}/test_emitter.py`, `doc/user/install-{antigravity,opencode}.adoc` |
| `doc/antigravity/plans/harness-bundles-target-rules.md` | `REQ-HBNDL-1..6` | `feature/harness-bundles-target-rules` | `marketplace/targets/component_targets.py`, `marketplace/targets/{claude,opencode,antigravity}/`, `marketplace/bundles/plan-marshall-{antigravity,opencode}/`, `marketplace/.claude-plugin/marketplace.json`, `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/` |
| `doc/antigravity/plans/steward-harness-config.md` | `REQ-STEW-1..4` | `feature/steward-harness-config` | `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/{determine_mode.py,configure_harness.py}`, `marketplace/bundles/plan-marshall/skills/marshall-steward/{SKILL.md,standards/}`, `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git_workflow.py` |
