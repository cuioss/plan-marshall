# Process & Execution Blueprint for Antigravity / Multi-Target Plans

This document captures the reusable process, execution, and workflow discipline stripped from the completed `dist-installation` plan. Every self-contained implementation plan under `doc/antigravity/plans/` embeds this workflow contract so each plan can be executed end-to-end from a single prompt (`implement doc/antigravity/plans/{plan-slug}.md`).

---

## 1. Skill Loading & Context Preparation

Before writing code, load the foundational and surface-specific skills from the repository bundle tree:

- **Always load**:
  - `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`
  - `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md`
- **Load conditionally by touched surface**:
  - Production code implementation: `marketplace/bundles/plan-marshall/skills/persona-implementer/SKILL.md`
  - Python production code: `marketplace/bundles/pm-dev-python/skills/python-core/SKILL.md`
  - Python unit/integration tests: `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md`
  - Bundle / `SKILL.md` / `plugin.json` structure: `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/SKILL.md`
  - AsciiDoc (`*.adoc`) documentation: `marketplace/bundles/pm-documents/skills/ref-asciidoc/SKILL.md`
  - Security-sensitive changes (installers, subprocesses, untrusted paths): `marketplace/bundles/plan-marshall/skills/persona-security-expert/SKILL.md`

---

## 2. Repository Hard Rules

1. **`.plan/` Access via Scripts Only**:
   - Never use direct file tools (`Read`, `Write`, `Edit`) on `.plan/` paths.
   - Always use `python3 .plan/execute-script.py` with `manage-*` scripts (e.g., `plan-marshall:manage-files:manage-files`).
   - Exception: `.plan/temp/` is designated for temporary/scratch files.
2. **One Command per Shell Call**:
   - Never chain commands with `&&`, `;`, `|`, or background `&`.
   - Never use `$()`, subshells, shell loops, or heredocs in command calls.
3. **No Shell File Operations**:
   - Never run `ls`, `find`, `cat`, `grep`, or `git grep` in shell commands.
   - Use structured architecture queries (`python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture ...`) or dedicated file/search tools.
4. **CI & Git Operations via Abstraction**:
   - Route worktree lifecycle, artifact detection, commit formatting, branch switch/pull, and ref pruning through `plan-marshall:workflow-integration-git:git-workflow` (`worktree-create`, `detect-artifacts`, `format-commit`, `switch-and-pull`, `worktree-remove`, `prune-local-and-remote-ref`), use `git -C {worktree_path}` for staging, committing (`-F`), and pushing inside the worktree, and route all PR/CI operations through `plan-marshall:tools-integration-ci:ci`.
5. **Documentation Standards**:
   - No version history, changelogs, timestamps, or dates in documentation.
   - Document current state only; cross-reference rather than duplicating.

---

## 3. Stage-by-Stage Execution Lifecycle

### Stage 1: Worktree & Branch Setup
1. **Verify Clean Root Checkout**:
   - Confirm `git status --porcelain` is empty on `main`. Stop and report if dirty.
2. **Fetch, Create Worktree & Push Branch**:
   - Fetch latest `origin/main`: `git fetch origin main`.
   - Provision an isolated git worktree at `.plan/local/worktrees/{slug}` on branch `{branch}` (`feature/{slug}` or `fix/{slug}`) based on `origin/main`:
     ```bash
     python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-create --plan-id {slug} --branch {branch} --base origin/main
     ```
   - **Push immediately before any edits**: `git -C .plan/local/worktrees/{slug} push -u origin {branch}` (remote is the only durable storage).
   - Verify `.venv` and `.pyprojectx` are available in the worktree and `.plan/execute-script.py` resolves cleanly so builds and executor calls run inside `.plan/local/worktrees/{slug}` without re-downloading toolchains.

### Stage 2..N: Iterative Implementation & Commit Discipline
Work through the plan's deliverables in logical stages. For every stage:

1. **Fast Red/Green Test Iteration**:
   - Write or update unit tests covering the stage's deliverables.
   - For rapid single-file test feedback during development:
     ```bash
     uv run pytest {path/to/test_file.py} -o addopts=""
     ```
2. **Per-Commit Quality Gate**:
   - Before every commit, run the quality gate:
     ```bash
     python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"
     ```
   - Note: `quality-gate` auto-fixes files in place via `ruff check --fix` and `ruff format`.
   - Inspect the output and log file (`total_issues: 0` and empty `errors[]`) to confirm `ruff`, `mypy`, `SPDX-header check`, and `plugin-doctor` all pass cleanly.
3. **Explicit Staging (Never `git add -A`)**:
   - Check `git -C {worktree_path} status --porcelain` to verify no stray lockfile churn (e.g., `uv.lock`) or untracked artifacts exist.
   - Stage only the explicit deliverable and test file paths (`git -C {worktree_path} add <path1> <path2>`).
4. **Commit with Mandatory Trailer & Push**:
   - Commit in coherent units using conventional commit subjects (`feat(...): ...`, `fix(...): ...`, `test(...): ...`, `docs(...): ...`) formatted via `plan-marshall:workflow-integration-git:git-workflow format-commit` and the mandatory trailer (no `Generated with` footer):
     ```text
     Co-Authored-By: plan-marshall <noreply@cuioss.de>
     ```
   - Push immediately after every commit:
     ```bash
     git -C {worktree_path} push
     ```

### Final Stage: Full Verification, Pre-PR Self-Review, PR Lifecycle & Cleanup
1. **Full Repository Verification**:
   - Run the complete verification suite (`quality-gate` + `test-compile` + `module-tests`):
     ```bash
     python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"
     ```
   - Confirm `status: success`, `total_issues: 0`, and `errors: []`.
   - When target generators, templates, or bundles are touched, also run target generation verification via the executor:
     ```bash
     python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "generate --target all --output .plan/temp/target-verify"
     ```
2. **Independent Pre-PR Verification Subagent**:
   - Before opening the PR, dispatch a read-only verification subagent (`research` or `self`) with:
     - The plan file path and all requirements (`REQ-*`).
     - The full branch diff (`git -C {worktree_path} diff origin/main...HEAD`).
     - Instructions to verify every deliverable is implemented as specified, covered by tests, free of collateral churn, and swept beyond the diff for stale references (docstrings, CLI help strings, test stubs, `.adoc` docs).
   - Fix any findings identified by the verifier, re-run `verify`, commit, and push.
3. **Pull Request Creation & Review Cycle**:
   - Create the PR targeting `main` via `plan-marshall:tools-integration-ci:ci` with a structured summary of deliverables and verification results.
   - Monitor CI status and automated review bots; triage and resolve any review comments.
   - Merge via squash merge / merge queue once all required checks are green.
4. **Post-Merge Cleanup**:
   - Switch main checkout to `main` and pull latest via `git-workflow`:
     ```bash
     python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull --plan-id {slug} --base main
     ```
   - Tear down the worktree at `.plan/local/worktrees/{slug}` and prune the local/remote feature branch ref:
     ```bash
     python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-remove --plan-id {slug}
     ```
   - Move the completed plan file from `doc/antigravity/plans/` into `doc/antigravity/done/`.
