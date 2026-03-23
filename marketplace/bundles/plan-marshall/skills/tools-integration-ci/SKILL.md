---
name: tools-integration-ci
description: CI provider abstraction with unified API for GitHub and GitLab operations (PR, issues, CI status)
user-invocable: false
---

# Tools Integration CI Skill

Unified CI provider abstraction using **static routing** - one script per provider, config stores full commands.

## What This Skill Provides

- Provider detection and health verification
- PR operations (create, reviews)
- CI status and wait operations
- Issue operations (create)
- Unified TOON output format across providers

## When to Activate This Skill

Activate when:
- Detecting CI provider from repository configuration
- Verifying CI tool installation and authentication
- Creating or managing pull requests
- Checking CI status or waiting for CI completion
- Creating issues

---

## Architecture

**Static Routing Pattern**: Config stores full commands, wizard generates provider-specific paths.

```
marshal.json                          Scripts
ci.commands.pr-create ─────────────► github.py pr create
ci.commands.ci-status ─────────────► github.py ci status
```

**Load Reference**: For full architecture details:
```
Read standards/architecture.md
```

---

## Skill Structure

```
tools-integration-ci/
├── SKILL.md                     # This file
├── standards/
│   ├── architecture.md          # Static routing, skill boundaries
│   ├── api-contract.md          # Shared TOON output formats
│   ├── github-impl.md           # GitHub-specific: gh CLI
│   └── gitlab-impl.md           # GitLab-specific: glab CLI
└── scripts/
    ├── ci_health.py             # Detection & verification
    ├── github.py                # GitHub operations via gh
    └── gitlab.py                # GitLab operations via glab
```

---

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| ci_health | `plan-marshall:tools-integration-ci:ci_health` | Provider detection & verification |
| github | `plan-marshall:tools-integration-ci:github` | GitHub operations via gh CLI |
| gitlab | `plan-marshall:tools-integration-ci:gitlab` | GitLab operations via glab CLI |

---

## Workflow: Health Check

**Pattern**: Command Chain Execution

Detect CI provider and verify tools are available and authenticated.

### Step 1: Run Health Check

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health status
```

### Step 2: Process Result

```toon
status: success
provider: github
repo_url: https://github.com/org/repo
confidence: high
required_tool: gh
required_tool_ready: true
overall: healthy

tools[2]{name,installed,authenticated}:
git	true	true
gh	true	true
```

---

## Workflow: Detect Provider

**Pattern**: Command Chain Execution

Detect CI provider from git remote URL.

### Step 1: Run Detection

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health detect
```

### Step 2: Process Result

```toon
status: success
provider: github
repo_url: https://github.com/org/repo
confidence: high
```

---

## Workflow: Persist Configuration

**Pattern**: Command Chain Execution

Detect provider and persist to marshal.json with static commands.

### Step 1: Run Persist

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health persist
```

### Step 2: Process Result

```toon
status: success
persisted_to: marshal.json

ci_config{key,value}:
provider	github
repo_url	https://github.com/org/repo

ci_commands[11]{name,command}:
pr-create	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr create
pr-view	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr view
pr-reviews	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr reviews
pr-comments	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr comments
pr-reply	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr reply
pr-resolve-thread	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr resolve-thread
pr-thread-reply	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github pr thread-reply
ci-status	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github ci status
ci-wait	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github ci wait
issue-create	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github issue create
issue-view	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github issue view
```

---

## Workflow: View PR (Current Branch)

**Pattern**: Provider-Agnostic Router

Get PR/MR details for the current branch.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
```

### Step 2: Process Result

```toon
status: success
operation: pr_view
pr_number: 456
pr_url: https://github.com/org/repo/pull/456
state: open
title: Add feature X
head_branch: feature/add-x
base_branch: main
```

---

## Workflow: Reply to PR

**Pattern**: Provider-Agnostic Router

Post a comment on a pull request.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply \
    --pr-number 123 --body "Fixed as suggested."
```

### Step 2: Process Result

```toon
status: success
operation: pr_reply
pr_number: 123
```

---

## Workflow: Resolve Review Thread

**Pattern**: Provider-Agnostic Router

Resolve (mark as resolved) a review thread on a PR.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
    --pr-number 123 --thread-id PRRT_abc123
```

### Step 2: Process Result

```toon
status: success
operation: pr_resolve_thread
thread_id: PRRT_abc123
```

---

## Workflow: Reply to Review Thread

**Pattern**: Provider-Agnostic Router

Reply to a specific review thread (inline code comment), not a top-level PR comment.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
    --pr-number 123 --thread-id PRRT_abc123 --body "Fixed as suggested."
```

### Step 2: Process Result

```toon
status: success
operation: pr_thread_reply
pr_number: 123
thread_id: PRRT_abc123
```

---

## Workflow: Create PR

**Pattern**: Provider-Agnostic Router

Create a pull request using config-stored command.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Add feature X" --body "Description" --base main
```

### Step 2: Process Result

```toon
status: success
operation: pr_create
pr_number: 456
pr_url: https://github.com/org/repo/pull/456
```

---

## Workflow: Check CI Status

**Pattern**: Provider-Agnostic Router

Check CI status for a pull request.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci status \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: ci_status
pr_number: 123
overall_status: pending

checks[3]{name,status,conclusion}:
build	completed	success
test	in_progress	-
lint	completed	failure
```

---

## Workflow: Wait for CI

**Pattern**: Polling with Timeout

Wait for CI checks to complete with two-layer timeout pattern.

### Step 1: Execute with Timeout

Use outer shell timeout as safety net:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
    --pr-number 123
```

**Bash tool timeout**: 1800000ms (30-minute safety net). Internal timeout managed by script.

**Claude Bash Tool**: Set `timeout` parameter to `600000` (ms).

### Step 2: Process Result

```toon
status: success
operation: ci_wait
pr_number: 123
final_status: success
duration_sec: 95
```

---

## Workflow: Get PR Reviews

**Pattern**: Provider-Agnostic Router

Get reviews for a pull request.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews \
    --pr-number 123
```

### Step 2: Process Result

```toon
status: success
operation: pr_reviews
pr_number: 123

reviews[2]{user,state,submitted_at}:
alice	APPROVED	2025-01-15T10:30:00Z
bob	CHANGES_REQUESTED	2025-01-15T11:00:00Z
```

---

## Workflow: Create Issue

**Pattern**: Provider-Agnostic Router

Create an issue.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create \
    --title "Bug: feature X" --body "Description"
```

### Step 2: Process Result

```toon
status: success
operation: issue_create
issue_number: 789
issue_url: https://github.com/org/repo/issues/789
```

---

## Workflow: View Issue

**Pattern**: Provider-Agnostic Router

View issue details.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github issue view \
    --issue 123
```

### Step 2: Process Result

```toon
status: success
operation: issue_view
issue_number: 123
issue_url: https://github.com/org/repo/issues/123
title: Bug in authentication flow
body: When users try to login...
author: username
state: open
created_at: 2025-01-15T10:30:00Z
updated_at: 2025-01-18T14:20:00Z

labels[2]:
- bug
- priority:high

assignees[1]:
- alice
```

---

## Storage Pattern

**Split storage** (shared vs local):

| File | Content | Shared |
|------|---------|--------|
| `.plan/marshal.json` | `ci.provider`, `ci.repo_url`, `ci.commands` | Yes (git) |
| `.plan/run-configuration.json` | `ci.authenticated_tools`, command timeouts | No (local) |

---

## Error Handling

All operations return TOON error format on failure:

```toon
status: error
operation: pr_create
error: Authentication failed
context: gh auth status returned non-zero
```

Exit codes:
- `0`: Success (stdout)
- `1`: Error (stderr)

---

## Tool Requirements

| Provider | CLI Tool | Auth Check |
|----------|----------|------------|
| github | `gh` | `gh auth status` |
| gitlab | `glab` | `glab auth status` |

---

## References

- `standards/architecture.md` - Static routing and skill boundaries
- `standards/api-contract.md` - Shared TOON output formats
- `standards/github-impl.md` - GitHub-specific implementation
- `standards/gitlab-impl.md` - GitLab-specific implementation
