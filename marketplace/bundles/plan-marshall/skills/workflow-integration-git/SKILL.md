---
name: workflow-integration-git
description: Git commit workflow with conventional commits, artifact cleanup, and optional push
user-invocable: false
---

# CUI Git Workflow Skill

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

- Artifact detection and cleanup
- Commit message generation following conventional commits
- Optional push to remote

### Commit Standards

- **Format:** `<type>(<scope>): <subject>`
- **Types:** feat, fix, docs, style, refactor, perf, test, chore
- **Quality:** imperative mood, lowercase, no period, max 50 chars

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

**Step 1: Load Commit Standards**
```
Read standards/git-commit-standards.md
```

**Step 2: Check for Uncommitted Changes**
```bash
git status --porcelain
```

If no changes → Report "No changes to commit"

**Step 3: Clean Artifacts**

```
Read standards/artifact-cleanup.md
```

Follow the detection and cleanup rules. Safe deletions are automatic; uncertain cases require user confirmation.

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

**Multi-type priority:** fix > feat > perf > refactor > docs > style > test > chore

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

## Standards (Load On-Demand)

| Standard | When to Load |
|----------|-------------|
| `standards/git-commit-standards.md` | Conventional commits format, type definitions, best practices |
| `standards/artifact-cleanup.md` | Artifact detection patterns and cleanup rules |

## Critical Rules

**Artifacts:** NEVER commit `*.class`, `*.temp`, `*.backup*`
**Permissions:** NEVER push without `push` param
**Standards:** Follow conventional commits format, add Co-Authored-By footer
**Safety:** Ask user if uncertain about file deletion

## References

- Conventional Commits: https://www.conventionalcommits.org/
- Git Commit Best Practices: https://cbea.ms/git-commit/
