---
name: plan-marshall-workflow-integration-gitlab
description: GitLab provider for MR review workflows — fetch comments, triage, and respond to review feedback via glab CLI
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# GitLab CI Integration Workflow Skill

GitLab provider for the findings-pipeline `pr-comment` producer. Mirror of the GitHub provider's two-verb contract: `fetch_findings` (FIND — fetch MR review comments, apply the pre-filter `comment-patterns.json`, and file one `pr-comment` finding per surviving comment, quarantining the untrusted body under `raw_input.{body}`) and `post_responses` (RESPOND — apply already-decided triage dispositions back to the MR, keyed by `hash_id`). Triage is NOT on the provider surface. Uses the `glab` CLI for all GitLab operations.

> **Architectural context**: This SKILL.md owns the provider-side CLI surface. For the FIND → INGEST → one-TRIAGE → one-RESPOND flow that connects this provider to the unified ledger, the batched `manage-findings ingest` pass, the per-domain `ext-triage` consolidated triage, and the invariant gate, see [`ref-workflow-architecture/standards/findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md).

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

```text
workflow-integration-gitlab (GitLab MR comment workflow)
  ├─> gitlab_ops.py (GitLab operations via glab CLI)
  ├─> gitlab_pr.py (two-verb provider: fetch_findings + post_responses)
  └─> triage_helpers (ref-toon-format) — shared error handling
```

This skill is the GitLab provider in the CI provider model. The central dispatcher (`tools-integration-ci:ci`) routes to this skill's `gitlab_ops.py` for all GitLab operations.

## Usage Examples

```bash
# FIND: fetch + pre-filter + file one pr-comment finding per surviving comment (body quarantined under raw_input)
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr fetch_findings --pr-number 123 --plan-id EXAMPLE-PLAN

# RESPOND: apply already-decided triage dispositions back to the MR, keyed by hash_id
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr post_responses --pr-number 123 --plan-id EXAMPLE-PLAN

# Raw fetch (no filtering, no storage) — for ad-hoc inspection
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr fetch-comments --pr 123

# Consumer reads ingested findings via manage-findings (top-level fields only)
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list --plan-id EXAMPLE-PLAN --type pr-comment
```

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| gitlab_ops | `plan-marshall:workflow-integration-gitlab:gitlab_ops` | GitLab operations via glab CLI |
| gitlab_pr | `plan-marshall:workflow-integration-gitlab:gitlab_pr` | Two-verb provider: `fetch_findings` (FIND — fetch + pre-filter + file) and `post_responses` (RESPOND — apply triaged dispositions, keyed by hash_id) |

## Workflow: Handle Review (Producer-Side)

**Purpose:** Stage MR review comments into the per-type finding store, then let the LLM consumer drive classification and responses from the stored findings.

**FIND flow:** `fetch_findings` is the producer surface. It fetches review comments, applies the `comment-patterns.json` keyword pre-filter to drop obvious noise (bot signatures, "lgtm", etc.), and files one `pr-comment` finding per surviving comment (the untrusted body quarantined under `raw_input.{body}`). The batched `manage-findings ingest` pass then promotes the validated body to the clean top-level fields; the consolidated triage pass reads those top-level fields and decides dispositions, which `post_responses` transmits back. Triage is not on this provider surface.

**Steps:**

1. **FIND — file comments to the ledger**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr fetch_findings --pr-number {mr} --plan-id {plan_id}
   ```
   Output reports `count_fetched`, `count_skipped_noise`, `count_stored`, and `producer_mismatch_hash_id` (set when count_stored ≠ count_fetched − count_skipped_noise; the mismatch is also persisted as a Q-Gate finding under phase `5-execute` with title prefix `(producer-mismatch)`).

2. **Query Stored Findings**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list --plan-id {plan_id} --type pr-comment
   ```

3. **Process by Action Type** — the LLM reads each finding's `detail` (which carries the full body, kind, thread_id, author, path:line, comment_id) and decides code_change / explain / ignore. After acting on each finding, call `manage-findings resolve --hash-id {hash} --resolution fixed|suppressed|accepted`.

## Consumers

This skill is consumed by:
- `tools-integration-ci` — CI dispatcher routes GitLab operations here
- `workflow-pr-doctor` — PR diagnosis workflows
- `phase-6-finalize` — plan finalization with MR creation

## Comment Classification

`standards/comment-patterns.json` is a **pre-filter only** — it drops obvious noise (bot signatures, "lgtm", "thanks!") before findings are written. Classification of surviving comments belongs to the LLM consumer, which reads the full body from each finding's `detail` field.

## Error Handling

| Failure | Action |
|---------|--------|
| fetch-comments failure | Report error to caller with stderr details |
| triage failure | Log warning, skip comment, continue |
| CI router failure | Log warning, continue — best-effort |

## Canonical invocations

The canonical argparse surface for `gitlab_pr.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### fetch-comments

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr fetch-comments \
  [--pr PR] [--unresolved-only]
```

### fetch_findings

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr fetch_findings \
  --pr-number PR_NUMBER --plan-id PLAN_ID
```

### post_responses

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-gitlab:gitlab_pr post_responses \
  --pr-number PR_NUMBER --plan-id PLAN_ID
```

## Related

- `plan-marshall:tools-integration-ci` — Central CI dispatcher
- `plan-marshall:workflow-integration-github` — GitHub provider counterpart
- `plan-marshall:workflow-pr-doctor` — PR diagnosis workflows
