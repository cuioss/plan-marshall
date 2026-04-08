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
  ├─> gitlab.py (GitLab operations via glab CLI)
  ├─> pr.py (comment fetch, triage)
  └─> triage_helpers (ref-toon-format) — shared triage, error handling
```

This skill is the GitLab provider in the CI provider model. The central dispatcher (`tools-integration-ci:ci`) routes to this skill's `gitlab.py` for all GitLab operations.

## Usage Examples

```bash
# Fetch comments for current branch's MR
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:pr fetch-comments

# Fetch comments for specific MR
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:pr fetch-comments --pr 123

# Triage a single comment
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:pr triage --comment '{"id":"C1","body":"Fix this","path":"src/Main.java","line":42}'
```

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| gitlab | `plan-marshall:workflow-integration-gitlab:gitlab` | GitLab operations via glab CLI |
| pr | `plan-marshall:workflow-integration-gitlab:pr` | MR comment fetch and triage |

## Consumers

This skill is consumed by:
- `tools-integration-ci` — CI dispatcher routes GitLab operations here
- `workflow-pr-doctor` — PR diagnosis workflows
- `phase-6-finalize` — plan finalization with MR creation

## Comment Classification

Classification patterns are data-driven — loaded from `standards/comment-patterns.json`. Classification priority: `code_change(high)` > `code_change(medium/low)` > `ignore` > `explain`.

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
