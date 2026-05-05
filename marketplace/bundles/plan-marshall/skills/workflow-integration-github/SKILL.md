---
name: workflow-integration-github
description: GitHub provider for PR review workflows — fetch comments, triage, and respond to review feedback via gh CLI
user-invocable: false
---

# GitHub CI Integration Workflow Skill

GitHub-specific PR review comment workflow — fetching comments and triaging them into action categories (code_change, explain, ignore). Uses the `gh` CLI for all GitHub operations.

## Enforcement

**Execution mode**: Fetch PR review comments, triage each for action, implement fixes or generate responses, resolve threads.

**Prohibited actions:**
- Never call `gh` directly from LLM context; all operations go through script API
- Never resolve review comments without addressing the reviewer's concern
- Never dismiss reviews without documented justification

**Constraints:**
- Review comment responses must explain the fix or provide rationale for disagreement
- CI wait timeout must be respected with user prompt on expiry

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `pr` | int | no | auto-detect | PR number (auto-detects current branch's PR if omitted) |
| `unresolved-only` | bool | no | false | Only return unresolved comments (`pr comments`) |

## Architecture

```
workflow-integration-github (GitHub PR comment workflow)
  ├─> github_ops.py (GitHub operations via gh CLI — PR, CI, issue)
  ├─> github_pr.py (PR comment triage — delegates to github_ops for fetch)
  └─> triage_helpers (ref-toon-format) — shared triage, error handling
```

This skill is the GitHub provider in the CI provider model. The central dispatcher (`tools-integration-ci:ci`) routes to this skill's `github_ops.py` for all GitHub operations.

## Usage Examples

```bash
# Producer-side: fetch + pre-filter + store one pr-comment finding per surviving comment
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr comments-stage --pr-number 123 --plan-id my-plan

# Raw fetch (no filtering, no storage) — for ad-hoc inspection
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr fetch-comments --pr 123

# LLM consumer reads stored findings via manage-findings
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query --plan-id my-plan --type pr-comment
```

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| github_ops | `plan-marshall:workflow-integration-github:github_ops` | GitHub PR, CI, and issue operations via gh CLI |
| github_pr | `plan-marshall:workflow-integration-github:github_pr` | Producer-side PR review comment fetcher (fetch + pre-filter + store) |

## Consumers

This skill is consumed by:
- `tools-integration-ci` — CI dispatcher routes GitHub operations here
- `workflow-pr-doctor` — PR diagnosis workflows
- `phase-6-finalize` — plan finalization with PR creation

## Workflows

### Workflow 1: Fetch Comments

**Purpose:** Fetch all review comments for a PR.

**Steps:**

1. **Get PR Comments**

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr comments [--pr-number {number}] [--unresolved-only]
   ```

2. **Return Comment List**

### Workflow 2: Handle Review (Producer-Side)

**Purpose:** Stage PR review comments into the per-type finding store, then let the LLM consumer drive classification and responses from the stored findings.

**Producer-side flow:** `comments-stage` is the only callable surface. It fetches review comments, applies the `comment-patterns.json` keyword pre-filter to drop obvious noise (bot signatures, "lgtm", etc.), and writes one `pr-comment` finding per surviving comment via `manage-findings add`. No script-side classification or batch-triage call is exposed to the LLM — the LLM reads the stored findings and decides per-finding action itself.

**GitHub GraphQL ID Format Rules:**

| Operation | Parameter | ID Field | Format Example |
|-----------|-----------|----------|----------------|
| `thread-reply --thread-id` | Comment's `thread_id` field | GraphQL node ID | `PRRT_kwDO...` |
| `resolve-thread --thread-id` | Comment's `thread_id` field | GraphQL node ID | `PRRT_kwDO...` |

Both operations take the same `PRRT_` thread ID — pass the comment's `thread_id` field for either. The comment's `id` field (format `PRRC_...`) is never valid for `thread-reply` or `resolve-thread`. The producer-side stager places `thread_id`, `comment_id`, `kind`, `author`, `path`, `line`, and the full body in the finding's `detail` field so downstream consumers can reconstruct any reply or resolve call.

**NEVER use numeric IDs** — GitHub GraphQL requires global node IDs.

**Steps:**

1. **Stage Comments**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr comments-stage --pr-number {pr} --plan-id {plan_id}
   ```
   Output reports `count_fetched`, `count_skipped_noise`, `count_stored`, and `producer_mismatch_hash_id` (set when count_stored ≠ count_fetched − count_skipped_noise; the mismatch is also persisted as a Q-Gate finding under phase `5-execute` with title prefix `(producer-mismatch)`).

2. **Query Stored Findings**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query --plan-id {plan_id} --type pr-comment
   ```

3. **Process by Action Type** — the LLM reads each finding's `detail` (which carries the full body, kind, thread_id, author, path:line, comment_id) and decides:

   **For code_change:** Read file, implement change, reply with commit reference
   **For explain:** Generate explanation, reply via:
   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply --pr-number {pr} --body "..."
   ```
   Resolve thread:
   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread --pr-number {pr} --thread-id {thread_id}
   ```
   **For ignore:** Resolve thread without replying

   After acting on each finding, the LLM should call `manage-findings resolve --hash-id {hash} --resolution fixed|suppressed|accepted` to mark progress.

## Comment Classification

`standards/comment-patterns.json` is now a **pre-filter only** — it drops obvious noise (bot signatures, "lgtm", "thanks!") before findings are written, but is **no longer the decision authority** for the action category. Classification of surviving comments belongs to the LLM consumer, which reads the full body from each finding's `detail` field.

## Error Handling

| Failure | Action |
|---------|--------|
| `pr comments` failure | Report error to caller with stderr details |
| triage failure | Log warning, skip comment, continue |
| CI router failure | Log warning, continue — best-effort |

## Related

- `plan-marshall:tools-integration-ci` — Central CI dispatcher
- `plan-marshall:workflow-integration-gitlab` — GitLab provider counterpart
- `plan-marshall:workflow-pr-doctor` — PR diagnosis workflows
