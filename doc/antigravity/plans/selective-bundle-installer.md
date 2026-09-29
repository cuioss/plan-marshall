# Plan 1: Selective Bundle Installation, Atomic Update & Safe Uninstall Lifecycle (`REQ-INST-1..6`)

> **Self-Contained Execution Contract**: This plan is completely self-contained. When asked to `implement doc/antigravity/plans/selective-bundle-installer.md`, read this file at `doc/antigravity/plans/selective-bundle-installer.md` and execute every stage in order from Stage 1 (Worktree & Branch Setup) through Stage 6 (Verification, PR Lifecycle & Post-Merge Cleanup).

- **Plan Slug**: `selective-bundle-installer`
- **Branch**: `feature/selective-bundle-installer`
- **Worktree**: `.plan/local/worktrees/selective-bundle-installer`
- **Requirements Covered**: `REQ-INST-1`, `REQ-INST-2`, `REQ-INST-3`, `REQ-INST-4`, `REQ-INST-5`, `REQ-INST-6`

---

## 1. Skill Loading & Repository Hard Rules

### 1.1 Step 0 — Load Core & Surface Skills
Before making any changes, load the following skills from the repository bundle tree:
1. `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`
2. `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md`
3. `marketplace/bundles/plan-marshall/skills/persona-implementer/SKILL.md`
4. `marketplace/bundles/pm-dev-python/skills/python-core/SKILL.md`
5. `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md`
6. `marketplace/bundles/pm-documents/skills/ref-asciidoc/SKILL.md`
7. `marketplace/bundles/plan-marshall/skills/persona-security-expert/SKILL.md`

### 1.2 Hard Rules (`AGENTS.md` / `CLAUDE.md`)
- **`.plan/` access via scripts only**: Never use direct file tools (`Read`, `Write`, `Edit`) on `.plan/` paths. Always invoke `python3 .plan/execute-script.py` with `manage-*` scripts. Use `.plan/temp/` for temporary files.
- **One command per shell call**: No `&&`, `;`, `|`, trailing `&`, `$()`, subshells, loops, or heredocs in shell tool calls.
- **No shell file operations**: Never run `ls`, `find`, `cat`, `grep`, or `git grep`. Use dedicated file/search tools or `architecture` script queries.
- **CI & git operations via abstraction**: Use `plan-marshall:workflow-integration-git:git-workflow` and `plan-marshall:tools-integration-ci:ci` via the executor.
- **Documentation standards**: No version history, changelogs, dates, or timestamps; document current state only.

---

## 2. Ground-Truth Baseline (`main` + PR `#1646`)

1. **Existing Installer Templates**:
   - `marketplace/targets/antigravity/templates/install.sh` and `marketplace/targets/opencode/templates/install.sh` already exist and are emitted with mode `0o755` into `target/antigravity/install.sh` and `target/opencode/install.sh`.
   - Both currently support `--workspace` (`-w`), `--target-dir PATH`, `--ref REF`, `--uninstall`, and `--help`, and support both local mode and remote tarball download mode (`curl -fsSL ... | bash`).
   - Currently, both copy all emitted skills, agents, and commands wholesale without bundle filtering.
2. **Existing Flat Skill Identity Metadata (PR `#1646`)**:
   - `marketplace/targets/skill_identity.py` (`skill_identity_metadata_lines(bundle, skill_name)`) is called by both `marketplace/targets/antigravity/frontmatter.py` and `marketplace/targets/opencode/frontmatter.py`.
   - Every emitted `SKILL.md` in `target/antigravity/skills/{bundle}-{skill}/SKILL.md` and `target/opencode/skill/{bundle}-{skill}/SKILL.md` carries:
     ```yaml
     metadata:
       bundle: <bundle>
       skill: <skill>
     ```
   - `marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py` reads this via `read_flat_skill_identity(skill_dir)`.
3. **Existing `dist-manifest.json` Emission**:
   - `marketplace/targets/generate.py` emits `dist-manifest.json` at the root of `target/antigravity` and `target/opencode` containing `version`, `source_sha`, `executor_scripts_fingerprint`, `executor_changed_at_version`, `config_seed_fingerprint`, and `config_changed_at_version`.
4. **Current Gap in Component Attribution & Uninstall**:
   - While `SKILL.md` files carry `metadata.bundle`, emitted `agents/*.md` and `commands/*.md` (and Antigravity `plugin.json` / OpenCode `opencode.json`) do not record a per-bundle component map (`bundle_components`) showing which `skills/`, `agents/`, and `commands/` files belong to each bundle.
   - In `marketplace/targets/opencode/templates/install.sh`, `prune_managed_components()` only globs `plan-marshall-*` under `skills/`, `agents/`, and `commands/`, leaving all `pm-dev-*`, `pm-documents-*`, `pm-plugin-development-*`, and `pm-requirements-*` entries behind on `--uninstall`.

---

## 3. Requirements Specification (`REQ-INST-1..6`)

### `REQ-INST-1`: Core vs. Domain Module Separation, Bundle Attribution & Dependency Closure
- **Mandatory Core**: `plan-marshall` (plus target harness bundle `plan-marshall-antigravity` or `plan-marshall-opencode` when present in the emitted distribution) is always installed and cannot be excluded.
- **Selectable Domain Bundles**:
  - `pm-dev-java`: Core Java, JUnit 5, CDI/Quarkus, ArchUnit gate, Maven profiles.
  - `pm-dev-java-cui`: CUI Java standards (CuiLogger, OpenRewrite, CUI HTTP). *Requires `pm-dev-java`.*
  - `pm-dev-python`: Python 3.10+, pytest, pyprojectx, import-linter gate.
  - `pm-dev-frontend`: JavaScript/TypeScript, CSS, Lit, ESLint, Jest, JS arch gate.
  - `pm-dev-frontend-cui`: CUI JavaScript/Maven integration. *Requires `pm-dev-frontend`.*
  - `pm-dev-oci`: OCI container standards and security.
  - `pm-documents`: AsciiDoc, documentation and diagram verification.
  - `pm-plugin-development`: Marketplace plugin creation, doctor, maintenance.
  - `pm-requirements`: Requirements engineering and traceability.
- **Dependency Closure**:
  - Selecting `pm-dev-java-cui` automatically adds `pm-dev-java`.
  - Selecting `pm-dev-frontend-cui` automatically adds `pm-dev-frontend`.
- **Group Aliases**:
  - `all`: All bundles present in the distribution.
  - `core`: Mandatory core (`plan-marshall` + target harness bundle if present).
  - `java`: `pm-dev-java`, `pm-dev-java-cui`
  - `python`: `pm-dev-python`
  - `frontend`: `pm-dev-frontend`, `pm-dev-frontend-cui`
  - `oci`: `pm-dev-oci`
  - `docs`: `pm-documents`
  - `reqs`: `pm-requirements`
  - `plugin-dev`: `pm-plugin-development`
- **Deterministic Bundle-to-Component Mapping**:
  - Both `antigravity/emitter.py` and `opencode/emitter.py` must emit a `bundle-components.json` (or `bundle_components` map in `plugin.json` / `opencode.json`) mapping each emitted `bundle_name` to its relative emitted paths:
    ```json
    {
      "plan-marshall": {
        "skills": ["skills/plan-marshall-plan-marshall", "..."],
        "agents": ["agents/plan-marshall-execution-context.md", "..."],
        "commands": ["commands/plan-marshall-plan-marshall.md", "..."]
      }
    }
    ```
    (Note: for OpenCode, the emitter writes singular `skill/`, `agent/`, `command/` paths; the installer maps them to plural `skills/`, `agents/`, `commands/` in the destination).

### `REQ-INST-2`: Interactive Selection Interface & `/dev/tty` Stdin Robustness
- When invoked interactively without bundle flags (`--all`, `--core-only`, `--bundles`, `--without-bundles`, `--update`, `--uninstall`), `install.sh` checks if interactive input is available:
  - If `[ -t 0 ]` or if `/dev/tty` is readable (`( : </dev/tty ) 2>/dev/null`), prompt the user via `/dev/tty` with:
    - `Core: plan-marshall [MANDATORY]`
    - Available domain aliases (`java`, `python`, `frontend`, `oci`, `docs`, `reqs`, `plugin-dev`)
    - Prompt: `[A]ll (default), [C]ore only, or comma-separated bundles/aliases:`
  - If neither `FD 0` is a TTY nor `/dev/tty` is available (headless CI/container), default non-interactively to `--all`.
- Delegate JSON parsing, alias expansion, dependency closure, file copying/pruning, manifest creation, and `plugin.json`/`opencode.json` tailoring to an embedded Python 3 helper in `install.sh` (stdlib only; no `jq` dependency).

### `REQ-INST-3`: Non-Interactive CLI Flags
Support the following CLI flags in both `marketplace/targets/antigravity/templates/install.sh` and `marketplace/targets/opencode/templates/install.sh`:
- `--all`: Install core + all domain bundles.
- `--core-only`: Install only mandatory core (`plan-marshall` + target harness bundle if present).
- `-b, --bundles <csv>`: Comma-separated list of bundle names or aliases (e.g. `--bundles python,docs` or `--bundles pm-dev-python`). Unknown bundle or alias names must fail closed with exit code 2 and a clear error message.
- `--without-bundles <csv>`: Exclude specific domain bundles/aliases from the full set. Attempting to exclude `plan-marshall` (or a base bundle while keeping its dependent child bundle without also excluding the child) must either fail closed or exclude the dependent child with a clear diagnostic.

### `REQ-INST-4`: Persistent Installation Manifest & Manifest Tailoring
- Write an installation manifest to:
  - Antigravity: `${TARGET_DIR}/.install-manifest.json`
  - OpenCode: `${TARGET_DIR}/.plan-marshall-manifest.json`
- **Schema** (no timestamps):
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
      "agents/plan-marshall-execution-context.md",
      "commands/plan-marshall-plan-marshall.md"
    ]
  }
  ```
- **Target Config Tailoring**:
  - **Antigravity**: Rewrite `${TARGET_DIR}/plugin.json` so `"bundles"` lists only `installed_bundles`.
  - **OpenCode**: When writing `${TARGET_DIR}/opencode.json` (if managed/present), filter `"agent"` entries to only agents belonging to `installed_bundles`.

### `REQ-INST-5`: Atomic Update Mechanism (`-U, --update`)
- Support `-U` / `--update` in both `install.sh` scripts:
  1. Read existing `.install-manifest.json` / `.plan-marshall-manifest.json` in `TARGET_DIR`.
  2. If present and no explicit `--bundles` / `--all` / `--core-only` flag was passed on the `--update` command line, reuse `installed_bundles` from the existing manifest. If no prior manifest exists, fall back to `--all`.
  3. Create a temporary backup snapshot of existing managed files in `TARGET_DIR`.
  4. Remove obsolete files listed in the old manifest's `managed_files` that are no longer part of the new installation set.
  5. Copy the new selected bundle files and write the updated manifest.
  6. If any step fails, restore `TARGET_DIR` from the backup snapshot and exit non-zero.

### `REQ-INST-6`: Re-Engineered Safe & Selective Uninstallation
- **Full Uninstall (`--uninstall` without `--bundles`)**:
  - **Antigravity**: Remove `TARGET_DIR` if it exists (current behavior preserved).
  - **OpenCode**: Read `.plan-marshall-manifest.json` if present and remove every file in `managed_files` plus empty parent skill directories and `.plan-marshall-manifest.json`. In addition (or when no manifest exists), prune all entries matching any known marketplace bundle prefix (`plan-marshall-*`, `pm-dev-java-*`, `pm-dev-java-cui-*`, `pm-dev-python-*`, `pm-dev-frontend-*`, `pm-dev-frontend-cui-*`, `pm-dev-oci-*`, `pm-documents-*`, `pm-plugin-development-*`, `pm-requirements-*`) across both plural (`skills/`, `agents/`, `commands/`) and singular (`skill/`, `agent/`, `command/`) directories. Never delete non-plan-marshall user files.
- **Selective Uninstall (`--uninstall --bundles <csv>`)**:
  - Refuse to uninstall `plan-marshall` (core).
  - Refuse to uninstall a base bundle (`pm-dev-java` or `pm-dev-frontend`) if its dependent child (`pm-dev-java-cui` or `pm-dev-frontend-cui`) remains in `installed_bundles` and was not included in the `--bundles` removal list.
  - Remove all managed files belonging to the specified bundles, remove empty skill directories, update `installed_bundles` and `managed_files` in `.install-manifest.json` / `.plan-marshall-manifest.json`, and prune `plugin.json` (`bundles`).

---

## 4. Concrete Deliverables & Affected Files

### D1: Emitter Bundle-Component Inventory (`bundle-components.json`)
- **Files**:
  - `marketplace/targets/antigravity/emitter.py`
  - `marketplace/targets/opencode/emitter.py`
- **Changes**:
  - Track per-bundle emitted relative paths (`skills`, `agents`, `commands`) during `emit_bundles()`.
  - Emit `bundle-components.json` at `output_dir / 'bundle-components.json'` (and include it in `written` so `_prune_stale_outputs` and manifest hashing cover it) with schema:
    ```json
    {
      "schema_version": 1,
      "target": "antigravity",
      "bundles": {
        "plan-marshall": {
          "skills": ["skills/plan-marshall-plan-marshall", ...],
          "agents": ["agents/plan-marshall-execution-context.md", ...],
          "commands": ["commands/plan-marshall-plan-marshall.md", ...]
        }
      }
    }
    ```
  - For OpenCode, record the emitted relative paths (`skill/{bundle}-{skill}`, `agent/{name}.md`, `command/{name}.md`); the OpenCode installer maps leading `skill/` $\to$ `skills/`, `agent/` $\to$ `agents/`, `command/` $\to$ `commands/`.

### D2: Antigravity `install.sh` Selective Bundle, Update & Manifest Lifecycle
- **File**: `marketplace/targets/antigravity/templates/install.sh`
- **Changes**:
  - Add CLI flags: `--all`, `--core-only`, `-b`/`--bundles <csv>`, `--without-bundles <csv>`, `-U`/`--update`.
  - Add interactive `/dev/tty` bundle prompt when run without bundle flags and TTY is available.
  - Embed a self-contained Python 3 helper function that:
    - Resolves bundle aliases (`all`, `core`, `java`, `python`, `frontend`, `oci`, `docs`, `reqs`, `plugin-dev`) and validates bundle names against `bundle-components.json` (or fallback `SKILL.md` `metadata.bundle` scan).
    - Computes dependency closure (`pm-dev-java-cui` $\to$ `pm-dev-java`, `pm-dev-frontend-cui` $\to$ `pm-dev-frontend`) and enforces mandatory `plan-marshall` (plus `plan-marshall-antigravity` if present).
    - Supports `--update` (reading prior `.install-manifest.json` bundle selection if no new bundle flags were given, staging a backup, pruning removed files, rolling back on error).
    - Copies only the selected bundles' skills, agents, and commands into `TARGET_DIR`.
    - Prunes `TARGET_DIR/plugin.json` `"bundles"` list to `installed_bundles`.
    - Computes `dist_manifest_sha` (SHA-256 of `dist-manifest.json` if present, else `"unknown"`) and writes `TARGET_DIR/.install-manifest.json`.
    - Handles `--uninstall --bundles <csv>` for selective bundle removal.

### D3: OpenCode `install.sh` Selective Bundle, Update, Manifest & Fixed Uninstall Lifecycle
- **File**: `marketplace/targets/opencode/templates/install.sh`
- **Changes**:
  - Add the same CLI flags (`--all`, `--core-only`, `-b`/`--bundles <csv>`, `--without-bundles <csv>`, `-U`/`--update`) and `/dev/tty` interactive selector.
  - Embed the Python 3 helper adapted for OpenCode's singular-to-plural deployment (`skill/` $\to$ `skills/`, `agent/` $\to$ `agents/`, `command/` $\to$ `commands/`) and `${TARGET_DIR}/.plan-marshall-manifest.json`.
  - Fix full `--uninstall` (`prune_managed_components`) to delete all files tracked in `.plan-marshall-manifest.json` plus fallback prefix pruning for all 10 bundle prefixes (`plan-marshall-*`, `pm-dev-*`, `pm-documents-*`, `pm-plugin-development-*`, `pm-requirements-*`) across both plural and singular directories, while leaving non-plan-marshall files untouched.
  - Support selective `--uninstall --bundles <csv>`.

### D4: Unit & Integration Tests
- **Files**:
  - `test/marketplace/targets/antigravity/test_emitter.py`
  - `test/marketplace/targets/opencode/test_emitter.py`
- **Tests to Add**:
  - Verify `bundle-components.json` is emitted and attributes every emitted skill, agent, and command to its bundle.
  - Test `install.sh --core-only` installs only `plan-marshall` (and harness bundle if present), prunes `plugin.json` `bundles`, and writes `.install-manifest.json` / `.plan-marshall-manifest.json`.
  - Test `install.sh --bundles pm-dev-java-cui` automatically pulls in `pm-dev-java` via dependency resolution.
  - Test `install.sh --bundles python,docs` installs `plan-marshall`, `pm-dev-python`, and `pm-documents` only.
  - Test `install.sh --without-bundles java,frontend` excludes Java and Frontend bundles while installing the rest.
  - Test `install.sh --update` preserves the prior `installed_bundles` selection from the manifest and removes obsolete files.
  - Test `install.sh --uninstall --bundles pm-documents` selectively removes `pm-documents` files and updates the manifest while preserving other installed bundles, and refuses removing `pm-dev-java` while `pm-dev-java-cui` remains installed.
  - Test OpenCode `install.sh --uninstall` removes `pm-dev-*`, `pm-documents-*`, `pm-plugin-development-*`, and `pm-requirements-*` components while preserving third-party user skills (e.g. `skills/my-custom-skill/SKILL.md`).

### D5: User Installation Documentation
- **Files**:
  - `doc/user/install-antigravity.adoc`
  - `doc/user/install-opencode.adoc`
- **Changes**:
  - Document selective bundle installation (`--core-only`, `--bundles`, `--without-bundles`, group aliases), interactive selection, `--update`, and selective `--uninstall --bundles`.

---

## 5. Stage-by-Stage Execution Tasks

### Stage 1: Worktree & Branch Setup
- [ ] **Task 1.1**: Verify `git status --porcelain` on `main` is completely empty.
- [ ] **Task 1.2**: Fetch latest `origin/main` (`git fetch origin main`).
- [ ] **Task 1.3**: Create branch `feature/selective-bundle-installer` from `origin/main` and push immediately to `origin` (`git push -u origin feature/selective-bundle-installer`).
- [ ] **Task 1.4**: Set up isolated worktree at `.plan/local/worktrees/selective-bundle-installer` via `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-setup --plan-id selective-bundle-installer --branch feature/selective-bundle-installer` (ensuring `.venv` and `.pyprojectx` symlinks exist in the worktree).

### Stage 2: Emitter `bundle-components.json` Attribution (D1)
- [ ] **Task 2.1**: Update `marketplace/targets/antigravity/emitter.py` to collect per-bundle emitted relative paths (`skills`, `agents`, `commands`) and write `bundle-components.json` at `output_dir / 'bundle-components.json'`.
- [ ] **Task 2.2**: Update `marketplace/targets/opencode/emitter.py` to collect per-bundle emitted relative paths (`skills`, `agents`, `commands`) and write `bundle-components.json` at `output_dir / 'bundle-components.json'`.
- [ ] **Task 2.3**: Run fast pytest check on emitter tests (`uv run pytest test/marketplace/targets/antigravity/test_emitter.py test/marketplace/targets/opencode/test_emitter.py -o addopts=""`).
- [ ] **Task 2.4**: Run `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"`, verify 0 issues/errors, stage modified files explicitly (`git add`), commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git push`.

### Stage 3: Antigravity & OpenCode `install.sh` Lifecycle Upgrade (D2, D3)
- [ ] **Task 3.1**: Implement selective bundle flags (`--all`, `--core-only`, `-b`/`--bundles`, `--without-bundles`, `-U`/`--update`), `/dev/tty` interactive prompt, dependency closure (`pm-dev-java-cui` $\to$ `pm-dev-java`, `pm-dev-frontend-cui` $\to$ `pm-dev-frontend`), `.install-manifest.json` generation, `plugin.json` pruning, atomic update backup/rollback, and selective `--uninstall --bundles` in `marketplace/targets/antigravity/templates/install.sh`.
- [ ] **Task 3.2**: Implement the matching selective bundle flags, `/dev/tty` prompt, dependency closure, `.plan-marshall-manifest.json` generation, atomic `--update`, selective `--uninstall --bundles`, and fixed full `--uninstall` (`prune_managed_components` covering manifest + all `plan-marshall-*` and `pm-*` prefixes while preserving user files) in `marketplace/targets/opencode/templates/install.sh`.
- [ ] **Task 3.3**: Verify shell syntax with `bash -n` on both templates and run target generation (`./pw generate --target antigravity --output .plan/temp/ag-test` and `./pw generate --target opencode --output .plan/temp/oc-test`).
- [ ] **Task 3.4**: Run `quality-gate`, stage explicitly, commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git push`.

### Stage 4: Comprehensive Test Suite (D4)
- [ ] **Task 4.1**: Add unit/integration tests in `test/marketplace/targets/antigravity/test_emitter.py` covering `bundle-components.json`, `--core-only`, `--bundles` with alias and dependency resolution (`pm-dev-java-cui` $\to$ `pm-dev-java`), `--without-bundles`, `.install-manifest.json`, `plugin.json` pruning, `--update`, and selective `--uninstall --bundles`.
- [ ] **Task 4.2**: Add unit/integration tests in `test/marketplace/targets/opencode/test_emitter.py` covering `bundle-components.json`, `--core-only`, `--bundles`, `--without-bundles`, `.plan-marshall-manifest.json`, `--update`, selective `--uninstall --bundles`, and full `--uninstall` pruning all `pm-*` domain bundles while leaving custom user skills intact.
- [ ] **Task 4.3**: Run `uv run pytest test/marketplace/targets/antigravity/test_emitter.py test/marketplace/targets/opencode/test_emitter.py -o addopts=""` and confirm all tests pass.
- [ ] **Task 4.4**: Run `quality-gate`, stage explicitly, commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git push`.

### Stage 5: Documentation Updates (D5)
- [ ] **Task 5.1**: Update `doc/user/install-antigravity.adoc` and `doc/user/install-opencode.adoc` to document `--core-only`, `--bundles`, `--without-bundles`, bundle aliases, interactive selection, `--update`, and selective `--uninstall --bundles`.
- [ ] **Task 5.2**: Run `quality-gate`, stage explicitly, commit with trailer `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, and `git push`.

### Stage 6: Full Verification, Pre-PR Subagent Review, PR Lifecycle & Cleanup
- [ ] **Task 6.1**: Run full verification: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"`. Confirm `status: success`, `total_issues: 0`, and `errors: []`.
- [ ] **Task 6.2**: Dispatch an independent read-only verification subagent to review `git diff origin/main...HEAD` against `REQ-INST-1..6` and sweep beyond the diff for any stale claims or unreferenced constants. Fix any findings, re-run `verify`, commit, and push.
- [ ] **Task 6.3**: Create PR via `plan-marshall:tools-integration-ci:ci`, monitor CI checks and automated review bots, triage and resolve any review findings, and merge via squash merge / merge queue.
- [ ] **Task 6.4**: Switch main repository to `main`, run `git pull origin main`, tear down worktree `.plan/local/worktrees/selective-bundle-installer`, and move `doc/antigravity/plans/selective-bundle-installer.md` into `doc/antigravity/done/selective-bundle-installer.md` via `manage-files` (and `git rm doc/antigravity/plans/selective-bundle-installer.md`).
