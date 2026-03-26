# Tools Integration CI API Contract

Shared TOON output formats and API specifications for all CI operations.

---

## Output Format: TOON

All scripts output TOON format for consistency and easy parsing.

**Structure**:
```toon
status: success|error
operation: <operation_name>
{operation_specific_fields}

{optional_tables}
```

---

## Health Operations (ci_health.py)

### detect

Detect CI provider from git remote.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health detect
```

**Success Output**:
```toon
status: success
provider: github|gitlab|unknown
repo_url: https://github.com/org/repo
confidence: high|medium|none
```

**Error Output**:
```toon
status: error
error: Failed to detect provider
context: git remote get-url origin failed
```

---

### verify

Verify CLI tools are installed and authenticated.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health verify [--tool TOOL]
```

**Success Output** (all tools):
```toon
status: success
all_required_available: true

tools[3]{name,installed,authenticated,version}:
git	true	true	2.43.0
gh	true	true	2.45.0
glab	false	false	-
```

**Success Output** (specific tool):
```toon
status: success
tool: gh
installed: true
authenticated: true
version: 2.45.0
```

---

### status

Full health check combining detect and verify.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health status
```

**Success Output**:
```toon
status: success
provider: github
repo_url: https://github.com/org/repo
confidence: high
required_tool: gh
required_tool_ready: true
overall: healthy|degraded|unknown

tools[2]{name,installed,authenticated}:
git	true	true
gh	true	true
```

---

### persist

Persist configuration to marshal.json with static commands.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health persist [--plan-dir .plan]
```

**Success Output**:
```toon
status: success
persisted_to: marshal.json

ci_config{key,value}:
provider	github
repo_url	https://github.com/org/repo

ci_commands[19]{name,command}:
pr-create	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create
pr-view	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
pr-reviews	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews
pr-comments	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments
pr-reply	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply
pr-resolve-thread	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread
pr-thread-reply	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply
pr-merge	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge
pr-auto-merge	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr auto-merge
pr-close	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr close
pr-ready	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr ready
pr-edit	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr edit
ci-status	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci status
ci-wait	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait
ci-rerun	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci rerun
ci-logs	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci logs
issue-create	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create
issue-view	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue view
issue-close	python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue close
```

---

## PR Operations (github.py / gitlab.py)

### pr create

Create a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
    --title "Add feature X" \
    --body "Description" \
    --base main \
    [--draft]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--title` | Yes | PR title |
| `--body` | Yes | PR description |
| `--base` | No | Base branch (default: main) |
| `--draft` | No | Create as draft PR |

**Success Output**:
```toon
status: success
operation: pr_create
pr_number: 456
pr_url: https://github.com/org/repo/pull/456
```

**Error Output**:
```toon
status: error
operation: pr_create
error: Failed to create PR
context: gh pr create returned non-zero exit code
```

---

### pr view

View PR/MR for the current branch.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
```

**Arguments**: None (uses current branch)

**Success Output**:
```toon
status: success
operation: pr_view
pr_number: 456
pr_url: https://github.com/org/repo/pull/456
state: open
title: Add feature X
head_branch: feature/add-x
base_branch: main
is_draft: false
mergeable: MERGEABLE
merge_state: CLEAN
review_decision: APPROVED
```

**Error Output**:
```toon
status: error
operation: pr_view
error: No PR found for current branch
context: gh pr view returned non-zero exit code
```

**Field Mapping (GitHub vs GitLab)**:
| Field | GitHub | GitLab |
|-------|--------|--------|
| `pr_number` | `.number` | `.iid` |
| `pr_url` | `.url` | `.web_url` |
| `state` | `.state` (lowercase) | `.state` ("opened"→"open") |
| `title` | `.title` | `.title` |
| `head_branch` | `.headRefName` | `.source_branch` |
| `base_branch` | `.baseRefName` | `.target_branch` |
| `is_draft` | `.isDraft` | `.draft` |
| `mergeable` | `.mergeable` | `.merge_status` |
| `merge_state` | `.mergeStateStatus` | - |
| `review_decision` | `.reviewDecision` | `.approved_by` (mapped) |

---

### pr list

List pull requests with optional branch and state filters.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr list \
    [--head feature/branch] \
    [--state open|closed|all]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--head` | No | Filter by head/source branch name |
| `--state` | No | Filter by state: open, closed, all (default: open) |

**Success Output**:
```toon
status: success
operation: pr_list
total: 2
state_filter: open
head_filter: feature/branch

prs[2]{number,url,title,state,head_branch,base_branch}:
123	https://github.com/org/repo/pull/123	Add feature X	open	feature/branch	main
456	https://github.com/org/repo/pull/456	Fix bug Y	open	feature/branch	develop
```

**Error Output**:
```toon
status: error
operation: pr_list
error: Failed to list PRs
context: gh pr list returned non-zero exit code
```

**Field Mapping (GitHub vs GitLab)**:
| Field | GitHub | GitLab |
|-------|--------|--------|
| `number` | `.number` | `.iid` |
| `url` | `.url` | `.web_url` |
| `title` | `.title` | `.title` |
| `state` | `.state` (lowercase) | `.state` ("opened"→"open") |
| `head_branch` | `.headRefName` | `.source_branch` |
| `base_branch` | `.baseRefName` | `.target_branch` |

**CLI Mapping (GitHub vs GitLab)**:
| Aspect | GitHub (`gh`) | GitLab (`glab`) |
|--------|---------------|-----------------|
| Command | `gh pr list` | `glab mr list` |
| `--head` | `--head {branch}` | `--source-branch {branch}` |
| `--state` | `--state open\|closed\|all` | `--state opened\|closed\|all` |
| Output format | `--json number,url,...` | `--output json` |

---

### pr reply

Post a comment on a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply \
    --pr-number 123 \
    --body "Fixed as suggested."
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |
| `--body` | Yes | Comment text |

**Success Output**:
```toon
status: success
operation: pr_reply
pr_number: 123
```

**Error Output**:
```toon
status: error
operation: pr_reply
error: Failed to comment on PR 123
context: gh pr comment returned non-zero exit code
```

---

### pr resolve-thread

Resolve a review thread on a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
    --pr-number 123 \
    --thread-id PRRT_abc123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | GitHub: No, GitLab: Yes | PR number |
| `--thread-id` | Yes | Review thread ID |

**Success Output**:
```toon
status: success
operation: pr_resolve_thread
thread_id: PRRT_abc123
```

**Field Mapping (GitHub vs GitLab)**:
| Aspect | GitHub | GitLab |
|--------|--------|--------|
| API | GraphQL `resolveReviewThread` mutation | REST `PUT discussions/:id` |
| `--thread-id` | GraphQL node ID (e.g., `PRRT_kwDO...`) | Discussion ID |
| `--pr-number` | Ignored (thread ID is self-contained) | Required (URL path component) |

---

### pr thread-reply

Reply to a specific review thread (inline code comment thread).

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
    --pr-number 123 \
    --thread-id PRRT_abc123 \
    --body "Fixed as suggested."
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |
| `--thread-id` | Yes | Comment/thread ID to reply to |
| `--body` | Yes | Reply text |

**Success Output**:
```toon
status: success
operation: pr_thread_reply
pr_number: 123
thread_id: PRRT_abc123
```

**Field Mapping (GitHub vs GitLab)**:
| Aspect | GitHub | GitLab |
|--------|--------|--------|
| API | GraphQL `addPullRequestReviewComment` with `inReplyTo` | REST `POST discussions/:id/notes` |
| `--thread-id` | Comment node ID (`inReplyTo` parameter) | Discussion ID |
| Requires PR node ID | Yes (fetched internally) | No |

---

### pr reviews

Get reviews for a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews \
    --pr-number 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |

**Success Output**:
```toon
status: success
operation: pr_reviews
pr_number: 123
review_count: 2

reviews[2]{user,state,submitted_at}:
alice	APPROVED	2025-01-15T10:30:00Z
bob	CHANGES_REQUESTED	2025-01-15T11:00:00Z
```

---

### pr comments

Get inline code review comments (review threads) for a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments \
    --pr-number 123 \
    [--unresolved-only]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |
| `--unresolved-only` | No | Only return unresolved comments |

**Success Output**:
```toon
status: success
operation: pr_comments
provider: github
pr_number: 123
total: 5
unresolved: 2

comments[5]{id,author,body,path,line,resolved,created_at}:
c1	alice	Fix security issue...	src/Auth.java	42	false	2025-01-15T10:30:00Z
c2	bob	Please rename var	src/Utils.java	15	false	2025-01-15T11:00:00Z
c3	carol	Looks good	src/Main.java	8	true	2025-01-15T11:30:00Z
```

**Field Mapping (GitHub vs GitLab)**:
| Field | GitHub (GraphQL) | GitLab (REST) |
|-------|------------------|---------------|
| `id` | `comments.nodes[].id` | `notes[].id` |
| `author` | `author.login` | `author.username` |
| `body` | `body` | `body` |
| `path` | `reviewThreads.nodes[].path` | `position.new_path` |
| `line` | `reviewThreads.nodes[].line` | `position.new_line` |
| `resolved` | `isResolved` | `resolved` |

---

## CI Operations (github.py / gitlab.py)

### ci status

Check CI status for a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci status \
    --pr-number 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |

**Success Output**:
```toon
status: success
operation: ci_status
pr_number: 123
overall_status: pending|success|failure
check_count: 3
elapsed_sec: 45

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	in_progress	-	45	https://github.com/org/repo/actions/runs/112	CI
lint	completed	failure	30	https://github.com/org/repo/actions/runs/113	Lint
```

**Overall Status Logic**:
- `success`: All checks completed with success
- `failure`: Any check completed with failure
- `pending`: Any check still in progress

---

### ci wait

Wait for CI checks to complete.

**Command**:
```bash
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
    --pr-number 123 \
    [--timeout 300] \
    [--interval 30]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |
| `--timeout` | No | Max wait time in seconds (default: 300) |
| `--interval` | No | Poll interval in seconds (default: 30) |

**Success Output**:
```toon
status: success
operation: ci_wait
pr_number: 123
final_status: success|failure
duration_sec: 95
polls: 4
elapsed_sec: 95

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	completed	success	90	https://github.com/org/repo/actions/runs/112	CI
lint	completed	success	30	https://github.com/org/repo/actions/runs/113	Lint
```

**Timeout Output**:
```toon
status: error
operation: ci_wait
error: Timeout waiting for CI
pr_number: 123
duration_sec: 300
last_status: pending

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	in_progress	-	300	https://github.com/org/repo/actions/runs/112	CI
lint	completed	success	30	https://github.com/org/repo/actions/runs/113	Lint
```

---

## Issue Operations (github.py / gitlab.py)

### issue create

Create an issue.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create \
    --title "Bug: feature X not working" \
    --body "Description of the issue" \
    [--labels "bug,priority:high"]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--title` | Yes | Issue title |
| `--body` | Yes | Issue description |
| `--labels` | No | Comma-separated labels |

**Success Output**:
```toon
status: success
operation: issue_create
issue_number: 789
issue_url: https://github.com/org/repo/issues/789
```

---

### issue view

View issue details.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue view \
    --issue 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--issue` | Yes | Issue number or URL |

**Success Output**:
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

**Field Mapping (GitHub vs GitLab)**:
| Field | GitHub | GitLab |
|-------|--------|--------|
| `issue_number` | `.number` | `.iid` |
| `issue_url` | `.url` | `.web_url` |
| `body` | `.body` | `.description` |
| `author` | `.author.login` | `.author.username` |
| `state` | `.state` (lowercase) | `.state` ("opened"→"open") |
| `labels[]` | `.labels[].name` | `.labels[]` (direct strings) |
| `assignees[]` | `.assignees[].login` | `.assignees[].username` |
| `milestone` | `.milestone.title` | `.milestone.title` |

---

### pr merge

Merge a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge \
    --pr-number 123 \
    [--strategy merge|squash|rebase] \
    [--delete-branch]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |
| `--strategy` | No | Merge strategy: merge, squash, or rebase (default: merge) |
| `--delete-branch` | No | Delete head branch after merge |

**Success Output**:
```toon
status: success
operation: pr_merge
pr_number: 123
strategy: squash
```

**Error Output**:
```toon
status: error
operation: pr_merge
error: Failed to merge PR 123
context: gh pr merge returned non-zero exit code
```

---

### pr auto-merge

Enable auto-merge on a pull request (merges automatically when all checks pass).

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr auto-merge \
    --pr-number 123 \
    [--strategy merge]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |
| `--strategy` | No | Merge strategy: merge, squash, or rebase (default: merge) |

**Success Output**:
```toon
status: success
operation: pr_auto_merge
pr_number: 123
enabled: true
```

**Error Output**:
```toon
status: error
operation: pr_auto_merge
error: Failed to enable auto-merge on PR 123
context: gh pr merge --auto returned non-zero exit code
```

---

### pr close

Close a pull request without merging.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr close \
    --pr-number 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |

**Success Output**:
```toon
status: success
operation: pr_close
pr_number: 123
```

**Error Output**:
```toon
status: error
operation: pr_close
error: Failed to close PR 123
context: gh pr close returned non-zero exit code
```

---

### pr ready

Mark a draft PR as ready for review.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr ready \
    --pr-number 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |

**Success Output**:
```toon
status: success
operation: pr_ready
pr_number: 123
```

**Error Output**:
```toon
status: error
operation: pr_ready
error: Failed to mark PR 123 as ready
context: gh pr ready returned non-zero exit code
```

---

### pr edit

Edit a pull request title and/or body.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr edit \
    --pr-number 123 \
    [--title "New title"] \
    [--body "New body"]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |
| `--title` | No | New PR title |
| `--body` | No | New PR body |

**Success Output**:
```toon
status: success
operation: pr_edit
pr_number: 123
```

**Error Output**:
```toon
status: error
operation: pr_edit
error: Failed to edit PR 123
context: gh pr edit returned non-zero exit code
```

---

### ci rerun

Rerun a failed CI workflow run.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci rerun \
    --run-id 12345
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--run-id` | Yes | Workflow run ID |

**Success Output**:
```toon
status: success
operation: ci_rerun
run_id: 12345
```

**Error Output**:
```toon
status: error
operation: ci_rerun
error: Failed to rerun workflow 12345
context: gh run rerun returned non-zero exit code
```

---

### ci logs

Get logs from a CI workflow run.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci logs \
    --run-id 12345
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--run-id` | Yes | Workflow run ID |

**Success Output**:
```toon
status: success
operation: ci_logs
run_id: 12345
log_lines: 142
content: [build log output]
```

**Error Output**:
```toon
status: error
operation: ci_logs
error: Failed to get logs for workflow 12345
context: gh run view --log returned non-zero exit code
```

---

### issue close

Close an issue.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue close \
    --issue 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--issue` | Yes | Issue number |

**Success Output**:
```toon
status: success
operation: issue_close
issue_number: 123
```

**Error Output**:
```toon
status: error
operation: issue_close
error: Failed to close issue 123
context: gh issue close returned non-zero exit code
```

---

## Exit Codes

| Code | Meaning | Output Stream |
|------|---------|---------------|
| 0 | Success | stdout |
| 1 | Error | stderr |

---

## Error Format

All errors follow the same TOON structure:

```toon
status: error
operation: <operation_name>
error: <error_message>
context: <additional_context>
```

**Common Error Types**:

| Error | Context |
|-------|---------|
| Authentication failed | CLI auth status returned non-zero |
| Tool not installed | which <tool> returned non-zero |
| Network error | Connection timed out |
| Invalid PR number | PR 999 not found |
| Permission denied | No write access to repository |

---

## Marshal.json CI Structure

After `persist` command, marshal.json contains:

```json
{
  "ci": {
    "provider": "github",
    "repo_url": "https://github.com/org/repo",
    "detected_at": "2025-01-15T10:00:00Z",
    "commands": {
      "pr-create": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create",
      "pr-view": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view",
      "pr-reviews": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews",
      "pr-comments": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments",
      "pr-reply": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply",
      "pr-resolve-thread": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread",
      "pr-thread-reply": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply",
      "pr-merge": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge",
      "pr-auto-merge": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr auto-merge",
      "pr-close": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr close",
      "pr-ready": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr ready",
      "pr-edit": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr edit",
      "ci-status": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci status",
      "ci-wait": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait",
      "ci-rerun": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci rerun",
      "ci-logs": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci logs",
      "issue-create": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create",
      "issue-view": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue view",
      "issue-close": "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue close"
    }
  }
}
```

---

## Run-Configuration.json CI Structure

Local machine-specific configuration:

```json
{
  "ci": {
    "git_present": true,
    "authenticated_tools": ["git", "gh"],
    "verified_at": "2025-01-15T10:00:00Z"
  }
}
```
