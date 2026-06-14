---
name: workflow-integration-git
description: Git commit workflow with conventional commits, artifact cleanup, and optional push
user-invocable: false
mode: workflow
---

# Git Workflow Skill

Provides git commit workflow following conventional commits specification. Includes artifact cleanup, commit formatting, and optional push.

## Enforcement

**Execution mode**: Execute git commit workflow steps sequentially, delegating to script for artifact cleanup and commit formatting.

**Prohibited actions:**
- Never commit secrets, credentials, or `.env` files
- Never skip artifact cleanup step before committing (LLM must call detect-artifacts and act on results — the script detects but does not delete)
- Never run raw `git <subcommand>` that relies on the current working directory.

**Constraints:**
- Commit messages must follow conventional commits format: `<type>(<scope>): <subject>` — see `standards/git-commit-standards.md` for types, rules, and examples
- Push only when explicitly requested via parameters
- All git invocations MUST use `git -C {worktree_path} <subcommand>`. `{worktree_path}` is resolved from `status.metadata.worktree_path` in Step 0 of the Commit Changes workflow. See `standards/worktree-handling.md` for the worktree-specific application of this rule.
- Temp files MUST be written under `.plan/temp/` per project policy — never `/tmp/`.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `message` | string | no | auto-generate from diff | Custom commit message |
| `push` | bool | no | false | Push to remote after committing |

## Prerequisites

No external `Skill:` dependencies. Script imports `triage_helpers` from `ref-toon-format` at runtime (see `ref-workflow-architecture` → "Shared Infrastructure").

## Architecture

```
workflow-integration-git (git commit workflow)
  └─> triage_helpers (ref-toon-format) — error handling, TOON serialization
```

## Usage Examples

```bash
# Format a commit message
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow format-commit \
  --type feat --scope auth --subject "add login flow"

# Analyze a worktree diff for commit suggestions
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff --plan-id {plan_id}
# or with explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff --project-dir {worktree_path}

# Detect artifacts before committing
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow detect-artifacts
```

## Workflow: Commit Changes

**Purpose:** Commit all uncommitted changes following Git Commit Standards.

**Input Parameters:**
- **message** (optional): Custom commit message
- **push** (optional): Push after committing

### Steps

**Step 0: Resolve Worktree Path**

Read the active worktree path from plan status metadata. Every subsequent git call binds to this path via `git -C`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field worktree_path
```

Use the returned `value` as `{worktree_path}` throughout the rest of the workflow. If the field is absent (non-plan context), use the repository root resolved by the caller and still prefix every git call with `git -C <root>` — never rely on the agent's cwd.

**Step 1: Verify Commit Standards**
Use the quick reference above. For edge cases (breaking changes, multi-footer, scope guidelines), read `standards/git-commit-standards.md`.

**Step 2: Check for Uncommitted Changes**
```bash
git -C {worktree_path} status --porcelain
```

If no changes → Report "No changes to commit"

**Step 3: Clean Artifacts**

Detect artifacts using the script:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow detect-artifacts [--root <repo-root>]
```

The script returns `safe` (auto-deletable) and `uncertain` (needs confirmation) lists. Pattern definitions are in `standards/artifact-patterns.json`. The script respects `.gitignore` by default — gitignored files are excluded since they cannot be accidentally committed. Tracked files never appear in `safe`; they are always routed to `uncertain` so the caller must confirm before deletion. For safe artifacts, delete them. For uncertain artifacts, ask user via `AskUserQuestion`.

**Step 4: Generate Commit Message**

If custom message provided:
- Validate format
- Use provided message

If no message:
- Capture and analyze the diff in a single call (the script runs `git -C {worktree_path} diff [--cached]` internally — no temp file required):

  ```bash
  python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff \
    --plan-id {plan_id} [--cached]
  # or with explicit path override:
  python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff \
    --project-dir {worktree_path} [--cached]
  ```
- The script suggests `type` and `scope` but NOT the subject line — compose the subject yourself based on the diff content and the detected type
- If multiple change types are present, use the highest priority: fix > feat > perf > refactor > docs > style > test > chore > ci
- **Scope caveat**: The script infers scope from the first source file's path structure. For changes spanning multiple modules, the detected scope may not be representative — omit scope for cross-cutting changes.

**Step 5: Stage and Commit**

Stage specific files relevant to the logical change (use `git -C {worktree_path} status --porcelain` to review):

```bash
# ONE Bash call — stage files
git -C {worktree_path} add <specific-files>
```

Author the commit message via the `Write` tool to a `.plan/temp/` file (the path is permission-pre-approved via `Write(.plan/**)` and lives inside the workspace — never `/tmp/`). The message MUST end with the Co-Authored-By trailer. BOTH the `Write` and the `git commit -F` MUST use the worktree-absolute `{worktree_path}/.plan/temp/...` path: the harness `Write` tool resolves a relative path against the main checkout while `git -C {worktree_path}` resolves it against the worktree, so a relative-path round-trip would reference two different files and the commit could read a stale message. `{worktree_path}` is already resolved in Step 0, so no new resolution step is required.

```
Write(file_path="{worktree_path}/.plan/temp/{plan_id}-commit-msg.txt", content="{commit_message}\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
```

Then commit using `-F` to read the message from the file — this is one Bash call with no `&&`, no heredoc, no `$(...)` substitution:

```bash
# ONE Bash call — commit reading message from worktree-absolute .plan/temp/ file
git -C {worktree_path} commit -F {worktree_path}/.plan/temp/{plan_id}-commit-msg.txt
```

The `git commit -m "$(cat <<'EOF' … EOF)"` form is forbidden — it combines `$(…)` substitution with a heredoc, both of which trip the Bash safety harness. See `dev-agent-behavior-rules/standards/tool-usage-patterns.md` for the chain-shape and Bash-write rules.

**Step 6: Push (Optional)**

If `push` parameter:
```bash
git -C {worktree_path} push
```

### Output

```toon
status: success
commit_hash: abc123
commit_message: "feat(http): add retry configuration"
files_changed: 5
artifacts_cleaned: 2
pushed: true
```

## Scripts

**Script**: `plan-marshall:workflow-integration-git:git-workflow`

| Command | Parameters | Description |
|---------|------------|-------------|
| `format-commit` | `--type --subject [--scope] [--body] [--breaking] [--footer]` | Format commit message (Co-Authored-By NOT appended — caller adds it at `git commit` time per project convention) |
| `analyze-diff` | `(--plan-id \| --project-dir) [--cached]` | Capture and analyze the worktree diff for commit suggestions. Resolves working tree path from plan metadata when `--plan-id` is used. |
| `detect-artifacts` | `[--root]` | Scan for committable artifacts |
| `force-push-with-lease` | `(--plan-id \| --project-dir --branch)` | Force-push feature branch to origin with `--force-with-lease` guard (post-rebase). Resolves branch and worktree path from plan metadata when `--plan-id` is used. |
| `switch-and-pull` | `(--plan-id \| --project-dir) --base` | Checkout `--base` on the main checkout and pull from origin. Resolves main checkout root from plan metadata when `--plan-id` is used. |
| `prune-local-and-remote-ref` | `(--plan-id \| --project-dir --head) [--mode local_and_remote\|local_only]` | Delete local feature branch and optionally prune the remote-tracking ref after merge. Internal `show-ref` guard skips ref deletion when already absent. Default mode `local_and_remote`; use `local_only` in local-only plans. |
| `worktree-path` | `--plan-id` | Resolve the persisted worktree path via `manage-status get-worktree-path` |
| `worktree-create` | `--plan-id --branch [--base]` | Run `git worktree add` plus project-state bookkeeping (`metadata.use_worktree`/`worktree_path`/`worktree_branch`) |
| `worktree-remove` | `--plan-id [--force]` | Remove the worktree first, then delete the branch ref |
| `worktree-list` | _(none)_ | List plans whose `status.metadata.use_worktree == true` |
| `locate-plan-checkout` | `--plan-id` | Report where a plan's directory currently lives (`current` \| `worktree` \| `not_found`). The `worktree` probe resolves by two paths: the canonical `_resolve_worktree_path_for_plan` (manage-status) channel for not-yet-moved plans, then a structural `get_worktree_root() / {plan_id}` filesystem probe for the moved-in-from-main case (phase-5+, ADR-002). Reuses the uniform cwd walk-up for the current-checkout probe — no inline `git worktree list --porcelain` re-parsing. Used by the cross-session re-entry preflight at the `/plan-marshall` entry sites. |
| `baseline-reconcile` | `--plan-id [--base-branch] [--skip-fetch] [--no-emit]` | Mechanical baseline reconciliation for phase-2-refine Step 3d. Resolves the worktree path (from `status.metadata.worktree_path`), fetches `origin/{base_branch}`, lists upstream commits since the captured `worktree_sha`, and runs `git merge-tree` to detect potential conflicts — no working-tree mutation. Each conflicted file becomes a Q-Gate finding under `--source qgate` so the phase-2-refine iterate-to-confidence loop addresses the drift. The LLM-judgement classification step (which upstream commit warrants scope adjustment) stays bundled in the existing phase-2-refine dispatch. `--skip-fetch` bypasses the network round-trip for tests / replay scenarios. |

**Script**: `plan-marshall:workflow-integration-git:prepare_execute`

| Command | Parameters | Description |
|---------|------------|-------------|
| `prepare` | `--plan-id [--branch] [--base]` | Atomic phase-5 move-in: materializes the worktree (delegating to `worktree-create`), then MOVES the plan directory (`.plan/local/plans/{plan_id}`) from main into its worktree-resident location and GENERATES a worktree-bound executor (`.plan/execute-script.py`) into the worktree — the executor is per-tree derived state, NOT moved; main's copy stays present and untouched. Returns the canonical `worktree_path`. Atomic-with-rollback (a partial-move failure leaves plan state WHOLLY on main), idempotent (already-moved-in → no-op success), and never changes the caller's cwd — the phase-5 orchestrator pins its own cwd to the returned `worktree_path`. `--branch` is required only on first run (when the worktree has not yet been materialized); on re-entry it is ignored. See ADR-002. |

**Script**: `plan-marshall:workflow-integration-git:merge_lock`

| Command | Parameters | Description |
|---------|------------|-------------|
| `acquire` | `--plan-id [--timeout]` | Atomically acquire the single main-anchored merge lock (`.plan/local/merge.lock` on the MAIN checkout, recording the holder `plan-id`). Uses an `O_EXCL` create so concurrent acquirers serialize — exactly one wins, losers retry with simple backoff until the lock frees or `--timeout` (default 30s) elapses. A lock whose recorded holder no longer corresponds to a live plan is reclaimed (re-verified atomically). See ADR-002. |
| `release` | `--plan-id` | Remove the merge lock when this caller is the recorded holder. Idempotent: releasing a lock that is already free, or held by a foreign holder, is a no-op success. |

**Script**: `plan-marshall:workflow-integration-git:integrate_into_main`

| Command | Parameters | Description |
|---------|------------|-------------|
| `integrate` | `--plan-id` | Atomic finalize move-back: in ONE call it ACQUIRES the cooperative merge lock (delegating to `merge_lock`), FOLDS the plan's own global logs into the plan dir, MOVES the plan directory back from the worktree to main, and RELEASES the lock on every exit path. Does NOT regenerate the executor — on-main executor regeneration is the project-level `finalize-step-sync-plugin-cache` step's responsibility (meta-project-only), run after the cache sync. Runs while the worktree is STILL PRESENT (branch cleanup removes the worktree AFTER this returns). Atomic-with-rollback (a partial move-back rolls the plan dir back into the worktree, lock released), idempotent (already-integrated → no-op success). Does NOT change the caller's cwd and does NOT remove the worktree — the finalize orchestrator returns its own cwd to main after the call. See ADR-002. |

The `worktree-*` subcommands implement the §9 two-state contract: `--plan-id` is mandatory (these verbs operate on a worktree), and path resolution flows through `manage-status get-worktree-path` so a single plan-id is sufficient — no `--project-dir`, no filesystem layout re-derivation. `worktree-create` is the only verb that materializes a path on disk; it computes `get_worktree_root() / <plan-id>`, runs `git worktree add`, and writes the resolved path back to status metadata so subsequent verbs resolve through the canonical channel.

**`merge_lock` is the single main-anchored resolver exception (ADR-002).** Every other path resolution in the codebase is uniform cwd-relative (phases 1-4 resolve to main because cwd is main; phase-5+ resolve to the pinned worktree because cwd is pinned there). `merge_lock` — and ONLY `merge_lock` — always resolves `.plan/local/merge.lock` against the MAIN checkout regardless of caller cwd, because cross-session coordination is inherently main-scoped: phase-5+ finalizes each run with cwd pinned to their own worktree, yet they must all contend for one shared lock. It MUST remain the only main-anchored resolver so the codebase cannot regrow a pervasive git-common-dir-style resolution hack. See ADR-002 and `tools-script-executor/standards/cwd-policy.md` (D6).

### format-commit

Format commit message following conventional commits.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow format-commit \
  --type feat \
  --scope http \
  --subject "add retry config" \
  [--body "Extended description..."] \
  [--breaking "API changed"] \
  [--footer "Fixes #123"]
```

**Parameters**:
- `--type` (required): Commit type (feat, fix, docs, style, refactor, perf, test, chore)
- `--subject` (required): Commit subject line
- `--scope`: Optional component scope
- `--body`: Optional commit body
- `--breaking`: Optional breaking change description
- `--footer`: Optional additional footer

**Output** (TOON):
```toon
type: feat
scope: http
subject: add retry config
formatted_message: "feat(http): add retry config"
validation:
  valid: true
  warnings[0]:
status: success
```

### analyze-diff

Capture the worktree diff via `git -C {worktree_path} diff [--cached]` and analyze it to suggest commit message parameters. The script captures the diff in-process; callers no longer need to materialize a temp file.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff \
  --plan-id PLAN_ID [--cached]
# or with explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff \
  --project-dir ABS_PATH [--cached]
```

**Parameters**:
- `--plan-id`: Plan identifier — resolves the worktree path via `manage-status get-worktree-path` (mutually exclusive with `--project-dir`).
- `--project-dir`: Explicit worktree path (escape hatch; mutually exclusive with `--plan-id`).
- `--cached`: Use the staged diff (`git diff --cached`) instead of the unstaged working-tree diff.

**Output** (TOON):
```toon
mode: analysis
suggestions:
  type: feat
  scope: auth
  detected_changes[1]:
    - Significant new code added
  files_changed[1]:
    - src/main/java/auth/Login.java
status: success
```

### detect-artifacts

Scan a directory for build artifacts and temporary files that should not be committed.
Files already covered by `.gitignore` are excluded by default since they cannot be accidentally committed.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow detect-artifacts \
  [--root /path/to/repo] [--no-gitignore]
```

**Parameters**:
- `--root`: Root directory to scan (default: current working directory)
- `--no-gitignore`: Include gitignored files in results (default: respect .gitignore)

**Output** (TOON):
```toon
root: /path/to/repo
safe[2]:
  - src/main/java/Example.class
  - .DS_Store
uncertain[1]:
  - target/classes/Config.class
total: 3
status: success
```

### force-push-with-lease

Push the plan's feature branch to `origin` using `--force-with-lease`, detecting concurrent remote pushes instead of silently overwriting them. The primary path (`--plan-id`) resolves the worktree path and branch name from plan metadata; the escape hatch (`--project-dir` + `--branch`) accepts an explicit path for post-worktree-removal or non-plan contexts.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow force-push-with-lease \
  --plan-id PLAN_ID
# or with explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow force-push-with-lease \
  --project-dir ABS_PATH --branch BRANCH
```

**Parameters**:
- `--plan-id`: Plan identifier — resolves worktree path and branch name via `manage-status get-worktree-path` (mutually exclusive with `--project-dir`).
- `--project-dir`: Explicit worktree path (escape hatch; mutually exclusive with `--plan-id`; requires `--branch`).
- `--branch`: Branch name to push (only with `--project-dir`; resolved from plan metadata when `--plan-id` is used).

**Output** (TOON, success):
```toon
status: success
operation: force-push-with-lease
plan_id: EXAMPLE-PLAN
branch: feature/EXAMPLE-PLAN
remote: origin
remote_sha: abc123def456
```

**Typed errors**:

| `error_type` | Cause |
|-------------|-------|
| `plan_not_found` | `--plan-id` supplied but executor missing, python3 absent, manage-status timed out, or plan resolution failed |
| `worktree_not_materialized` | `worktree_path` or `worktree_branch` absent from manage-status response |
| `missing_required_arg` | Neither `--plan-id` nor `--project-dir` supplied; or `--project-dir` without `--branch` |
| `project_dir_not_a_git_repo` | `--project-dir` path is not a git working tree |
| `branch_not_found` | Branch does not exist locally, or branch is `main`/`master` (force-push to base branch is refused) |
| `push_rejected_non_fast_forward` | `--force-with-lease` lease violation: remote moved since last fetch |
| `lease_check_failed` | Force-with-lease check could not be evaluated |
| `push_failed` | Push exited non-zero for another reason |

### switch-and-pull

Checkout `--base` on the project directory and then pull from `origin` using the explicit form `git pull origin {base_branch}` (never the implicit plain `git pull`). Designed for post-merge cleanup; the primary path (`--plan-id`) derives the main checkout root from `marketplace_paths`; the escape hatch (`--project-dir`) accepts an explicit path.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull \
  --plan-id PLAN_ID --base BASE_BRANCH
# or with explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull \
  --project-dir ABS_PATH --base BASE_BRANCH
```

**Parameters**:
- `--plan-id`: Plan identifier — resolves the main checkout root via `marketplace_paths` (mutually exclusive with `--project-dir`).
- `--project-dir`: Explicit main checkout path (escape hatch; mutually exclusive with `--plan-id`).
- `--base` (required): Base branch to check out and pull (consumer-configured via `project.default_base_branch`; per-plan override via `references.base_branch`).

**Output** (TOON, success):
```toon
status: success
operation: switch-and-pull
plan_id: EXAMPLE-PLAN
base_branch: main
pre_sha: abc123
post_sha: def456
commits_pulled: 3
```

**Typed errors**:

| `error_type` | Cause |
|-------------|-------|
| `plan_not_found` | `--plan-id` supplied but executor missing, python3 absent, manage-status timed out, plan resolution failed, or `marketplace_paths` unavailable |
| `missing_required_arg` | Neither `--plan-id` nor `--project-dir` supplied |
| `project_dir_not_a_git_repo` | `--project-dir` path is not a git working tree |
| `branch_not_found` | `--base` branch not found on remote (`origin/{base}` does not exist) |
| `merge_conflict` | Checkout failed due to uncommitted changes in the current working tree |
| `pull_failed` | `git checkout` or `git pull origin {base}` exited non-zero for another reason |

### prune-local-and-remote-ref

Delete the local feature branch and (in `local_and_remote` mode) the remote-tracking ref `refs/remotes/origin/{head_branch}` after a PR merge. An internal `show-ref` guard skips remote-tracking ref deletion when the ref is already absent.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow prune-local-and-remote-ref \
  --plan-id PLAN_ID [--mode local_and_remote|local_only]
# or with explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow prune-local-and-remote-ref \
  --project-dir ABS_PATH --head HEAD_BRANCH [--mode local_and_remote|local_only]
```

**Parameters**:
- `--plan-id`: Plan identifier — resolves main checkout root and head branch via `manage-status get-worktree-path` (mutually exclusive with `--project-dir`).
- `--project-dir`: Explicit main checkout path (escape hatch; mutually exclusive with `--plan-id`; requires `--head`).
- `--head`: Feature branch name to delete (only with `--project-dir`; resolved from plan metadata when `--plan-id` is used).
- `--mode`: Deletion scope: `local_and_remote` (default) deletes both the local branch and remote-tracking ref; `local_only` skips the remote-tracking ref operation.

**Output** (TOON, success — full deletion):
```toon
status: success
operation: prune-local-and-remote-ref
plan_id: EXAMPLE-PLAN
head_branch: feature/EXAMPLE-PLAN
mode: local_and_remote
local_deleted: true
remote_ref_deleted: true
```

**Output** (TOON, partial — remote-tracking ref was already absent):
```toon
status: partial
operation: prune-local-and-remote-ref
plan_id: EXAMPLE-PLAN
head_branch: feature/EXAMPLE-PLAN
mode: local_and_remote
local_deleted: true
remote_ref_deleted: false
remote_ref_warning: "remote-tracking ref refs/remotes/origin/feature/EXAMPLE-PLAN was already absent — no-op"
```

**Typed errors**:

| `error_type` | Cause |
|-------------|-------|
| `plan_not_found` | `--plan-id` supplied but executor missing, python3 absent, manage-status timed out, plan resolution failed, or `marketplace_paths` unavailable |
| `worktree_not_materialized` | `worktree_branch` absent from manage-status response |
| `missing_required_arg` | Neither `--plan-id` nor `--project-dir` supplied; or `--project-dir` without `--head` |
| `project_dir_not_a_git_repo` | `--project-dir` path is not a git working tree |
| `branch_delete_failed` | Refusing to delete the currently checked-out branch; or `git branch -D` exited non-zero |
| `unexpected_ref_error` | `git update-ref -d` failed after `show-ref` confirmed the ref exists |

### worktree-path

Resolve the persisted worktree path for a plan via `manage-status get-worktree-path`. Returns the absolute path plus an `exists` flag indicating whether the directory is currently materialized. The path is the value of `status.metadata.worktree_path` — populated at phase-5 materialization by `worktree-create` / `prepare` (phases 1-4 record only `use_worktree`, not the path).

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-path \
  --plan-id EXAMPLE-PLAN
```

**Parameters**:
- `--plan-id` (required): Plan identifier. Absence is rejected with `error: plan_resolution_failed` — the worktree subcommands operate on a worktree, so a plan id is mandatory.

**Output** (TOON):
```toon
status: success
plan_id: EXAMPLE-PLAN
worktree_path: /repo/.plan/local/worktrees/EXAMPLE-PLAN
exists: true
```

### worktree-create

Run `git worktree add <resolved-path> <branch>` against the main checkout, set up `.plan/local` and `.plan/execute-script.py` symlinks, best-effort bootstrap pyprojectx, and persist the resolved path/branch via `manage-status metadata --set` so subsequent verbs can resolve through the canonical channel. The path is computed from `get_worktree_root() / <plan-id>`.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-create \
  --plan-id EXAMPLE-PLAN --branch feature/EXAMPLE-PLAN [--base {base_branch}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (mandatory).
- `--branch` (required): Feature branch name to create.
- `--base`: Base ref for the new branch (default: current HEAD).

**Output** (TOON):
```toon
status: success
plan_id: EXAMPLE-PLAN
worktree_path: /repo/.plan/local/worktrees/EXAMPLE-PLAN
branch: feature/EXAMPLE-PLAN
plan_symlink: /repo/.plan/local/worktrees/EXAMPLE-PLAN/.plan
bootstrap: ok
```

### worktree-remove

Remove the worktree (`git worktree remove`) first, then delete the branch ref read from status metadata. Order matters: `git worktree remove` refuses to drop a branch ref that is still checked out, so cleanup is always worktree-first. Branch deletion failures surface as `branch_warning` rather than failing the command — the worktree is gone, branch cleanup is recoverable.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-remove \
  --plan-id EXAMPLE-PLAN [--force]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (mandatory).
- `--force`: Force removal (use only if worktree is clean).

**Output** (TOON, success):
```toon
status: success
plan_id: EXAMPLE-PLAN
worktree_path: /repo/.plan/local/worktrees/EXAMPLE-PLAN
action: removed
branch: feature/EXAMPLE-PLAN
```

### worktree-list

Enumerate plans whose `status.metadata.use_worktree == true`. Reads from `manage-status list`, then resolves each plan's worktree path via `manage-status get-worktree-path`; plans without a configured worktree are silently skipped.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-list
```

**Parameters**: _(none)_

**Output** (TOON):
```toon
status: success
worktrees_root: /repo/.plan/local/worktrees
count: 2
worktrees[2]{plan_id,path,branch}:
  EXAMPLE-PLAN,/repo/.plan/local/worktrees/EXAMPLE-PLAN,feature/EXAMPLE-PLAN
  other,/repo/.plan/local/worktrees/other,feature/other
```

### locate-plan-checkout

Report where a plan's directory currently lives, resolving one of three states without raw `git worktree list --porcelain` re-parsing — it reuses the uniform cwd walk-up (`_find_plan_root_from_cwd`) for the current-checkout probe and resolves the worktree probe by two paths in order: the canonical `_resolve_worktree_path_for_plan` (`manage-status get-worktree-path`) channel, then — when that channel cannot resolve the path — a structural `get_worktree_root() / {plan_id}` filesystem probe. The structural fallback handles the moved-in-from-main case: a plan whose dir was MOVED into its worktree at phase-5 entry (ADR-002) is invisible to the manage-status channel (its `status.json` is no longer on main), so the verb probes the canonical worktree location directly and confirms `status.json` on disk, still returning `location: worktree` when the call is made from main. The verb is read-only and idempotent: a call made from inside the worktree (already cwd-pinned) returns `location: current`, so the cross-session re-entry preflight never double-`cd`s.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow locate-plan-checkout \
  --plan-id EXAMPLE-PLAN
```

**Parameters**:
- `--plan-id` (required): Plan identifier (mandatory — resolves the plan checkout location).

**Resolution states**:
- `current` — the plan directory exists on the current checkout's `.plan/local/plans/{plan_id}/status.json` (covers both main-checkout plans and the already-cwd-pinned-in-worktree case).
- `worktree` — the plan dir lives in its worktree but the current checkout does NOT hold it. Resolved by two paths, tried in order: (1) the canonical `manage-status get-worktree-path` channel, which still succeeds for a not-yet-moved plan whose `status.json` is on main; (2) a structural `get_worktree_root() / {plan_id}` filesystem probe handling the moved-in-from-main case — a phase-5+ plan whose dir was MOVED into its worktree (ADR-002) is invisible to the manage-status channel, so the verb probes `{worktree}/.plan/local/plans/{plan_id}/status.json` directly and confirms it on disk. `worktree_path` is present only in this state.
- `not_found` — neither location holds the plan dir.

**Output** (TOON, plan dir on the current checkout):
```toon
status: success
plan_id: EXAMPLE-PLAN
location: current
```

**Output** (TOON, plan dir moved into a worktree — call made from main):
```toon
status: success
plan_id: EXAMPLE-PLAN
location: worktree
worktree_path: /repo/.plan/local/worktrees/EXAMPLE-PLAN
```

**Output** (TOON, unknown plan):
```toon
status: success
plan_id: EXAMPLE-PLAN
location: not_found
```

### prepare_execute — prepare

Atomic phase-5 move-in (notation `plan-marshall:workflow-integration-git:prepare_execute`). In ONE call it materializes the worktree (delegating to the `worktree-create` machinery so a single code path owns `git worktree add` + `.plan` bookkeeping), then MOVES (not copies) the plan directory (`.plan/local/plans/{plan_id}`) from the main checkout into its worktree-resident location and GENERATES a worktree-bound executor (`.plan/execute-script.py`) into the worktree via `generate_executor --marketplace-root {worktree}`. The executor is per-tree DERIVED state, NOT a moved slot — main's copy stays present and untouched; generation is non-fatal. It returns the canonical `worktree_path`.

**The script does NOT change the caller's cwd** — a subprocess cannot mutate its parent's cwd. It RETURNS `worktree_path`; the phase-5 orchestrator pins ITS OWN cwd to that path for the remainder of phase-5+ (D8 wires the pin). The move is atomic-with-rollback (a partial-move failure rolls back so plan state is left WHOLLY on main, never half-moved, returning `status: error`) and idempotent (an already-moved-in plan returns success returning the same path). The idempotent re-entry is **self-healing**: when the plan dir is already moved in but the worktree executor is absent on disk (the partial-materialization case), the re-entry regenerates/copies the missing executor and returns `action: healed` rather than a bare `action: noop`. See ADR-002 and the TOCTOU mitigation menu in `dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards`.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:prepare_execute prepare \
  --plan-id PLAN_ID --branch BRANCH [--base BASE_REF]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (mandatory).
- `--branch`: Feature branch to create when the worktree has not been materialized yet (required on first run; ignored on re-entry once the worktree exists).
- `--base`: Base ref for the new branch (default: current HEAD).

**Output** (TOON, first run):
```toon
status: success
plan_id: EXAMPLE-PLAN
worktree_path: /repo/.plan/local/worktrees/EXAMPLE-PLAN
action: moved
moved_in[1]:
  - /repo/.plan/local/worktrees/EXAMPLE-PLAN/.plan/local/plans/EXAMPLE-PLAN
worktree_executor_generated: true
executor_detail: "worktree executor generated at /repo/.plan/local/worktrees/EXAMPLE-PLAN/.plan/execute-script.py"
```

**Output** (TOON, re-entry — already moved in, executor present):
```toon
status: success
plan_id: EXAMPLE-PLAN
worktree_path: /repo/.plan/local/worktrees/EXAMPLE-PLAN
action: noop
message: "plan state already moved into worktree"
```

**Output** (TOON, re-entry with missing executor — self-healed): when the plan dir is already moved in but the worktree executor is absent on disk, the re-entry regenerates/copies it and reports the heal:
```toon
status: success
plan_id: EXAMPLE-PLAN
worktree_path: /repo/.plan/local/worktrees/EXAMPLE-PLAN
action: healed
message: "plan state already moved in; regenerated missing worktree executor"
worktree_executor_generated: true
executor_detail: "worktree executor generated at /repo/.plan/local/worktrees/EXAMPLE-PLAN/.plan/execute-script.py"
```

**Typed errors** (all `status: error`, `exit_code: 0`):

| `error_code` | Cause |
|-------------|-------|
| `NOT_FOUND` | Worktree root unresolvable, executor path unresolvable, or the plan directory is absent on the main checkout |
| `INVALID_INPUT` | `--branch` omitted on first run (worktree not yet materialized), or a move-in step failed (rolled back to main) |

### merge_lock — acquire / release

Cooperative merge lock (notation `plan-marshall:workflow-integration-git:merge_lock`) — the SINGLE main-anchored coordination file serializing concurrent `integrate_into_main` (D5) finalizes. One lock file at the MAIN checkout's `.plan/local/merge.lock` records the holder `plan-id`; concurrent finalizes serialize their merge + write-back to main.

**Main-anchored resolution — the single deliberate exception (ADR-002).** This script — and ONLY this script — always resolves its lock file against the MAIN checkout regardless of the caller's cwd, because cross-session coordination is inherently main-scoped (phase-5+ callers run with cwd pinned to their own worktree, yet must all contend for one shared lock). It MUST remain the only main-anchored resolver so the codebase cannot regrow a pervasive git-common-dir-style hack. See ADR-002 and `tools-script-executor/standards/cwd-policy.md` (D6).

**Concurrency correctness.** `acquire` collapses the does-the-lock-exist → create-it check-then-act into a single atomic `os.open(..., O_CREAT | O_EXCL | O_WRONLY)`: two sessions racing to create the path — exactly one wins, the loser gets `EEXIST` and retries with simple backoff. Stale reclamation (a holder whose plan directory no longer exists) is itself a check-then-act and re-verifies atomically: the stale file is removed and the `O_EXCL` create immediately re-attempted, so a third session winning the race in between makes the reclaimer lose cleanly and retry. No fair queue, no elaborate data structure — the lock contents are a single line recording the holder. See the TOCTOU mitigation menu in `dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards`.

`integrate_into_main` (D5) acquires before move-back/merge and releases after, on every exit path.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:merge_lock acquire \
  --plan-id PLAN_ID [--timeout 30]
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:merge_lock release \
  --plan-id PLAN_ID
```

**Parameters**:
- `acquire --plan-id` (required): holder source — the `plan-id` acquiring the lock.
- `acquire --timeout`: max seconds to wait for a held lock to free before returning `TIMEOUT` (default 30).
- `release --plan-id` (required): holder source — removes the lock only when this caller is the recorded holder.

**Output** (TOON, acquire success):
```toon
status: success
plan_id: EXAMPLE-PLAN
action: acquired
lock_path: /repo/.plan/local/merge.lock
holder: EXAMPLE-PLAN
reclaimed: false
```

**Output** (TOON, release):
```toon
status: success
plan_id: EXAMPLE-PLAN
action: released
lock_path: /repo/.plan/local/merge.lock
```

**Typed errors** (all `status: error`, `exit_code: 0`):

| `error_code` | Cause |
|-------------|-------|
| `NOT_FOUND` | The main checkout (and thus the lock path) could not be resolved (not a git repo) |
| `TIMEOUT` | The lock was held by a live holder for the entire `--timeout` budget |
| `INVALID_INPUT` | `release` failed to remove the lock file (filesystem error) |

### integrate_into_main — integrate

Atomic finalize move-back (notation `plan-marshall:workflow-integration-git:integrate_into_main`) — the inverse of `prepare_execute`. In ONE atomic call it ACQUIRES the cooperative merge lock (delegating to `merge_lock`), FOLDS the plan's own global logs into the plan dir's `logs/`, MOVES the plan directory back from the worktree to the main checkout, and RELEASES the lock. It does NOT regenerate the executor.

**Runs while the worktree is STILL PRESENT** — branch cleanup removes the worktree AFTER this script returns. **The script does NOT change the caller's cwd** (a subprocess cannot mutate its parent's cwd) and **does NOT remove the worktree**. It RETURNS a status TOON; the finalize orchestrator returns ITS OWN cwd to main after the call so the uniform cwd rule resumes main resolution for retrospective + archive. The move-back is atomic-with-rollback (a partial move-back rolls the plan dir back into the worktree, leaving the authoritative copy whole, and releases the lock) and idempotent (an already-integrated plan is a no-op success that never acquires the lock). The merge lock is released on EVERY exit path, including rollback. See ADR-002 and the TOCTOU mitigation menu in `dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards`.

**Executor regeneration ownership.** `integrate_into_main` does NOT regenerate the executor. On-main executor regeneration (when a plan changes the marketplace script SET — newly added notations must resolve post-merge) is a project-level, meta-project-only finalize step (`finalize-step-sync-plugin-cache`, run after the cache sync), NOT this script's responsibility. The executor is per-tree DERIVED state (ADR-002): main keeps its copy present throughout phase-5+, each worktree generates its own at move-in, and the on-main copy is refreshed by the cache-sync step. This script only moves the plan dir back under the merge lock.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:integrate_into_main integrate \
  --plan-id PLAN_ID
```

**Parameters**:
- `--plan-id` (required): Plan identifier (mandatory).

**Output** (TOON, success):
```toon
status: success
plan_id: EXAMPLE-PLAN
action: integrated
plan_dir: /repo/.plan/local/plans/EXAMPLE-PLAN
folded_logs[1]:
  - work.log
```

**Output** (TOON, re-entry — already integrated):
```toon
status: success
plan_id: EXAMPLE-PLAN
action: noop
message: "plan state already integrated into main"
```

**Typed errors** (all `status: error`, `exit_code: 0`):

| `error_code` | Cause |
|-------------|-------|
| `NOT_FOUND` | Worktree root unresolvable, or the worktree-resident plan directory is absent (and not already on main) |
| `TIMEOUT` | The merge lock was held by a live holder for the entire wait budget (surfaced verbatim from `merge_lock acquire`) |
| `INVALID_INPUT` | A move-back step failed (rolled back to the worktree, lock released) |

## Canonical invocations

The canonical argparse surface for `git-workflow.py` and the standalone
`prepare_execute.py`, `merge_lock.py`, and `integrate_into_main.py`. The plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `workflow-integration-git` Canonical invocations →
`worktree-create`") instead of restating the command inline. The sibling
`git_provider.py` module exposes shared helpers (`run_git`, provider declarations)
and has no CLI surface — it is not invoked directly.

### format-commit

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow format-commit \
  --type TYPE --subject TEXT \
  [--scope SCOPE] [--body TEXT] [--breaking TEXT] [--footer TEXT]
```

### analyze-diff

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff \
  --plan-id PLAN_ID [--cached]
# or explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff \
  --project-dir ABS_PATH [--cached]
```

### detect-artifacts

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow detect-artifacts \
  [--root DIR] [--no-gitignore]
```

### force-push-with-lease

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow force-push-with-lease \
  --plan-id PLAN_ID
# or explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow force-push-with-lease \
  --project-dir ABS_PATH --branch BRANCH
```

### switch-and-pull

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull \
  --plan-id PLAN_ID --base BASE_BRANCH
# or explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull \
  --project-dir ABS_PATH --base BASE_BRANCH
```

### prune-local-and-remote-ref

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow prune-local-and-remote-ref \
  --plan-id PLAN_ID [--mode local_and_remote|local_only]
# or explicit path override:
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow prune-local-and-remote-ref \
  --project-dir ABS_PATH --head HEAD_BRANCH [--mode local_and_remote|local_only]
```

### worktree-path

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-path \
  --plan-id PLAN_ID
```

### worktree-create

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-create \
  --plan-id PLAN_ID --branch BRANCH \
  [--base BASE_REF]
```

### worktree-remove

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-remove \
  --plan-id PLAN_ID [--force]
```

### worktree-list

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-list
```

### worktree-rebase-to

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-rebase-to \
  --plan-id PLAN_ID --base BASE_REF
```

### locate-plan-checkout

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow locate-plan-checkout \
  --plan-id PLAN_ID
```

### baseline-reconcile

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow baseline-reconcile \
  --plan-id PLAN_ID \
  [--base-branch BRANCH] \
  [--skip-fetch] [--no-emit]
```

### prepare_execute — prepare

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:prepare_execute prepare \
  --plan-id PLAN_ID [--branch BRANCH] [--base BASE_REF]
```

### merge_lock — acquire / release

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:merge_lock acquire \
  --plan-id PLAN_ID [--timeout SECONDS]
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:merge_lock release \
  --plan-id PLAN_ID
```

### integrate_into_main — integrate

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:integrate_into_main integrate \
  --plan-id PLAN_ID
```

## Error Handling

| Failure | Action |
|---------|--------|
| No changes to commit | Report "No changes to commit" and return success (not an error). |
| format-commit validation failure | Report warnings to caller. Do not commit with invalid message. |
| analyze-diff on missing/invalid worktree | Return failure with the path. Caller should pass an existing worktree. |
| Artifact cleanup uncertain | Ask user via `AskUserQuestion` before deleting. Never auto-delete uncertain files. |
| git commit failure (hook rejection, conflict) | Report error with full output. Do not retry automatically. |
| git push failure | Report error. Never force-push as fallback. |
| `worktree-*` invoked without `--plan-id` | argparse rejects with non-zero exit. The verbs operate on a worktree; a plan id is mandatory. |
| `worktree-path`/`worktree-remove` on plan without configured worktree | Return `error: plan_resolution_failed` — `status.metadata.use_worktree` is false or `worktree_path` is unset. |
| `worktree-create` against a path that already exists | Return `error: worktree_exists` with the conflicting path. |
| `worktree-create` `git worktree add` failure | Return `error: worktree_add_failed` with stderr from git. |
| `worktree-create` `.plan` symlink helper rejects a real directory | Return `error: plan_symlink_failed`; the worktree exists but `.plan/local` is a real directory or file (refused so user data is never clobbered). |
| `worktree-remove` worktree is dirty | Return `error: worktree_remove_failed` with hint to verify cleanliness before passing `--force`. |
| `worktree-remove` branch ref delete fails | Return success with `branch_warning` — the worktree is gone, branch cleanup is recoverable. |

## Standards (Load On-Demand)

| Standard | When to Load |
|----------|-------------|
| `standards/worktree-handling.md` | Canonical reference for worktree mechanism: path convention, dispatch protocol, `git -C` rule application, never-edit-main-checkout invariant, cleanup ordering, `--plan-id` two-state contract |
| `standards/git-commit-standards.md` | Edge cases: breaking changes, multi-footer, scope guidelines, anti-patterns |
| `standards/git-commit-config.json` | Adding/updating valid commit types, imperative mood allowlist, or length thresholds |
| `standards/artifact-patterns.json` | Adding/updating artifact detection patterns and cleanup rules |

## Related

See `ref-workflow-architecture` → "Workflow Skill Orchestration" for the full dependency graph and shared infrastructure documentation. Called by: `plan-marshall:workflow-pr-doctor` (commit after fixes), `plan-marshall:phase-6-finalize` (final commit).
