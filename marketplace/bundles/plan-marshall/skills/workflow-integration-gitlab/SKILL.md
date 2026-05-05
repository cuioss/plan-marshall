---
name: workflow-integration-gitlab
description: GitLab provider for MR review workflows — fetch comments, triage, and respond to review feedback via glab CLI
user-invocable: false
---

# GitLab CI Integration Workflow Skill

GitLab-specific MR review comment workflow — fetching comments and triaging them into action categories (code_change, explain, ignore). Uses the `glab` CLI for all GitLab operations.

## Enforcement

**Execution mode**: Fetch MR review comments, triage each for action, implement fixes or generate responses, resolve threads.

**Prohibited actions:**
- Never call `glab` directly from LLM context; all operations go through script API
- Never resolve review comments without addressing the reviewer's concern
- Never dismiss reviews without documented justification

**Constraints:**
- Review comment responses must explain the fix or provide rationale for disagreement
- CI wait timeout must be respected with user prompt on expiry

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pr` | int | no | auto-detect | MR number (auto-detects current branch's MR if omitted) |
| `unresolved-only` | bool | no | false | Only return unresolved comments (fetch-comments) |

## Architecture

```
workflow-integration-gitlab (GitLab MR comment workflow)
  ├─> gitlab_ops.py (GitLab operations via glab CLI)
  ├─> gitlab_pr.py (producer-side fetch + pre-filter + per-finding store)
  └─> triage_helpers (ref-toon-format) — shared error handling
```

This skill is the GitLab provider in the CI provider model. The central dispatcher (`tools-integration-ci:ci`) routes to this skill's `gitlab_ops.py` for all GitLab operations.

## Usage Examples

```bash
# Producer-side: fetch + pre-filter + store one pr-comment finding per surviving comment
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr comments-stage --pr-number 123 --plan-id my-plan

# Raw fetch (no filtering, no storage) — for ad-hoc inspection
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr fetch-comments --pr 123

# LLM consumer reads stored findings via manage-findings
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query --plan-id my-plan --type pr-comment
```

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| gitlab_ops | `plan-marshall:workflow-integration-gitlab:gitlab_ops` | GitLab operations via glab CLI |
| gitlab_pr | `plan-marshall:workflow-integration-gitlab:gitlab_pr` | Producer-side MR review comment fetcher (fetch + pre-filter + store) |

## Workflow: Handle Review (Producer-Side)

**Purpose:** Stage MR review comments into the per-type finding store, then let the LLM consumer drive classification and responses from the stored findings.

**Producer-side flow:** `comments-stage` is the only callable surface. It fetches review comments, applies the `comment-patterns.json` keyword pre-filter to drop obvious noise (bot signatures, "lgtm", etc.), and writes one `pr-comment` finding per surviving comment via `manage-findings add`. No script-side classification or batch-triage call is exposed to the LLM — the LLM reads the stored findings and decides per-finding action itself.

**Steps:**

1. **Stage Comments**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr comments-stage --pr-number {mr} --plan-id {plan_id}
   ```
   Output reports `count_fetched`, `count_skipped_noise`, `count_stored`, and `producer_mismatch_hash_id` (set when count_stored ≠ count_fetched − count_skipped_noise; the mismatch is also persisted as a Q-Gate finding under phase `5-execute` with title prefix `(producer-mismatch)`).

2. **Query Stored Findings**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query --plan-id {plan_id} --type pr-comment
   ```

3. **Process by Action Type** — the LLM reads each finding's `detail` (which carries the full body, kind, thread_id, author, path:line, comment_id) and decides code_change / explain / ignore. After acting on each finding, call `manage-findings resolve --hash-id {hash} --resolution fixed|suppressed|accepted`.

## Consumers

This skill is consumed by:
- `tools-integration-ci` — CI dispatcher routes GitLab operations here
- `workflow-pr-doctor` — PR diagnosis workflows
- `phase-6-finalize` — plan finalization with MR creation

## Comment Classification

`standards/comment-patterns.json` is now a **pre-filter only** — it drops obvious noise (bot signatures, "lgtm", "thanks!") before findings are written, but is **no longer the decision authority** for the action category. Classification of surviving comments belongs to the LLM consumer, which reads the full body from each finding's `detail` field.

## Error Handling

| Failure | Action |
|---------|--------|
| fetch-comments failure | Report error to caller with stderr details |
| triage failure | Log warning, skip comment, continue |
| CI router failure | Log warning, continue — best-effort |

## Related

- `plan-marshall:tools-integration-ci` — Central CI dispatcher
- `plan-marshall:workflow-integration-github` — GitHub provider counterpart
- `plan-marshall:workflow-pr-doctor` — PR diagnosis workflows
