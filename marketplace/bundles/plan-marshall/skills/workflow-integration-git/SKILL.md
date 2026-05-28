---
name: workflow-integration-git
description: Git commit workflow with conventional commits, artifact cleanup, and optional push
user-invocable: false
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

Author the commit message via the `Write` tool to a `.plan/temp/` file (the path is permission-pre-approved via `Write(.plan/**)` and lives inside the workspace — never `/tmp/`). The message MUST end with the Co-Authored-By trailer:

```
Write(file_path=".plan/temp/{plan_id}-commit-msg.txt", content="{commit_message}\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
```

Then commit using `-F` to read the message from the file — this is one Bash call with no `&&`, no heredoc, no `$(...)` substitution:

```bash
# ONE Bash call — commit reading message from .plan/temp/ file
git -C {worktree_path} commit -F .plan/temp/{plan_id}-commit-msg.txt
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
| `baseline-reconcile` | `--plan-id [--base-branch] [--worktree-path] [--skip-fetch] [--no-emit]` | Mechanical baseline reconciliation for phase-2-refine Step 3d. Resolves the worktree path (from `status.metadata.worktree_path`), fetches `origin/{base_branch}`, lists upstream commits since the captured `worktree_sha`, and runs `git merge-tree` to detect potential conflicts — no working-tree mutation. Each conflicted file becomes a Q-Gate finding under `--source qgate` so the phase-2-refine iterate-to-confidence loop addresses the drift. The LLM-judgement classification step (which upstream commit warrants scope adjustment) stays bundled in the existing phase-2-refine dispatch. `--skip-fetch` bypasses the network round-trip for tests / replay scenarios. |

The `worktree-*` subcommands implement the §9 two-state contract: `--plan-id` is mandatory (these verbs operate on a worktree), and path resolution flows through `manage-status get-worktree-path` so a single plan-id is sufficient — no `--project-dir`, no filesystem layout re-derivation. `worktree-create` is the only verb that materializes a path on disk; it computes `get_worktree_root() / <plan-id>`, runs `git worktree add`, and writes the resolved path back to status metadata so subsequent verbs resolve through the canonical channel.

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
- `--base` (required): Base branch to check out and pull (e.g., `main`).

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

Delete the local feature branch and (in `local_and_remote` mode) the remote-tracking ref `refs/remotes/origin/{head_branch}` after a PR merge. Consolidates the three inline git calls (BC-04, BC-05, BC-06) from `branch-cleanup.md`. An internal `show-ref` guard skips remote-tracking ref deletion when the ref is already absent (Drift 3 resolution).

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

Resolve the persisted worktree path for a plan via `manage-status get-worktree-path`. Returns the absolute path plus an `exists` flag indicating whether the directory is currently materialized. The path is the value of `status.metadata.worktree_path` — set when the plan was created with `--use-worktree` or by a prior `worktree-create` invocation.

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
  --plan-id EXAMPLE-PLAN --branch feature/EXAMPLE-PLAN [--base main]
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

## Canonical invocations

The canonical argparse surface for `git-workflow.py`. The D4 plugin-doctor analyzer
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

### baseline-reconcile

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow baseline-reconcile \
  --plan-id PLAN_ID \
  [--base-branch BRANCH] [--worktree-path ABS_PATH] \
  [--skip-fetch] [--no-emit]
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
