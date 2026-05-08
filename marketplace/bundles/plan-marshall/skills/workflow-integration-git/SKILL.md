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
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow format-commit \
  --type feat --scope auth --subject "add login flow"

# Analyze a worktree diff for commit suggestions
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow analyze-diff --worktree-path {worktree_path}

# Detect artifacts before committing
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow detect-artifacts
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status metadata \
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
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow detect-artifacts [--root <repo-root>]
```

The script returns `safe` (auto-deletable) and `uncertain` (needs confirmation) lists. Pattern definitions are in `standards/artifact-patterns.json`. The script respects `.gitignore` by default — gitignored files are excluded since they cannot be accidentally committed. Tracked files never appear in `safe`; they are always routed to `uncertain` so the caller must confirm before deletion. For safe artifacts, delete them. For uncertain artifacts, ask user via `AskUserQuestion`.

**Step 4: Generate Commit Message**

If custom message provided:
- Validate format
- Use provided message

If no message:
- Capture and analyze the diff in a single call (the script runs `git -C {worktree_path} diff [--cached]` internally — no temp file required):

  ```bash
  python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow analyze-diff \
    --worktree-path {worktree_path} [--cached]
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

The `git commit -m "$(cat <<'EOF' … EOF)"` form is forbidden — it combines `$(…)` substitution with a heredoc, both of which trip the Bash safety harness. See `dev-general-practices/standards/tool-usage-patterns.md` for the chain-shape and Bash-write rules.

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

**Script**: `plan-marshall:workflow-integration-git:git_workflow`

| Command | Parameters | Description |
|---------|------------|-------------|
| `format-commit` | `--type --subject [--scope] [--body] [--breaking] [--footer]` | Format commit message (Co-Authored-By NOT appended — caller adds it at `git commit` time per project convention) |
| `analyze-diff` | `--worktree-path [--cached]` | Capture and analyze the worktree diff for commit suggestions |
| `detect-artifacts` | `[--root]` | Scan for committable artifacts |
| `worktree-path` | `--plan-id` | Resolve the persisted worktree path via `manage-status get-worktree-path` |
| `worktree-create` | `--plan-id --branch [--base]` | Run `git worktree add` plus project-state bookkeeping (`metadata.use_worktree`/`worktree_path`/`worktree_branch`) |
| `worktree-remove` | `--plan-id [--force]` | Remove the worktree first, then delete the branch ref |
| `worktree-list` | _(none)_ | List plans whose `status.metadata.use_worktree == true` |

The `worktree-*` subcommands implement the §9 two-state contract: `--plan-id` is mandatory (these verbs operate on a worktree), and path resolution flows through `manage-status get-worktree-path` so a single plan-id is sufficient — no `--project-dir`, no filesystem layout re-derivation. `worktree-create` is the only verb that materializes a path on disk; it computes `get_worktree_root() / <plan-id>`, runs `git worktree add`, and writes the resolved path back to status metadata so subsequent verbs resolve through the canonical channel.

### format-commit

Format commit message following conventional commits.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow format-commit \
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
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow analyze-diff \
  --worktree-path /path/to/worktree [--cached]
```

**Parameters**:
- `--worktree-path` (required): Worktree path to capture the diff from. The script runs `git -C {worktree_path} diff` against this directory.
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
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow detect-artifacts \
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

### worktree-path

Resolve the persisted worktree path for a plan via `manage-status get-worktree-path`. Returns the absolute path plus an `exists` flag indicating whether the directory is currently materialized. The path is the value of `status.metadata.worktree_path` — set when the plan was created with `--use-worktree` or by a prior `worktree-create` invocation.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow worktree-path \
  --plan-id my-plan
```

**Parameters**:
- `--plan-id` (required): Plan identifier. Absence is rejected with `error: plan_resolution_failed` — the worktree subcommands operate on a worktree, so a plan id is mandatory.

**Output** (TOON):
```toon
status: success
plan_id: my-plan
worktree_path: /repo/.plan/local/worktrees/my-plan
exists: true
```

### worktree-create

Run `git worktree add <resolved-path> <branch>` against the main checkout, set up `.plan/local` and `.plan/execute-script.py` symlinks, best-effort bootstrap pyprojectx, and persist the resolved path/branch via `manage-status metadata --set` so subsequent verbs can resolve through the canonical channel. The path is computed from `get_worktree_root() / <plan-id>`.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow worktree-create \
  --plan-id my-plan --branch feature/my-plan [--base main]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (mandatory).
- `--branch` (required): Feature branch name to create.
- `--base`: Base ref for the new branch (default: current HEAD).

**Output** (TOON):
```toon
status: success
plan_id: my-plan
worktree_path: /repo/.plan/local/worktrees/my-plan
branch: feature/my-plan
plan_symlink: /repo/.plan/local/worktrees/my-plan/.plan
bootstrap: ok
```

### worktree-remove

Remove the worktree (`git worktree remove`) first, then delete the branch ref read from status metadata. Order matters: `git worktree remove` refuses to drop a branch ref that is still checked out, so cleanup is always worktree-first. Branch deletion failures surface as `branch_warning` rather than failing the command — the worktree is gone, branch cleanup is recoverable.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow worktree-remove \
  --plan-id my-plan [--force]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (mandatory).
- `--force`: Force removal (use only if worktree is clean).

**Output** (TOON, success):
```toon
status: success
plan_id: my-plan
worktree_path: /repo/.plan/local/worktrees/my-plan
action: removed
branch: feature/my-plan
```

### worktree-list

Enumerate plans whose `status.metadata.use_worktree == true`. Reads from `manage-status list`, then resolves each plan's worktree path via `manage-status get-worktree-path`; plans without a configured worktree are silently skipped.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow worktree-list
```

**Parameters**: _(none)_

**Output** (TOON):
```toon
status: success
worktrees_root: /repo/.claude/worktrees
count: 2
worktrees[2]{plan_id,path,branch}:
  my-plan,/repo/.plan/local/worktrees/my-plan,feature/my-plan
  other,/repo/.plan/local/worktrees/other,feature/other
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
