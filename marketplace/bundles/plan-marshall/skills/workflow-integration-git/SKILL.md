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
- Never run raw `git <subcommand>` that relies on the current working directory. Agent cwd is unreliable under worktree isolation.

**Constraints:**
- Commit messages must follow conventional commits format: `<type>(<scope>): <subject>` — see `standards/git-commit-standards.md` for types, rules, and examples
- Push only when explicitly requested via parameters
- All git invocations MUST use `git -C {worktree_path} <subcommand>`. No `cd` chaining, no implicit cwd. `{worktree_path}` is resolved from `status.metadata.worktree_path` in Step 0 of the Commit Changes workflow.

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

# Analyze a diff for commit suggestions
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow analyze-diff --file changes.diff

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

The script returns `safe` (auto-deletable) and `uncertain` (needs confirmation) lists. Pattern definitions are in `standards/artifact-patterns.json`. The script respects `.gitignore` by default — gitignored files are excluded since they cannot be accidentally committed. For safe artifacts, delete them. For uncertain artifacts, ask user via `AskUserQuestion`.

**Step 4: Generate Commit Message**

If custom message provided:
- Validate format
- Use provided message

If no message:
- Generate diff: `git -C {worktree_path} diff --cached > /tmp/changes.diff` (or `git -C {worktree_path} diff` for unstaged)
- Analyze diff using script to get type/scope hints:

  ```bash
  python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow analyze-diff --file <diff-file>
  ```
- The script suggests `type` and `scope` but NOT the subject line — compose the subject yourself based on the diff content and the detected type
- If multiple change types are present, use the highest priority: fix > feat > perf > refactor > docs > style > test > chore > ci
- **Scope caveat**: The script infers scope from the first source file's path structure. For changes spanning multiple modules, the detected scope may not be representative — omit scope for cross-cutting changes.

**Step 5: Stage and Commit**

Stage specific files relevant to the logical change (use `git -C {worktree_path} status --porcelain` to review):
```bash
git -C {worktree_path} add <specific-files>
git -C {worktree_path} commit -m "$(cat <<'EOF'
{commit_message}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

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
| `analyze-diff` | `--file` | Analyze diff for commit suggestions |
| `detect-artifacts` | `[--root]` | Scan for committable artifacts |

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

Analyze diff file to suggest commit message parameters.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git_workflow analyze-diff \
  --file changes.diff
```

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

## Error Handling

| Failure | Action |
|---------|--------|
| No changes to commit | Report "No changes to commit" and return success (not an error). |
| format-commit validation failure | Report warnings to caller. Do not commit with invalid message. |
| analyze-diff on missing file | Return failure with path. Caller should generate diff first. |
| Artifact cleanup uncertain | Ask user via `AskUserQuestion` before deleting. Never auto-delete uncertain files. |
| git commit failure (hook rejection, conflict) | Report error with full output. Do not retry automatically. |
| git push failure | Report error. Never force-push as fallback. |

## Standards (Load On-Demand)

| Standard | When to Load |
|----------|-------------|
| `standards/git-commit-standards.md` | Edge cases: breaking changes, multi-footer, scope guidelines, anti-patterns |
| `standards/git-commit-config.json` | Adding/updating valid commit types, imperative mood allowlist, or length thresholds |
| `standards/artifact-patterns.json` | Adding/updating artifact detection patterns and cleanup rules |

## Related

See `ref-workflow-architecture` → "Workflow Skill Orchestration" for the full dependency graph and shared infrastructure documentation. Called by: `plan-marshall:workflow-pr-doctor` (commit after fixes), `plan-marshall:phase-6-finalize` (final commit).
