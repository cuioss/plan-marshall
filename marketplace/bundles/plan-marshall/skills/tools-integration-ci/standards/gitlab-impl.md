# GitLab Implementation

GitLab-specific implementation details using the `glab` CLI.

---

## Tool Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| `glab` | 1.0+ | GitLab CLI for all operations |

### Authentication Check

```bash
glab auth status
```

**Success**: Exit code 0
**Failure**: Exit code 1 (not authenticated)

---

## Terminology Mapping

GitLab uses different terminology than GitHub:

| GitHub | GitLab | Notes |
|--------|--------|-------|
| Pull Request (PR) | Merge Request (MR) | Same concept |
| Checks | Pipelines/Jobs | CI status |
| `gh` | `glab` | CLI tool |

The API contract uses GitHub terminology (pr, ci) for consistency. The GitLab script translates internally.

---

## PR (Merge Request) Operations

### pr create

Create a merge request using `glab mr create`.

**CLI Command**:
```bash
glab mr create \
    --title "Title" \
    --description "Body" \
    --target-branch main \
    [--draft]
```

**JSON Output** (for parsing):
```bash
glab mr create --title "Title" --description "Body" --json iid,web_url
```

**Response**:
```json
{
  "iid": 456,
  "web_url": "https://gitlab.com/org/repo/-/merge_requests/456"
}
```

### pr reviews

Get reviews (approvals) for a merge request.

**CLI Command**:
```bash
glab mr view 123 --json approvals
```

**Alternative API Call**:
```bash
glab api projects/:id/merge_requests/123/approvals
```

**Response**:
```json
{
  "approved": true,
  "approved_by": [
    {
      "user": {"username": "alice"},
      "approved_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Note**: GitLab approvals are simpler than GitHub reviews. There's no "CHANGES_REQUESTED" state - users either approve or leave comments.

**State Mapping**:
| GitLab | Mapped to API Contract |
|--------|------------------------|
| approved | APPROVED |
| comment (not approved) | COMMENTED |

---

## CI Operations

### ci status

Check pipeline status for a merge request.

**CLI Command**:
```bash
glab mr view 123 --json pipeline
```

**Response**:
```json
{
  "pipeline": {
    "id": 789,
    "status": "running",
    "web_url": "https://gitlab.com/org/repo/-/pipelines/789"
  }
}
```

**Get Individual Jobs**:
```bash
glab ci view 789 --json jobs
```

**Response**:
```json
{
  "jobs": [
    {"name": "build", "status": "success"},
    {"name": "test", "status": "running"},
    {"name": "lint", "status": "failed"}
  ]
}
```

**Pipeline Status Values**:
| Status | Meaning |
|--------|---------|
| created | Pipeline created |
| pending | Pipeline pending |
| running | Pipeline running |
| success | Pipeline succeeded |
| failed | Pipeline failed |
| canceled | Pipeline canceled |
| skipped | Pipeline skipped |

**Job Status Mapping**:
| GitLab Status | API Contract Status | API Contract Conclusion |
|---------------|---------------------|------------------------|
| running | in_progress | - |
| success | completed | success |
| failed | completed | failure |
| canceled | completed | cancelled |
| skipped | completed | skipped |

### ci wait

Wait for pipeline to complete.

**CLI Command**:
```bash
glab ci status --wait
```

**Alternative** (script polling):
Poll pipeline status at intervals until complete.

**Completion Logic**:
```python
def is_complete(pipeline_status):
    return pipeline_status in ["success", "failed", "canceled", "skipped"]

def get_final_status(pipeline_status):
    if pipeline_status == "success":
        return "success"
    return "failure"  # failed, canceled, skipped all map to failure
```

---

## Issue Operations

### issue create

Create an issue using `glab issue create`.

**CLI Command**:
```bash
glab issue create \
    --title "Bug: feature X" \
    --description "Description" \
    [--label "bug,priority::high"]
```

**JSON Output** (for parsing):
```bash
glab issue create --title "Title" --description "Body" --json iid,web_url
```

**Response**:
```json
{
  "iid": 789,
  "web_url": "https://gitlab.com/org/repo/-/issues/789"
}
```

**Note**: GitLab uses `iid` (internal ID) for issue numbers within a project.

---

## Error Handling

### Common glab Errors

| Exit Code | Error | Handling |
|-----------|-------|----------|
| 1 | Not authenticated | Return auth error |
| 1 | Not in git repo | Return repo error |
| 1 | MR not found | Return not found error |
| 1 | Network error | Return network error |

### Error Detection Pattern

```python
result = subprocess.run(["glab", "mr", "view", "123"], capture_output=True)
if result.returncode != 0:
    stderr = result.stderr.decode()
    if "not logged in" in stderr.lower() or "authentication" in stderr.lower():
        return {"status": "error", "error": "Not authenticated"}
    if "not found" in stderr.lower():
        return {"status": "error", "error": f"MR {mr_number} not found"}
```

---

## Enterprise GitLab

For GitLab enterprise installations:

### Configuration

```bash
glab auth login --hostname gitlab.company.com
```

### Detection

The `ci_health.py` script detects GitLab enterprise by:
1. Checking for `gitlab.` in the remote URL
2. Checking for `.gitlab.` subdomain patterns
3. Checking for `.gitlab-ci.yml` file

---

## Rate Limiting

GitLab API has rate limits (varies by instance):
- gitlab.com: 2000 requests/minute for authenticated users
- Self-hosted: Configurable by admin

For high-volume operations:
- Check rate limit headers in API responses
- Add delays between operations if needed

---

## Authentication Methods

| Method | Command | Use Case |
|--------|---------|----------|
| Interactive | `glab auth login` | User setup |
| Token | `glab auth login --token` | CI/CD |
| SSH | Automatic with SSH keys | SSH-based auth |

**Token Environment Variable**:
```bash
export GITLAB_TOKEN=glpat-xxxx
glab auth status  # Uses GITLAB_TOKEN automatically
```

---

## Executor Mapping

The script is invoked via the executor:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:gitlab <command> [args]
```

**Commands**:
| Command | Description |
|---------|-------------|
| `pr create` | Create merge request |
| `pr reviews` | Get MR approvals |
| `ci status` | Check pipeline status |
| `ci wait` | Wait for pipeline completion |
| `issue create` | Create issue |

**Note**: Commands use GitHub terminology (pr, not mr) for API consistency. The script translates to GitLab equivalents internally.
