# Plan 2: Harness-Specific Bundles (`plan-marshall-antigravity`, `plan-marshall-opencode`), Bundle-Level Target Scoping & Zero-Token Target Rules (`REQ-HBNDL-1..6`)

> **Self-Contained Execution Contract**: This plan is completely self-contained. When asked to `implement doc/antigravity/plans/harness-bundles-target-rules.md`, read this file at `doc/antigravity/plans/harness-bundles-target-rules.md` and execute every stage in order from Stage 1 (Worktree & Branch Setup) through Stage 6 (Verification, PR Lifecycle & Post-Merge Cleanup).

- **Plan Slug**: `harness-bundles-target-rules`
- **Branch**: `feature/harness-bundles-target-rules`
- **Worktree**: `.plan/local/worktrees/harness-bundles-target-rules`
- **Requirements Covered**: `REQ-HBNDL-1`, `REQ-HBNDL-2`, `REQ-HBNDL-3`, `REQ-HBNDL-4`, `REQ-HBNDL-5`, `REQ-HBNDL-6`

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
7. `marketplace/bundles/plan-marshall/skills/persona-security-expert/SKILL.md`

### 1.2 Hard Rules (`AGENTS.md` / `CLAUDE.md`)
- **`.plan/` access via scripts only**: Never use direct file tools (`Read`, `Write`, `Edit`) on `.plan/` paths. Always invoke `python3 .plan/execute-script.py` with `manage-*` scripts. Use `.plan/temp/` for temporary files.
- **One command per shell call**: No `&&`, `;`, `|`, trailing `&`, `$()`, subshells, loops, or heredocs in shell tool calls.
- **No shell file operations**: Never run `ls`, `find`, `cat`, `grep`, or `git grep`. Use dedicated file/search tools or `architecture` script queries.
- **CI & git operations via abstraction**: Route worktree lifecycle, artifact detection, commit formatting, and branch switch/pull through `plan-marshall:workflow-integration-git:git-workflow` (`worktree-create`, `detect-artifacts`, `format-commit`, `switch-and-pull`, `worktree-remove`), use `git -C {worktree_path}` for staging, committing (`-F`), and pushing inside the worktree, and route PR/CI operations through `plan-marshall:tools-integration-ci:ci`.
- **Documentation standards**: No version history, changelogs, dates, or timestamps; document current state only.

---

## 2. Ground-Truth Baseline (`main` + PR `#1646`)

1. **Component-Level & File-Level Target Scoping (`marketplace/targets/component_targets.py`)**:
   - Currently supports `targets:` YAML frontmatter on individual components (`agents/*.md`, `commands/*.md`, `skills/*/SKILL.md`) and skill-internal `*.md` files (`read_target_scope`, `emits_to`, `excluded_emission_roots`, `validate_component_scopes`).
   - Does **not** yet support bundle-level `"targets": [...]` in `{bundle_dir}/.claude-plugin/plugin.json`.
2. **Target Emitters & `plugin.json` / `marketplace.json` Generation**:
   - `marketplace/targets/claude/target.py`, `marketplace/targets/claude/emitter.py`, `marketplace/targets/claude/equality_check.py`, `marketplace/targets/claude/plugin_json_gen.py`, and `marketplace/targets/claude/marketplace_json_gen.py` assume every bundle in `marketplace/bundles/` ships to `claude`.
   - Note: `PASSTHROUGH_FIELDS` in `marketplace/targets/claude/plugin_json_gen.py` is an explicit allowlist of top-level `plugin.json` keys (`name`, `version`, `description`, `author`, `license`, `homepage`, `repository`, `keywords`, `lspServers`).
   - `marketplace/targets/opencode/emitter.py` and `marketplace/targets/antigravity/emitter.py` iterate all bundles via `iter_bundle_dirs(marketplace_dir, bundles)` without checking bundle-level `"targets"` in `.claude-plugin/plugin.json`.
3. **Plugin-Doctor Target Scope Rule (`_analyze_target_scope.py`)**:
   - `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_target_scope.py` implements rule `targets-scope-invalid` for component frontmatter and skill-internal `*.md` frontmatter, tested in `test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py`.
   - Does not yet inspect `.claude-plugin/plugin.json` for bundle-level `"targets"` or check bundle-to-component scope narrowing.
4. **Architectural Boundaries Established in Prior Work**:
   - Emitter templates (`templates/install.sh`, `templates/user-invocable-command.md`) already live in `marketplace/targets/{antigravity,opencode}/templates/` and stay there.
   - Meta-project developer sync skills (`.agents/skills/sync-antigravity/` and `.claude/skills/sync-plugin-cache/`) remain project-local and are never packaged into consumer bundles.

---

## 3. Requirements Specification (`REQ-HBNDL-1..6`)

### `REQ-HBNDL-1`: Bundle-Level Target Scoping in `component_targets.py` & Target Emitters
- A bundle MAY declare `"targets": [...]` in `{bundle_dir}/.claude-plugin/plugin.json`:
  ```json
  {
    "name": "plan-marshall-antigravity",
    "version": "0.1.0",
    "description": "Antigravity harness operational rules and runtime integration",
    "targets": ["antigravity"]
  }
  ```
- **Semantics & Fail-Closed Validation (`TargetScopeError`)**:
  - **Field absent**: The bundle ships to every component-tree target (`claude`, `opencode`, `antigravity`).
  - **Field present**: Must be a non-empty list of strings (or a single non-empty string). Raises `TargetScopeError` if:
    - `.claude-plugin/plugin.json` is malformed JSON and mentions `"targets"`;
    - `"targets"` is empty (`[]` or `""`), not a string/list of strings, or contains non-string elements (e.g. booleans/numbers);
    - Any target name is not in `registered_target_names()`;
    - The set of targets contains no target in `component_tree_target_names()` (e.g. `["cuioss-review-bot"]` only);
    - Any component (`SKILL.md`, `agents/*.md`, `commands/*.md`) inside the bundle declares a `targets:` frontmatter scope that is not a subset of the bundle's `"targets"` scope (a component may only narrow its enclosing bundle's scope, never widen it).
- **Per-Target Enforcement**:
  - `ClaudeTarget` (`target.py`, `emitter.py`, `equality_check.py`, `marketplace_json_gen.py`, `plugin_json_gen.py`):
    - Add `'targets'` to `PASSTHROUGH_FIELDS` in `plugin_json_gen.py`.
    - Validate bundle scopes for all bundles in `validate_component_scopes(bundle_dir)`.
    - Skip bundles where `bundle_emits_to(bundle_dir, 'claude')` is `False` during `ClaudeTarget.generate()`, `run_equality_check()`, and `build_marketplace_json()` (so `target/claude/.claude-plugin/marketplace.json` only lists bundles emitted to `claude`).
  - `OpenCodeTarget` (`opencode/emitter.py`):
    - Validate bundle scope and skip bundles where `bundle_emits_to(bundle_dir, target_name)` is `False`.
  - `AntigravityTarget` (`antigravity/emitter.py`):
    - Validate bundle scope and skip bundles where `bundle_emits_to(bundle_dir, target_name)` is `False`. Also wire `emits_to()` component-level filtering in `antigravity/emitter.py` so component-level and bundle-level scoping behave identically across all three targets.

### `REQ-HBNDL-2`: `plugin-doctor` Bundle-Level Target Scope Validation
- Extend `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_target_scope.py`:
  - Scan `{bundle_dir}/.claude-plugin/plugin.json` for `"targets"`.
  - Report `RULE_ID = 'targets-scope-invalid'` findings for:
    - `reason: 'targets_empty'` when `"targets"` in `plugin.json` is empty (`[]` or `""`) or non-list/non-string.
    - `reason: 'targets_unknown'` when `"targets"` in `plugin.json` names an unregistered target.
    - `reason: 'targets_contradiction'` when a component (`SKILL.md`, `agents/*.md`, `commands/*.md`) inside a target-scoped bundle declares a `targets:` frontmatter scope containing a target excluded by its enclosing bundle's `plugin.json`.

### `REQ-HBNDL-3`: Harness Bundles (`plan-marshall-antigravity` & `plan-marshall-opencode`)
- Create two new target-scoped bundles under `marketplace/bundles/`:
  1. `marketplace/bundles/plan-marshall-antigravity/`:
     - `.claude-plugin/plugin.json` with `"name": "plan-marshall-antigravity"`, `"targets": ["antigravity"]`, `"skills": []`, `"agents": []`, `"commands": []`.
     - `README.md` documenting the bundle and its skill inventory.
     - `skills/target-rules/SKILL.md` (`user-invocable: false`, `mode: reference`) and `skills/target-rules/standards/antigravity-rules.md`.
  2. `marketplace/bundles/plan-marshall-opencode/`:
     - `.claude-plugin/plugin.json` with `"name": "plan-marshall-opencode"`, `"targets": ["opencode"]`, `"skills": []`, `"agents": []`, `"commands": []`.
     - `README.md` documenting the bundle and its skill inventory.
     - `skills/target-rules/SKILL.md` (`user-invocable: false`, `mode: reference`) and `skills/target-rules/standards/opencode-rules.md`.
- Register both bundles in `marketplace/.claude-plugin/marketplace.json`.

### `REQ-HBNDL-4`: Antigravity Target Rules Content
`marketplace/bundles/plan-marshall-antigravity/skills/target-rules/SKILL.md` and `standards/antigravity-rules.md` must specify:
1. **Antigravity Tool Invariants**: Mapping and usage rules for `run_command`, `view_file`, `write_to_file`, `replace_file_content`, `find_by_name`, `grep_search`, `ask_question`, `manage_task`, `invoke_subagent`, `send_message`, `schedule`, `search_web`, and `read_url_content`.
2. **Terminal Sandbox Discipline**: Run commands sandboxed first (`BypassSandbox: false`); one command per `run_command` call; no `&&`, `;`, `|`, `$()`, subshells, loops, or heredocs.
3. **Reactive Task & Subagent Handling**: Never poll `manage_task status` in a loop; rely on reactive wakeup notifications.
4. **`.plan/` Script-Only Access**: All `.plan/` reads and writes go exclusively through `python3 .plan/execute-script.py`; temporary files go in `.plan/temp/`.
5. **Artifact Isolation**: Keep Antigravity UI artifacts in `<appDataDir>/brain/<conversation-id>/` separate from repository source and `.plan/` state.

### `REQ-HBNDL-5`: OpenCode Target Rules Content
`marketplace/bundles/plan-marshall-opencode/skills/target-rules/SKILL.md` and `standards/opencode-rules.md` must specify:
1. **OpenCode Tool & Permission Invariants**: Usage of OpenCode native tools (`bash`, `read`, `write`, `edit`, `glob`, `grep`, `question`, `task`, `skill`, `webfetch`).
2. **Deployed Flat Layout**: Skills live under `~/.config/opencode/skills/{bundle}-{skill}/` (global) or `.opencode/skills/{bundle}-{skill}/` (workspace) with `metadata.bundle` and `metadata.skill` identity frontmatter.
3. **Command & `.plan/` Discipline**: One command per `bash` call; `.plan/` access exclusively via `python3 .plan/execute-script.py`; temporary files in `.plan/temp/`.

### `REQ-HBNDL-6`: Zero-Token Native Rule Delivery & Fail-Safe Entrypoint References
- Update `marketplace/targets/antigravity/templates/install.sh` (when `--workspace` is used or via `--emit-rules`) to copy the installed `skills/plan-marshall-antigravity-target-rules/standards/antigravity-rules.md` into `<workspace>/.agents/rules/plan-marshall-target-rules.md` when installing into a workspace, so Antigravity loads the rules natively with zero runtime tool calls.
- Update `marketplace/targets/opencode/templates/install.sh` (when `--workspace` is used or via `--emit-rules`) to copy the installed `skills/plan-marshall-opencode-target-rules/standards/opencode-rules.md` into `<workspace>/.opencode/rules/plan-marshall-target-rules.md` when installing into a workspace, so OpenCode loads the rules natively with zero runtime tool calls.
- Ensure `plan-marshall`, `plan-orchestrator`, and `marshall-steward` entrypoint skills do not make unconditional runtime file-read calls to load target rules and proceed normally when optional rule files are absent.

---

## 4. Concrete Deliverables & Affected Files

### D1: Bundle-Level Target Scoping in `marketplace/targets/`
- **Files**:
  - `marketplace/targets/component_targets.py`
  - `marketplace/targets/claude/plugin_json_gen.py`
  - `marketplace/targets/claude/marketplace_json_gen.py`
  - `marketplace/targets/claude/equality_check.py`
  - `marketplace/targets/claude/target.py`
  - `marketplace/targets/opencode/emitter.py`
  - `marketplace/targets/antigravity/emitter.py`
- **Changes**:
  - Implement `read_bundle_target_scope(bundle_dir: Path) -> frozenset[str] | None` and `bundle_emits_to(bundle_dir: Path, target_name: str) -> bool` in `component_targets.py`.
  - Update `validate_component_scopes(bundle_dir: Path)` in `component_targets.py` to also validate the bundle's `.claude-plugin/plugin.json` `"targets"` declaration and verify that any component-level `targets:` declaration inside `bundle_dir` is a subset of the bundle's scope.
  - Filter `bundle_dirs` by `bundle_emits_to(bundle_dir, target_name)` in `ClaudeTarget.generate()`, `run_equality_check()`, `build_marketplace_json()`, `opencode/emitter.py`, and `antigravity/emitter.py`.
  - Wire `emits_to()` component-level filtering in `antigravity/emitter.py` (`_emit_skill`, `_emit_agent`, `_emit_command`) to match `opencode/emitter.py`.

### D2: `plugin-doctor` Bundle Target Scope Analyzer
- **File**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_target_scope.py`
- **Changes**:
  - Add `_scan_bundle_manifest(bundle_dir: Path, registered: frozenset[str] | None) -> tuple[frozenset[str] | None, list[dict]]` that parses `{bundle_dir}/.claude-plugin/plugin.json` using stdlib `json.loads`.
  - Flag `targets_empty` and `targets_unknown` on `.claude-plugin/plugin.json`.
  - Flag `targets_contradiction` when a component inside `bundle_dir` declares `targets:` that widen the bundle's `"targets"`.

### D3: `plan-marshall-antigravity` & `plan-marshall-opencode` Bundles
- **Files**:
  - `marketplace/.claude-plugin/marketplace.json`
  - `marketplace/bundles/plan-marshall-antigravity/.claude-plugin/plugin.json`
  - `marketplace/bundles/plan-marshall-antigravity/README.md`
  - `marketplace/bundles/plan-marshall-antigravity/skills/target-rules/SKILL.md`
  - `marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md`
  - `marketplace/bundles/plan-marshall-opencode/.claude-plugin/plugin.json`
  - `marketplace/bundles/plan-marshall-opencode/README.md`
  - `marketplace/bundles/plan-marshall-opencode/skills/target-rules/SKILL.md`
  - `marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md`
  - `marketplace/targets/antigravity/templates/install.sh` (workspace `.agents/rules/plan-marshall-target-rules.md` emission)
  - `marketplace/targets/opencode/templates/install.sh` (workspace `.opencode/rules/plan-marshall-target-rules.md` emission)

### D4: Unit Tests
- **Files**:
  - `test/marketplace/targets/test_component_targets.py`
  - `test/marketplace/targets/antigravity/test_emitter.py`
  - `test/marketplace/targets/opencode/test_emitter.py`
  - `test/marketplace/targets/claude/test_emitter.py`
  - `test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py`
- **Tests to Add**:
  - Test `read_bundle_target_scope` and `bundle_emits_to` (absent $\to$ emits everywhere; `["antigravity"]` $\to$ emits only to `antigravity`; empty/unknown/contradicting component $\to$ raises `TargetScopeError`).
  - Test mutual exclusivity across targets: generating `claude`, `opencode`, and `antigravity` emits `plan-marshall-antigravity` only to `target/antigravity`, `plan-marshall-opencode` only to `target/opencode`, and neither to `target/claude` (nor `target/claude/.claude-plugin/marketplace.json`).
  - Test workspace rule emission in both `antigravity` (`<workspace>/.agents/rules/plan-marshall-target-rules.md`) and `opencode` (`<workspace>/.opencode/rules/plan-marshall-target-rules.md`) `install.sh` scripts.
  - Test `_analyze_target_scope.py` flags bundle-level `targets_empty`, `targets_unknown`, and bundle-to-component `targets_contradiction`.

### D5: Developer & User Documentation Updates
- **Files**:
  - `doc/developer/antigravity.adoc`
  - `doc/developer/opencode.adoc`
  - `doc/developer/distribution.adoc`
  - `doc/developer/repository-layout.adoc`
  - `doc/user/install-antigravity.adoc`
  - `doc/user/install-opencode.adoc`
- **Changes**:
  - Document `plan-marshall-antigravity` and `plan-marshall-opencode` bundles, bundle-level target scoping in `.claude-plugin/plugin.json`, zero-token workspace rules, tool invariants, and verification.
  - Document workspace target rules emission (`--workspace`, `.agents/rules/plan-marshall-target-rules.md`, `.opencode/rules/plan-marshall-target-rules.md`) in user installation guides.

### D6: Requirements Alignment & Plan Archival
- **Files**:
  - `doc/antigravity/requirements.md`
  - `doc/antigravity/plans/harness-bundles-target-rules.md` -> `doc/antigravity/done/harness-bundles-target-rules.md`
- **Changes**:
  - Thoroughly audit `REQ-HBNDL-1..6` implementation, adapt `doc/antigravity/requirements.md` from Pending to Implemented & Verified with test evidence, and update status overview and traceability matrix.
  - Check off all completed tasks and move plan to `doc/antigravity/done/harness-bundles-target-rules.md`.

---

## 5. Stage-by-Stage Execution Tasks

### Stage 1: Worktree & Branch Setup
- [ ] **Task 1.1**: Verify `git status --porcelain` on `main` is completely empty.
- [ ] **Task 1.2**: Fetch latest `origin/main` (`git fetch origin main`).
- [ ] **Task 1.3**: Set up isolated worktree at `.plan/local/worktrees/harness-bundles-target-rules` on branch `feature/harness-bundles-target-rules` based on `origin/main` via `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-create --plan-id harness-bundles-target-rules --branch feature/harness-bundles-target-rules --base origin/main`.
- [ ] **Task 1.4**: Push `feature/harness-bundles-target-rules` immediately (`git -C .plan/local/worktrees/harness-bundles-target-rules push -u origin feature/harness-bundles-target-rules`) and verify `.venv` and `.pyprojectx` symlinks exist in the worktree.

### Stage 2: Bundle-Level Target Scoping in `marketplace/targets/` & `plugin-doctor` (D1, D2)
- [ ] **Task 2.1**: Implement `read_bundle_target_scope`, `bundle_emits_to`, and bundle-to-component narrowing checks in `marketplace/targets/component_targets.py`.
- [ ] **Task 2.2**: Wire `bundle_emits_to` into `marketplace/targets/claude/{target.py,equality_check.py,marketplace_json_gen.py,plugin_json_gen.py}`, `marketplace/targets/opencode/emitter.py`, and `marketplace/targets/antigravity/emitter.py` (including component-level `emits_to` in `antigravity/emitter.py`).
- [ ] **Task 2.3**: Extend `_analyze_target_scope.py` in `pm-plugin-development:plugin-doctor` to validate bundle-level `"targets"` in `.claude-plugin/plugin.json` and detect bundle-to-component scope contradictions.
- [ ] **Task 2.4**: Add unit tests in `test/marketplace/targets/test_component_targets.py` and `test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py`, and run them via `uv run pytest test/marketplace/targets/test_component_targets.py test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py -o addopts=""`.
- [ ] **Task 2.5**: Run `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"`, stage modified files explicitly, commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git -C {worktree_path} push`.

### Stage 3: Author `plan-marshall-antigravity` & `plan-marshall-opencode` Bundles (D3)
- [ ] **Task 3.1**: Create `marketplace/bundles/plan-marshall-antigravity/` (`.claude-plugin/plugin.json` with `"targets": ["antigravity"]`, `README.md`, `skills/target-rules/SKILL.md`, `skills/target-rules/standards/antigravity-rules.md`).
- [ ] **Task 3.2**: Create `marketplace/bundles/plan-marshall-opencode/` (`.claude-plugin/plugin.json` with `"targets": ["opencode"]`, `README.md`, `skills/target-rules/SKILL.md`, `skills/target-rules/standards/opencode-rules.md`).
- [ ] **Task 3.3**: Register both bundles in `marketplace/.claude-plugin/marketplace.json`, update `marketplace/targets/antigravity/templates/install.sh` to emit `.agents/rules/plan-marshall-target-rules.md` in workspace mode when `plan-marshall-antigravity-target-rules` is present, and update `marketplace/targets/opencode/templates/install.sh` to emit `.opencode/rules/plan-marshall-target-rules.md` in workspace mode when `plan-marshall-opencode-target-rules` is present.
- [ ] **Task 3.4**: Regenerate `target/claude` (`python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate-claude"`) so `target/claude` equality check stays in sync, and test `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate --target all --output .plan/temp/all-targets"`.
- [ ] **Task 3.5**: Add target mutual-exclusivity and workspace rule emission tests in `test/marketplace/targets/{antigravity,opencode,claude}/test_emitter.py` and run them via `uv run pytest`.
- [ ] **Task 3.6**: Run `quality-gate`, stage explicitly, commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git -C {worktree_path} push`.

### Stage 4: Developer & User Documentation, Requirements Alignment (D5, D6)
- [ ] **Task 4.1**: Update developer guides (`doc/developer/antigravity.adoc`, `doc/developer/opencode.adoc`, `doc/developer/distribution.adoc`, `doc/developer/repository-layout.adoc`) for harness bundles and bundle-level target scoping.
- [ ] **Task 4.2**: Update user installation guides (`doc/user/install-antigravity.adoc`, `doc/user/install-opencode.adoc`) documenting workspace rule delivery.
- [ ] **Task 4.3**: Thoroughly verify `REQ-HBNDL-1..6` against the implementation, adapt `doc/antigravity/requirements.md` from Pending to Implemented & Verified with test evidence, and update status overview and traceability matrix.
- [ ] **Task 4.4**: Run `quality-gate`, stage explicitly, commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git -C {worktree_path} push`.

### Stage 5: Full Verification, Pre-PR Subagent Review & PR Lifecycle
- [ ] **Task 5.1**: Run full verification: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"`. Confirm `status: success`, `total_issues: 0`, and `errors: []`.
- [ ] **Task 5.2**: Dispatch an independent read-only verification subagent to review `git -C {worktree_path} diff origin/main...HEAD` against `REQ-HBNDL-1..6`, including a beyond-diff sweep for any hardcoded bundle counts or lists in tests/docs. Fix any findings, re-run `verify`, commit, and push.
- [ ] **Task 5.3**: Create PR via `plan-marshall:tools-integration-ci:ci`, monitor CI checks and automated review bots, triage and resolve any review findings, and merge via squash merge / merge queue.

### Stage 6: Post-Merge Cleanup & Plan Archival
- [ ] **Task 6.1**: Switch main repository to `main` and pull via `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull --plan-id harness-bundles-target-rules --base main`.
- [ ] **Task 6.2**: Tear down worktree `.plan/local/worktrees/harness-bundles-target-rules` via `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-remove --plan-id harness-bundles-target-rules`.
- [ ] **Task 6.3**: Check off all completed tasks in `doc/antigravity/plans/harness-bundles-target-rules.md`, move to `doc/antigravity/done/harness-bundles-target-rules.md` via `git mv`, update the traceability matrix in `doc/antigravity/requirements.md` to reference `doc/antigravity/done/harness-bundles-target-rules.md`, and commit the archival.
