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
# Fetch comments for current branch's PR
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr comments

# Fetch comments for specific PR
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_ops pr comments --pr-number 123

# Triage a single comment
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr triage --comment '{"id":"C1","body":"Fix this","path":"src/Main.java","line":42}'

# Batch triage multiple comments
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr triage-batch --comments '[{"id":"C1","body":"Bug here"},{"id":"C2","body":"LGTM"}]'
```

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| github_ops | `plan-marshall:workflow-integration-github:github_ops` | GitHub PR, CI, and issue operations via gh CLI |
| github_pr | `plan-marshall:workflow-integration-github:github_pr` | PR review comment triage (delegates to github_ops for fetch) |

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

### Workflow 2: Handle Review

**Purpose:** Process review comments and respond appropriately.

**GitHub GraphQL ID Format Rules:**

| Operation | Parameter | ID Field | Format Example |
|-----------|-----------|----------|----------------|
| `thread-reply --thread-id` | Comment's `thread_id` field | GraphQL node ID | `PRRT_kwDO...` |
| `resolve-thread --thread-id` | Comment's `thread_id` field | GraphQL node ID | `PRRT_kwDO...` |

Both operations take the same `PRRT_` thread id — pass the comment's `thread_id` field for either. The comment's `id` field (format `PRRC_...`) is never valid for `thread-reply` or `resolve-thread`.

**NEVER use numeric IDs** — GitHub GraphQL requires global node IDs.

**Steps:**

1. **Get Comments** — use Fetch Comments workflow with `--unresolved-only`
2. **Triage All Comments (Batch)**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr triage-batch --comments '[...]'
   ```
3. **Process by Action Type**

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

## Comment Classification

Classification patterns are data-driven — loaded from `standards/comment-patterns.json`. Classification priority: `code_change(high)` > `code_change(medium/low)` > `ignore` > `explain`.

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
