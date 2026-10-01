# Plan 3: `marshall-steward` Harness-Aware Preflight & Script-Only Local Harness Configuration (`REQ-STEW-1..4`)

> **Self-Contained Execution Contract**: This plan is completely self-contained. When asked to `implement doc/antigravity/plans/steward-harness-config.md`, read this file at `doc/antigravity/plans/steward-harness-config.md` and execute every stage in order from Stage 1 (Worktree & Branch Setup) through Stage 5 (Verification, PR Lifecycle & Post-Merge Cleanup).

- **Plan Slug**: `steward-harness-config`
- **Branch**: `feature/steward-harness-config`
- **Worktree**: `.plan/local/worktrees/steward-harness-config`
- **Requirements Covered**: `REQ-STEW-1`, `REQ-STEW-2`, `REQ-STEW-3`, `REQ-STEW-4`

---

## 1. Skill Loading & Repository Hard Rules

### 1.1 Step 0 — Load Core & Surface Skills
Before making any changes, load the following skills from the repository bundle tree:
1. `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`
2. `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md`
3. `marketplace/bundles/plan-marshall/skills/persona-implementer/SKILL.md`
4. `marketplace/bundles/pm-dev-python/skills/python-core/SKILL.md`
5. `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md`
6. `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/SKILL.md`

### 1.2 Hard Rules (`AGENTS.md` / `CLAUDE.md`)
- **`.plan/` access via scripts only**: Never use direct file tools (`Read`, `Write`, `Edit`) on `.plan/` paths. Always invoke `python3 .plan/execute-script.py` with `manage-*` scripts. Use `.plan/temp/` for temporary files.
- **One command per shell call**: No `&&`, `;`, `|`, trailing `&`, `$()`, subshells, loops, or heredocs in shell tool calls.
- **No shell file operations**: Never run `ls`, `find`, `cat`, `grep`, or `git grep`. Use dedicated file/search tools or `architecture` script queries.
- **CI & git operations via abstraction**: Route worktree lifecycle, artifact detection, commit formatting, and branch switch/pull through `plan-marshall:workflow-integration-git:git-workflow` (`worktree-create`, `detect-artifacts`, `format-commit`, `switch-and-pull`, `worktree-remove`), use `git -C {worktree_path}` for staging, committing (`-F`), and pushing inside the worktree, and route PR/CI operations through `plan-marshall:tools-integration-ci:ci`.
- **Documentation standards**: No version history, changelogs, dates, or timestamps; document current state only.

---

## 2. Ground-Truth Baseline (`main` + PR `#1646`)

1. **Empirical Target Resolution (`target_context.py` from PR `#1646`)**:
   - `marketplace/bundles/plan-marshall/skills/script-shared/scripts/target_context.py` already implements:
     - `detect_target_from_env()` checking `ANTIGRAVITY_AGENT` $\to$ `'antigravity'`, `OPENCODE` / `OPENCODE_PID` $\to$ `'opencode'`, `CLAUDE_CODE_SESSION_ID` $\to$ `'claude'`.
     - `resolve_target(cwd)` running the 3-tier cascade (`env` $\to$ `marshal_json` `runtime.target` $\to$ `fallback` `default_target()`), returning `ResolvedTarget(target=..., target_source=..., reason=...)`.
     - `resolve_context(target, marketplace_root, cwd)` handling explicit `--target` overrides and validating `marketplace_root`.
   - **Rule**: Do NOT re-implement environment variable target detection in `determine_mode.py` or `configure_harness.py`. Always import and call `resolve_target()` / `resolve_context()` from `target_context` (`script-shared`).
2. **Main-Anchored State Resolution (`marketplace_paths.resolve_main_anchored_path`)**:
   - `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` provides `resolve_main_anchored_path(subpath: str | Path) -> Path` (ADR-002), which resolves paths under the main checkout's `.plan/local/` even when invoked from a linked git worktree under `.plan/local/worktrees/{plan_id}` (while honoring `PLAN_BASE_DIR` / `file_ops.set_base_dir()` in tests).
   - Routing `.plan/local/harness/{harness}.json` through `resolve_main_anchored_path(f'harness/{harness}.json')` (falling back to `get_plan_base_dir() / 'local' / 'harness' / f'{harness}.json'` when outside a git repo) guarantees worktree inheritance automatically without file duplication.
3. **Existing `determine_mode.py` in `marshall-steward`**:
   - Located at `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py`.
   - Currently supports subcommands `mode` and `discover-domains`.
   - `determine_mode()` only checks `(plan_dir / 'execute-script.py').exists()` and `(plan_dir / 'marshal.json').exists()`, returning `mode: menu, reason: both_exist` even when the checkout was initialized under a different harness (e.g., Claude) and has never configured the active harness (e.g., Antigravity or OpenCode).
4. **Existing `platform-runtime` Target Setup Operations**:
   - `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` implements `project_initial_setup` and `project_install_hook` (`.agents/hooks.json`).
   - `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` implements `opencode_enforcement_apply`.

---

## 3. Requirements Specification (`REQ-STEW-1..4`)

### `REQ-STEW-1`: Active Harness Detection & Verification (`determine_mode.py check-harness`)
- Extend `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py` with:
  1. A `check-harness` subcommand accepting optional `--harness {claude,opencode,antigravity}`.
  2. Active harness resolution delegating to `target_context.resolve_target(Path.cwd())` (or `SOURCE_EXPLICIT` when `--harness` is supplied).
  3. Inspection of `.plan/local/harness/{harness}.json` (resolved via `resolve_main_anchored_path(f'harness/{harness}.json')` with non-git fallback to `get_plan_base_dir() / 'local' / 'harness' / f'{harness}.json'`).
  4. Verification of:
     - File existence and valid JSON schema (`schema_version == 1`, `harness == active_harness`, `checks` dict, `dist_manifest_sha` string).
     - `executor_ready`: `checks.get('executor_ready') is True` and `(plan_dir / 'execute-script.py').is_file()`.
     - `harness_paths_valid`: `checks.get('harness_paths_valid') is True` and the resolved harness bundle/skill root exists on disk (returning `configured: false`, `reason: 'harness_paths_invalid'` if false or missing).
     - `dist_manifest_sha` freshness: matches the current SHA-256 of the installed bundle root's `dist-manifest.json` (or SHA-256 of `.plan/execute-script.py` when running from a source checkout without `dist-manifest.json`).
  5. TOON return shape for `check-harness`:
     - When configured and fresh:
       ```toon
       status: success
       harness: antigravity
       target_source: env
       configured: true
       reason: configured
       config_path: /abs/path/to/.plan/local/harness/antigravity.json
       dist_manifest_sha: <sha256>
       ```
     - When unconfigured or stale:
       ```toon
       status: success
       harness: antigravity
       target_source: env
       configured: false
       reason: harness_config_missing | harness_config_invalid | harness_config_stale | harness_paths_invalid | executor_missing
       action_required: configure_harness
       config_path: /abs/path/to/.plan/local/harness/antigravity.json
       ```
  6. Extend `determine_mode()` (`determine_mode.py mode`) output to include `harness`, `target_source`, `harness_configured` (`True`/`False`), and `harness_reason` alongside `mode` (`wizard`/`menu`) and `reason`.

### `REQ-STEW-2`: Local Harness State Schema, Isolation & Worktree Safety
- **Location**: `.plan/local/harness/{harness}.json` (anchored to the main checkout's `.plan/local/harness/` via `resolve_main_anchored_path`).
- **Schema** (strictly no timestamps):
  ```json
  {
    "schema_version": 1,
    "harness": "antigravity",
    "target_source": "env",
    "dist_manifest_sha": "<sha256>",
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
- **Concurrent Multi-Harness Support**: A single checkout can hold `claude.json`, `opencode.json`, and `antigravity.json` simultaneously under `.plan/local/harness/` without collision.
- **Worktree Inheritance**: Because both `determine_mode.py` and `configure_harness.py` resolve `.plan/local/harness/{harness}.json` via `resolve_main_anchored_path` (ADR-002), any linked worktree in `.plan/local/worktrees/{plan_id}` reads the main checkout's harness state directly without dirtying git status.

### `REQ-STEW-3`: Deterministic Script-Only `configure_harness.py`
- Create `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py` (invocable as `python3 .plan/execute-script.py plan-marshall:marshall-steward:configure_harness`).
- **CLI Options**:
  - `--harness {claude,opencode,antigravity}` (optional; defaults to `target_context.resolve_target(Path.cwd())['target']`).
  - `--auto-sandbox-elevation` / `--no-auto-sandbox-elevation` (optional boolean flag for `settings.auto_sandbox_elevation`, defaulting to `False`).
- **Deterministic Execution (Zero LLM Tokens)**:
  1. Resolve active harness via `target_context.resolve_target(Path.cwd())` (or `--harness`).
  2. Check `(plan_dir / 'execute-script.py').is_file()` (`executor_ready`).
  3. Verify harness bundle/skill roots exist (`harness_paths_valid`).
  4. Invoke the target's `platform-runtime` setup hook (`project_initial_setup` / `project_install_hook` from `antigravity_runtime.py` for Antigravity, `opencode_enforcement_apply` from `opencode_runtime.py` for OpenCode, or permission/hook verification for Claude) when applicable, and record `rules_emitted` in `checks`.
  5. Compute `dist_manifest_sha` (SHA-256 of `dist-manifest.json` in the resolved bundle cache root if present, else SHA-256 of `.plan/execute-script.py` if present, else `"unbootstrapped"`).
  6. Write `.plan/local/harness/{harness}.json` atomically (`atomic_write_file`).
  7. Output a concise TOON result:
     ```toon
     status: success
     harness: antigravity
     target_source: env
     configured: true
     config_path: /abs/path/to/.plan/local/harness/antigravity.json
     dist_manifest_sha: <sha256>
     ```

### `REQ-STEW-4`: Integration with `marshall-steward` Lifecycle
- Update `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md`, `standards/wizard-flow.md`, and `standards/healthcheck-flow.md`:
  - **Menu Mode Preflight (`SKILL.md`)**: When `determine_mode.py mode` returns `mode: menu` with `harness_configured: false`, `marshall-steward` automatically invokes `python3 .plan/execute-script.py plan-marshall:marshall-steward:configure_harness` and emits a one-line status confirmation before presenting the menu.
  - **Wizard Mode (`standards/wizard-flow.md`)**: After executor bootstrap and runtime setup, invoke `plan-marshall:marshall-steward:configure_harness` to persist `.plan/local/harness/{harness}.json`.
  - **Health Check (`standards/healthcheck-flow.md`)**: Include `determine_mode.py check-harness` in the health check diagnostic steps.
- Update `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` docstring / constants if needed to list `harness` among the sanctioned `resolve_main_anchored_path` residents.

---

## 4. Concrete Deliverables & Affected Files

### D1: `determine_mode.py` Harness Verification (`check-harness` + `mode` Extension)
- **File**: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py`
- **Changes**:
  - Import `resolve_target` from `target_context` and `resolve_main_anchored_path` from `marketplace_paths`.
  - Implement `resolve_harness_config_path(harness: str) -> Path`, `compute_current_harness_sha(plan_dir: Path) -> str`, and `check_harness(harness_override: str | None = None) -> dict` (verifying `checks.executor_ready`, `checks.harness_paths_valid`, and `dist_manifest_sha`).
  - Add `check-harness` subcommand (`--harness` optional choice `['claude', 'opencode', 'antigravity']`).
  - Extend `determine_mode()` to call `check_harness()` and include `harness`, `target_source`, `harness_configured`, and `harness_reason` in its returned dictionary.

### D2: `configure_harness.py` Deterministic Setup Script
- **File**: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py`
- **Changes**:
  - Implement `configure_harness(harness_override: str | None = None, auto_sandbox_elevation: bool = False) -> dict`.
  - Dispatch the active target's `platform-runtime` setup hook (`project_initial_setup` / `project_install_hook` for Antigravity, `opencode_enforcement_apply` for OpenCode) and record the check outcomes (`rules_emitted`, `harness_paths_valid`, `executor_ready`).
  - Write `.plan/local/harness/{harness}.json` atomically using `atomic_write_file` from `file_ops`.
  - Expose CLI via `safe_main` and `parse_args_with_toon_errors`.

### D3: `marshall-steward` Workflow Documentation Updates
- **Files**:
  - `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md`
  - `marketplace/bundles/plan-marshall/skills/marshall-steward/standards/wizard-flow.md`
  - `marketplace/bundles/plan-marshall/skills/marshall-steward/standards/healthcheck-flow.md`
- **Changes**:
  - Document `determine_mode:check-harness` and `configure_harness` in `SKILL.md` script tables, Menu Mode preflight, Wizard Mode completion, and Health Check flow.

### D4: Unit Test Suite
- **Files**:
  - `test/plan-marshall/marshall-steward/test_determine_mode.py` (extend or add `test_harness_config.py`)
- **Tests to Add**:
  - Test `check_harness()` when `.plan/local/harness/{harness}.json` is missing (`configured: False`, `reason: 'harness_config_missing'`).
  - Test `configure_harness()` invokes the target's `platform-runtime` setup hook, writes valid `.plan/local/harness/{harness}.json` with no timestamps, and `check_harness()` subsequently returns `configured: True`, `reason: 'configured'`.
  - Test `check_harness()` returns `configured: False`, `reason: 'harness_paths_invalid'` when `checks.harness_paths_valid` is `False` or the harness paths are missing.
  - Test `check_harness()` detects staleness (`reason: 'harness_config_stale'`) when `dist_manifest_sha` changes, and `configure_harness()` refreshes it.
  - Test multi-harness coexistence (`claude.json`, `antigravity.json`, `opencode.json` in `.plan/local/harness/`) driven by `ANTIGRAVITY_AGENT=1`, `OPENCODE=1`, and `CLAUDE_CODE_SESSION_ID=test` environment variables via `target_context.resolve_target()`.
  - Test `determine_mode()` includes `harness`, `target_source`, `harness_configured`, and `harness_reason`.
  - Test worktree inheritance via `resolve_main_anchored_path` so a linked worktree sees the main checkout's `.plan/local/harness/{harness}.json`.

---

## 5. Stage-by-Stage Execution Tasks

### Stage 1: Worktree & Branch Setup
- [x] **Task 1.1**: Verify `git status --porcelain` on `main` is completely empty.
- [x] **Task 1.2**: Fetch latest `origin/main` (`git fetch origin main`).
- [x] **Task 1.3**: Set up isolated worktree at `.plan/local/worktrees/steward-harness-config` on branch `feature/steward-harness-config` based on `origin/main` via `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-create --plan-id steward-harness-config --branch feature/steward-harness-config --base origin/main`.
- [x] **Task 1.4**: Push `feature/steward-harness-config` immediately (`git -C .plan/local/worktrees/steward-harness-config push -u origin feature/steward-harness-config`) and verify `.venv` and `.pyprojectx` symlinks exist in the worktree.

### Stage 2: Implement `check-harness` in `determine_mode.py` & `configure_harness.py` (D1, D2)
- [x] **Task 2.1**: Extend `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py` with `check_harness()`, the `check-harness` CLI subcommand, and `harness_configured` fields in `determine_mode()`.
- [x] **Task 2.2**: Create `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py` implementing deterministic `platform-runtime` setup hook invocation and `.plan/local/harness/{harness}.json` creation and update.
- [x] **Task 2.3**: Write unit tests in `test/plan-marshall/marshall-steward/test_harness_config.py` and run `uv run pytest test/plan-marshall/marshall-steward/ -o addopts=""`.
- [x] **Task 2.4**: Run `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"`, stage modified files explicitly, commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git -C {worktree_path} push`.

### Stage 3: Integrate into `marshall-steward` Skill & Standards (D3)
- [x] **Task 3.1**: Update `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md`, `standards/wizard-flow.md`, and `standards/healthcheck-flow.md` to wire `check-harness` and `configure_harness`.
- [x] **Task 3.2**: Regenerate `target/claude` (`python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-claude"`) so `target/claude` stays in sync with `marketplace/bundles/plan-marshall/`.
- [x] **Task 3.3**: Run `quality-gate` (which runs `plugin-doctor` over the updated `SKILL.md` and `standards/*.md` files), confirm 0 issues/errors, stage explicitly, commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git -C {worktree_path} push`.

### Stage 4: Full Verification, Pre-PR Subagent Review, PR Lifecycle & Cleanup
- [x] **Task 4.1**: Run full verification: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"`. Confirm `status: success`, `total_issues: 0`, and `errors: []`.
- [x] **Task 4.2**: Dispatch an independent read-only verification subagent to review `git -C {worktree_path} diff origin/main...HEAD` against `REQ-STEW-1..4`, including a beyond-diff consumer sweep for `determine_mode.py` callers and tests. Fix any findings, re-run `verify`, commit, and push.
- [x] **Task 4.3**: Create PR via `plan-marshall:tools-integration-ci:ci`, monitor CI checks and automated review bots, triage and resolve any review findings, and merge via squash merge / merge queue.
- [x] **Task 4.4**: Switch main repository to `main` and pull via `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull --plan-id steward-harness-config --base main`, tear down worktree `.plan/local/worktrees/steward-harness-config` via `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-remove --plan-id steward-harness-config`, and move `doc/antigravity/plans/steward-harness-config.md` into `doc/antigravity/done/steward-harness-config.md`.
