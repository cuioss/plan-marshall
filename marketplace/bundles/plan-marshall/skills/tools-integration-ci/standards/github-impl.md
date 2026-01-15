# GitHub Implementation

GitHub-specific implementation details using the `gh` CLI.

---

## Tool Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| `gh` | 2.0+ | GitHub CLI for all operations |

### Authentication Check

```bash
gh auth status
```

**Success**: Exit code 0
**Failure**: Exit code 1 (not authenticated)

---

## PR Operations

### pr create

Create a pull request using `gh pr create`.

**CLI Command**:
```bash
gh pr create \
    --title "Title" \
    --body "Body" \
    --base main \
    [--draft]
```

**JSON Output** (for parsing):
```bash
gh pr create --title "Title" --body "Body" --json number,url
```

**Response**:
```json
{
  "number": 456,
  "url": "https://github.com/org/repo/pull/456"
}
```

### pr reviews

Get reviews for a pull request.

**CLI Command**:
```bash
gh pr view 123 --json reviews
```

**Response**:
```json
{
  "reviews": [
    {
      "author": {"login": "alice"},
      "state": "APPROVED",
      "submittedAt": "2025-01-15T10:30:00Z"
    },
    {
      "author": {"login": "bob"},
      "state": "CHANGES_REQUESTED",
      "submittedAt": "2025-01-15T11:00:00Z"
    }
  ]
}
```

**Review States**:
| State | Meaning |
|-------|---------|
| APPROVED | Reviewer approved |
| CHANGES_REQUESTED | Reviewer requested changes |
| COMMENTED | Reviewer left comments only |
| PENDING | Review not yet submitted |
| DISMISSED | Review was dismissed |

---

## CI Operations

### ci status

Check CI status for a pull request.

**CLI Command**:
```bash
gh pr checks 123 --json name,state,conclusion
```

**Response**:
```json
[
  {"name": "build", "state": "completed", "conclusion": "success"},
  {"name": "test", "state": "in_progress", "conclusion": null},
  {"name": "lint", "state": "completed", "conclusion": "failure"}
]
```

**State Values**:
| State | Meaning |
|-------|---------|
| queued | Check is queued |
| in_progress | Check is running |
| completed | Check has finished |

**Conclusion Values** (when state is completed):
| Conclusion | Meaning |
|------------|---------|
| success | Check passed |
| failure | Check failed |
| cancelled | Check was cancelled |
| skipped | Check was skipped |
| timed_out | Check timed out |

### ci wait

Wait for CI checks to complete.

**CLI Command**:
```bash
gh pr checks 123 --watch
```

**Alternative** (script polling):
Poll `gh pr checks 123 --json state` at intervals until all checks complete.

**Completion Logic**:
```python
def is_complete(checks):
    return all(c["state"] == "completed" for c in checks)

def get_final_status(checks):
    if any(c["conclusion"] == "failure" for c in checks):
        return "failure"
    if all(c["conclusion"] == "success" for c in checks):
        return "success"
    return "mixed"
```

---

## Issue Operations

### issue create

Create an issue using `gh issue create`.

**CLI Command**:
```bash
gh issue create \
    --title "Bug: feature X" \
    --body "Description" \
    [--label "bug,priority:high"]
```

**JSON Output** (for parsing):
```bash
gh issue create --title "Title" --body "Body" --json number,url
```

**Response**:
```json
{
  "number": 789,
  "url": "https://github.com/org/repo/issues/789"
}
```

---

## Error Handling

### Common gh Errors

| Exit Code | Error | Handling |
|-----------|-------|----------|
| 1 | Not authenticated | Return auth error |
| 1 | Not in git repo | Return repo error |
| 1 | PR not found | Return not found error |
| 1 | Network error | Return network error |
| 4 | Command cancelled | Return cancelled error |

### Error Detection Pattern

```python
result = subprocess.run(["gh", "pr", "view", "123"], capture_output=True)
if result.returncode != 0:
    stderr = result.stderr.decode()
    if "not logged in" in stderr.lower():
        return {"status": "error", "error": "Not authenticated"}
    if "could not find" in stderr.lower():
        return {"status": "error", "error": f"PR {pr_number} not found"}
```

---

## Rate Limiting

GitHub API has rate limits. The `gh` CLI handles this automatically with:
- Automatic retry with backoff
- Rate limit headers in response

For high-volume operations, consider:
- Batching requests
- Adding delays between operations
- Checking rate limit status: `gh api rate_limit`

---

## Authentication Methods

| Method | Command | Use Case |
|--------|---------|----------|
| Interactive | `gh auth login` | User setup |
| Token | `gh auth login --with-token` | CI/CD |
| SSH | `gh auth login --git-protocol ssh` | SSH-based auth |

**Token Environment Variable**:
```bash
export GH_TOKEN=ghp_xxxx
gh auth status  # Uses GH_TOKEN automatically
```

---

## Executor Mapping

The script is invoked via the executor:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github <command> [args]
```

**Commands**:
| Command | Description |
|---------|-------------|
| `pr create` | Create pull request |
| `pr reviews` | Get PR reviews |
| `ci status` | Check CI status |
| `ci wait` | Wait for CI completion |
| `issue create` | Create issue |
