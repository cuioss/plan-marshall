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
- Never force-push or amend published commits without explicit user approval
- Never commit secrets, credentials, or `.env` files
- Never skip artifact cleanup step before committing

**Constraints:**
- Each workflow step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- Commit messages must follow conventional commits format
- Push only when explicitly requested via parameters

## What This Skill Provides

### Workflows

1. **Commit Changes Workflow** - Full commit lifecycle
   - Artifact cleanup, staging, message generation, commit, optional push

### Capabilities

- Artifact detection and cleanup
- Commit message generation following conventional commits
- Optional push to remote

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | optional | Custom commit message (auto-generated from diff if omitted) |
| `push` | optional | Push to remote after committing (default: false) |

### Commit Standards (Quick Reference)

- **Format:** `<type>(<scope>): <subject>`
- **Types:** feat, fix, docs, style, refactor, perf, test, chore, ci
- **Subject:** imperative mood, lowercase, no period, max 50 chars (72 absolute max)
- **Body:** explain "why" not "what", wrap at 72 chars
- **Footer:** `BREAKING CHANGE:`, `Fixes #123`, `Co-Authored-By:`
- **Atomic:** one logical change per commit, code compiles and tests pass

## When to Activate This Skill

- Committing changes to repository
- Generating commit messages from diffs
- Cleaning build artifacts before commit

## Workflow: Commit Changes

**Purpose:** Commit all uncommitted changes following Git Commit Standards.

**Input Parameters:**
- **message** (optional): Custom commit message
- **push** (optional): Push after committing

### Steps

**Step 1: Verify Commit Standards**
Use the quick reference above. For edge cases (breaking changes, multi-footer, scope guidelines), read `standards/git-commit-standards.md`.

**Step 2: Check for Uncommitted Changes**
```bash
git status --porcelain
```

If no changes → Report "No changes to commit"

**Step 3: Clean Artifacts**

Detect artifacts using the script:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow detect-artifacts [--root <repo-root>]
```

The script returns `safe` (auto-deletable) and `uncertain` (needs confirmation) lists.
For safe artifacts, delete them. For uncertain artifacts, ask user via `AskUserQuestion`.
For full detection patterns and cleanup rules, read `standards/artifact-cleanup.md`.

**Step 4: Generate Commit Message**

If custom message provided:
- Validate format
- Use provided message

If no message:
- Analyze diff using script:

  ```bash
  python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff --file <diff-file>
  ```
- Generate message following standards

**Multi-type priority:** fix > feat > perf > refactor > docs > style > test > chore > ci

**Step 5: Stage and Commit**
```bash
git add <specific-files>
git commit -m "$(cat <<'EOF'
{commit_message}

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Step 6: Push (Optional)**

If `push` parameter:
```bash
git push
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
| `format-commit` | `--type --subject [--scope] [--body] [--breaking] [--footer]` | Format commit message |
| `analyze-diff` | `--file` | Analyze diff for commit suggestions |
| `detect-artifacts` | `[--root]` | Scan for committable artifacts |

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

Analyze diff file to suggest commit message parameters.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow analyze-diff \
  --file changes.diff
```

**Output** (TOON):
```toon
mode: analysis
suggestions:
  type: feat
  scope: auth
  subject: ~
  detected_changes[1]:
    - Significant new code added
  files_changed[1]:
    - src/main/java/auth/Login.java
status: success
```

### detect-artifacts

Scan a directory for build artifacts and temporary files that should not be committed.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow detect-artifacts \
  [--root /path/to/repo]
```

**Parameters**:
- `--root`: Root directory to scan (default: current working directory)

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

When a script or step returns failure:
- **No changes to commit**: Report "No changes to commit" and return success (not an error).
- **format-commit validation failure**: Report warnings to caller. Do not commit with invalid message.
- **analyze-diff on missing file**: Return failure with path. Caller should generate diff first.
- **Artifact cleanup uncertain**: Ask user via `AskUserQuestion` before deleting. Never auto-delete uncertain files.
- **git commit failure** (hook rejection, conflict): Report error with full output. Do not retry automatically.
- **git push failure**: Report error. Never force-push as fallback.

## Standards (Load On-Demand)

| Standard | When to Load |
|----------|-------------|
| `standards/git-commit-standards.md` | Edge cases: breaking changes, multi-footer, scope guidelines, anti-patterns |
| `standards/artifact-cleanup.md` | Artifact detection patterns and cleanup rules |

## Critical Rules

**Artifacts:** NEVER commit `*.class`, `*.temp`, `*.backup*`
**Permissions:** NEVER push without `push` param
**Standards:** Follow conventional commits format, add Co-Authored-By footer
**Safety:** Ask user if uncertain about file deletion

## References

- Conventional Commits: https://www.conventionalcommits.org/
- Git Commit Best Practices: https://cbea.ms/git-commit/
