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

## Repo Merge-Queue Operations

GitHub's merge queue is configured through a repository **ruleset** carrying a
rule of `type == "merge_queue"` on the target branch. The `repo merge-queue`
verbs read and write that state via `gh api`.

### repo merge-queue probe

Resolve the default branch, then read the evaluated rule set for that branch —
a single flat call that returns every rule applying to the branch.

**CLI Command**:
```bash
gh api repos/{owner}/{repo}                        # → .default_branch
gh api repos/{owner}/{repo}/rules/branches/{branch}  # → [ {type: ...}, ... ]
```

**Discriminator mapping**:

| Rules-endpoint result | `eligibility` |
|-----------------------|---------------|
| a rule with `type == "merge_queue"` is present | `eligible_configured` |
| no `merge_queue` rule present | `eligible_unconfigured` |
| HTTP 404 (rules endpoint unavailable) | `ineligible` |
| HTTP 401/403 or "must have admin" / "Resource not accessible" | actionable auth-scope error (never a stack trace) |

On `eligible_configured` the success TOON additionally carries `merge_method` —
the found `merge_queue` rule's `parameters.merge_method` in the ruleset spelling
(`SQUASH` / `MERGE` / `REBASE`). The field is omitted when the queue is
unconfigured or the parameter is absent/malformed.

**`externally_managed`** is also carried on `eligible_configured`, for **both**
`probe` and `enable`. It is computed by a read-only lookup for a ruleset named
`plan-marshall-merge-queue`: `true` when the queue is configured but no such
ruleset exists (the queue is owned by a foreign ruleset), `false` when
plan-marshall owns the ruleset. The field is **absent** — never `false` — on
every other discriminator, and on a lookup failure where ownership is genuinely
unknown, so unrelated return envelopes stay byte-stable.

> **Invariant**: plan-marshall never creates, reconciles, renames, or deletes a
> ruleset it did not create. On the `externally_managed: true` path no
> `POST` / `PUT` / `DELETE` is issued — `enable` reports the state and stops.

### repo merge-queue enable

Probe first. On `eligible_unconfigured` it creates an active branch ruleset
carrying a `merge_queue` rule scoped to the default branch. The rule's
`merge_method` is the mapped value of the configured `pr_merge_strategy`
(`default:branch-cleanup` step param): `squash` → `SQUASH`, `merge` → `MERGE`,
`rebase` → `REBASE`, defaulting to `SQUASH` on an absent/malformed/unknown
value:

**CLI Command**:
```bash
gh api -X POST repos/{owner}/{repo}/rulesets --input {payload.json}
```

The request body (the nested ruleset structure cannot be expressed via `-f`
field flags, so it is written to a transient file and passed via `--input`):

```json
{
  "name": "plan-marshall-merge-queue",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/heads/{branch}"], "exclude": []}},
  "rules": [{"type": "merge_queue", "parameters": {"merge_method": "{mapped pr_merge_strategy}", "grouping_strategy": "ALLGREEN", ...}}],
  "bypass_actors": [{"actor_id": "{resolved id}", "actor_type": "Integration", "bypass_mode": "always"}]
}
```

The top-level `bypass_actors` array is **conditional** — it is present only when
at least one bypass-actor id resolves, and the key is omitted entirely
otherwise. Each entry grants one GitHub App an `Integration` bypass with
`bypass_mode: always`, which is what lets org release automation push straight
to the ruleset-protected default branch without a GH013 rejection.

**Bypass-actor resolution** is two-tier and config-first:

| Tier | Source | Behavior |
|------|--------|----------|
| 1 | `merge_queue.bypass_app_id` (int) | Yields `[id]` with **no** API call — works for org-owned and personal-account repos |
| 2 | `merge_queue.bypass_app_slugs` (list[str]) | Only when no config id: `GET /orgs/{owner}/installations`, match each installation's `app_slug` against the configured slug(s), return the matched `app_id`(s) |
| 3 | neither resolves | `[]` — the ruleset is created without a `bypass_actors` key |

The tier-2 lookup is best-effort: any non-zero `gh` exit (including the
`admin:org`-scope or non-org-ownership precondition failure) degrades to `[]`
rather than surfacing an error, so an under-scoped or personal-account token
still creates the queue.

**`warnings[]` on the create return**: a create that resolved **no** bypass
actor still succeeds — the create is never refused — and the success TOON
carries a `warnings` list with one actionable entry: the created queue is
mandatory, so any direct push from release/tag automation to the default branch
will be rejected with GH013, and the remedy is to set
`merge_queue.bypass_app_id` or `merge_queue.bypass_app_slugs` in `marshal.json`
and re-run enable. The key is **omitted entirely** when a bypass actor resolved,
so the happy-path success shape is unchanged.

On `eligible_configured` the verb reconciles the named
`plan-marshall-merge-queue` ruleset's merge method against the same mapped
`pr_merge_strategy` value: when `parameters.merge_method` already matches, the
verb is a no-op (`changed: false`); when it differs, the corrected `merge_queue`
rule parameters are written via `PUT /repos/{owner}/{repo}/rulesets/{id}` (a
documented partial update, sent with the existing
name/target/enforcement/conditions/rules echoed back defensively) and the verb
returns `changed: true` with the reconcile detail. The method reconcile shares
one ruleset fetch — and at most one PUT — with the bypass-actor self-heal. A
merge queue configured under some other ruleset name is **externally managed**:
the verb returns `changed: false` with `externally_managed: true` and a detail
naming the state, and issues no mutation of any kind (see the invariant above).
That envelope is distinct from the genuine idempotent no-op, where
plan-marshall owns the ruleset and everything already matches.

On an `ineligible` probe the verb refuses with the actionable message naming the
Administration-scope / org-policy remedy; an auth-scope failure returns the same
actionable remedy.

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

### issue view

View issue details using `gh issue view`.

**CLI Command**:
```bash
gh issue view 123 --json number,url,title,body,author,state,createdAt,updatedAt,labels,assignees,milestone
```

**Response**:
```json
{
  "number": 123,
  "url": "https://github.com/org/repo/issues/123",
  "title": "Bug in authentication",
  "body": "Description...",
  "author": {"login": "username"},
  "state": "OPEN",
  "createdAt": "2025-01-15T10:30:00Z",
  "updatedAt": "2025-01-18T14:20:00Z",
  "labels": [{"name": "bug"}, {"name": "priority:high"}],
  "assignees": [{"login": "alice"}],
  "milestone": {"title": "v2.0"}
}
```

**Field Mapping**:
| TOON Field | JSON Path |
|------------|-----------|
| issue_number | `.number` |
| issue_url | `.url` |
| title | `.title` |
| body | `.body` |
| author | `.author.login` |
| state | `.state` (lowercase) |
| labels[] | `.labels[].name` |
| assignees[] | `.assignees[].login` |
| milestone | `.milestone.title` (or null) |

**State Values**:
| State | Meaning |
|-------|---------|
| OPEN | Issue is open |
| CLOSED | Issue is closed |

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
| `issue view` | View issue details |
