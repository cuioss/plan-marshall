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

Verify the CI tool and persist `authenticated_tools` to `run-configuration.json`. Provider identity and repo URL are canonically read from `providers[]` in marshal.json — this command does NOT write a `config["ci"]` block.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health persist [--plan-dir .plan]
```

**Success Output**:
```toon
status: success
persisted_to: run-configuration.json
provider: github
repo_url: https://github.com/org/repo
authenticated_tools[2]:
  - git
  - gh
```

---

## PR Operations (github.py / gitlab.py)

Every PR subcommand returns the standard envelope: success shape (`status: success`, `operation: {op}`, plus the identifiers listed in the "Response fields" column) and error shape (`status: error`, `operation: {op}`, `error: ...`, `context: {cli exit reason}`).

| Subcommand | Required args | Optional flags | Response fields |
|------------|---------------|----------------|-----------------|
| `pr create` | `--title`, `--body` | `--base` (default `main`), `--draft` | `pr_number`, `pr_url` |
| `pr view` | — (uses current branch) | — | `pr_number`, `pr_url`, `state`, `title`, `head_branch`, `base_branch`, `is_draft`, `mergeable`, `merge_state`, `review_decision` |
| `pr list` | — | `--head {branch}`, `--state open\|closed\|all` (default `open`) | `total`, `state_filter`, `head_filter`, `prs[N]{number,url,title,state,head_branch,base_branch}` |
| `pr reply` | `--pr-number`, `--body` | — | `pr_number` |
| `pr resolve-thread` | `--thread-id` (GitLab also requires `--pr-number`) | — | `thread_id` |
| `pr thread-reply` | `--pr-number`, `--thread-id`, `--body` | — | `pr_number`, `thread_id` |
| `pr reviews` | `--pr-number` | — | `pr_number`, `review_count`, `reviews[N]{user,state,submitted_at}` |
| `pr comments` | `--pr-number` | `--unresolved-only` | `provider`, `pr_number`, `total`, `unresolved`, `comments[N]{id,author,body,path,line,resolved,created_at}` |

### Provider Field Mapping

The PR operations normalize responses from `gh` (JSON) and `glab` (JSON) into the same shape. Mappings:

- **Top-level identifiers**: `pr_number` ← `.number` (GitHub) / `.iid` (GitLab); `pr_url` ← `.url` / `.web_url`; `state` lower-cased ("opened" → "open"); `title`, `head_branch` ← `.headRefName` / `.source_branch`; `base_branch` ← `.baseRefName` / `.target_branch`; `is_draft` ← `.isDraft` / `.draft`; `mergeable` ← `.mergeable` / `.merge_status`; `merge_state` ← `.mergeStateStatus` (GitHub only); `review_decision` ← `.reviewDecision` / `.approved_by` (mapped).
- **`pr list` CLI differences**: GitHub `gh pr list --head {branch} --state open|closed|all --json number,url,...`; GitLab `glab mr list --source-branch {branch} --state opened|closed|all --output json`.
- **`pr resolve-thread`**: GitHub uses the GraphQL `resolveReviewThread` mutation with a self-contained thread node id (e.g. `PRRT_kwDO...`), so `--pr-number` is ignored; GitLab uses REST `PUT discussions/:id` and requires both `--pr-number` and the discussion id.
- **`pr thread-reply`**: GitHub uses GraphQL `addPullRequestReviewComment` with `inReplyTo` set to the comment node id (the PR node id is fetched internally); GitLab uses REST `POST discussions/:id/notes` and does not require a PR node id.
- **`pr comments` field mapping**: `id` ← `comments.nodes[].id` / `notes[].id`; `author` ← `author.login` / `author.username`; `body` ← `body`; `path` ← `reviewThreads.nodes[].path` / `position.new_path`; `line` ← `reviewThreads.nodes[].line` / `position.new_line`; `resolved` ← `isResolved` / `resolved`.

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

### State-Transition Operations (summary)

The following subcommands all return the standard success shape (`status: success`, `operation: {op}`, plus a key identifier such as `pr_number`, `issue_number`, or `run_id`) and the standard error shape (`status: error`, `operation: {op}`, `error: ...`, `context: {underlying-cli-exit-reason}`). They accept only the listed required arguments and the optional flags noted inline.

| Subcommand | Required args | Optional flags | Notes |
|------------|---------------|----------------|-------|
| `pr merge --pr-number N` | `--pr-number` | `--strategy merge\|squash\|rebase` (default `merge`), `--delete-branch` | Success adds `strategy`. |
| `pr auto-merge --pr-number N` | `--pr-number` | `--strategy` | Enables auto-merge when all checks pass; success adds `enabled: true`. |
| `pr close --pr-number N` | `--pr-number` | — | Closes without merging. |
| `pr ready --pr-number N` | `--pr-number` | — | Marks a draft as ready for review. |
| `pr edit --pr-number N` | `--pr-number` | `--title`, `--body` | Edits title and/or body. |
| `ci rerun --run-id ID` | `--run-id` | — | Re-runs a failed workflow. |
| `ci logs --run-id ID` | `--run-id` | — | Success adds `log_lines` and `content` with the log output. |
| `issue close --issue N` | `--issue` | — | Closes the issue. |

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
    "detected_at": "2025-01-15T10:00:00Z"
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
