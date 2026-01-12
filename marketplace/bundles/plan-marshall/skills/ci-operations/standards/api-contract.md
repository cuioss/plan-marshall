# CI Operations API Contract

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
python3 .plan/execute-script.py plan-marshall:ci-operations:ci_health detect
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
python3 .plan/execute-script.py plan-marshall:ci-operations:ci_health verify [--tool TOOL]
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
python3 .plan/execute-script.py plan-marshall:ci-operations:ci_health status
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
python3 .plan/execute-script.py plan-marshall:ci-operations:ci_health persist [--plan-dir .plan]
```

**Success Output**:
```toon
status: success
persisted_to: marshal.json

ci_config{key,value}:
provider	github
repo_url	https://github.com/org/repo

ci_commands[5]{name,command}:
pr-create	python3 .plan/execute-script.py plan-marshall:ci-operations:github pr create
pr-reviews	python3 .plan/execute-script.py plan-marshall:ci-operations:github pr reviews
ci-status	python3 .plan/execute-script.py plan-marshall:ci-operations:github ci status
ci-wait	python3 .plan/execute-script.py plan-marshall:ci-operations:github ci wait
issue-create	python3 .plan/execute-script.py plan-marshall:ci-operations:github issue create
```

---

## PR Operations (github.py / gitlab.py)

### pr create

Create a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:ci-operations:github pr create \
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

### pr reviews

Get reviews for a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:ci-operations:github pr reviews \
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

## CI Operations (github.py / gitlab.py)

### ci status

Check CI status for a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:ci-operations:github ci status \
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

checks[3]{name,status,conclusion}:
build	completed	success
test	in_progress	-
lint	completed	failure
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
timeout 600s python3 .plan/execute-script.py plan-marshall:ci-operations:github ci wait \
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
```

**Timeout Output**:
```toon
status: error
operation: ci_wait
error: Timeout waiting for CI
pr_number: 123
duration_sec: 300
last_status: pending
```

---

## Issue Operations (github.py / gitlab.py)

### issue create

Create an issue.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:ci-operations:github issue create \
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
      "pr-create": "python3 .plan/execute-script.py plan-marshall:ci-operations:github pr create",
      "pr-reviews": "python3 .plan/execute-script.py plan-marshall:ci-operations:github pr reviews",
      "ci-status": "python3 .plan/execute-script.py plan-marshall:ci-operations:github ci status",
      "ci-wait": "python3 .plan/execute-script.py plan-marshall:ci-operations:github ci wait",
      "issue-create": "python3 .plan/execute-script.py plan-marshall:ci-operations:github issue create"
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
