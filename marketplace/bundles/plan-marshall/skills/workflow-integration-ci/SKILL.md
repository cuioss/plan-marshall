---
name: workflow-integration-ci
description: PR review comment workflow - fetch comments and triage for action classification (GitHub and GitLab via tools-integration-ci)
user-invocable: false
---

# CI Integration Workflow Skill (Provider-Agnostic)

Handles PR review comment workflows - fetching comments and triaging them into action categories (code_change, explain, ignore). The script provides fetch and triage operations; the calling LLM implements responses and thread resolution. Works with both GitHub and GitLab via the unified `tools-integration-ci` abstraction.

## Enforcement

**Execution mode**: Fetch PR review comments, triage each for action, implement fixes or generate responses, resolve threads.

**Prohibited actions:**
- Never resolve review comments without addressing the reviewer's concern
- Never dismiss reviews without documented justification

**Constraints:**
- Review comment responses must explain the fix or provide rationale for disagreement
- CI wait timeout must be respected with user prompt on expiry

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `pr` | optional | PR number (auto-detects current branch's PR if omitted) |
| `unresolved-only` | optional | Only return unresolved comments (fetch-comments) |

### Shared Infrastructure

Uses `triage_helpers` from `ref-toon-format` for triage handlers, error codes, and TOON serialization.

## Prerequisites

```
Skill: plan-marshall:tools-integration-ci
```

The `tools-integration-ci` skill provides the CI router (`ci.py`, `github.py`, `gitlab.py`) for provider abstraction.

## Usage Examples

```bash
# Fetch comments for current branch's PR
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr fetch-comments

# Fetch comments for specific PR
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr fetch-comments --pr 123

# Triage a single comment
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage --comment '{"id":"C1","body":"Fix this","path":"src/Main.java","line":42}'

# Batch triage multiple comments
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage-batch --comments '[{"id":"C1","body":"Bug here"},{"id":"C2","body":"LGTM"}]'
```

## Architecture

```
workflow-integration-ci (PR comment workflow)
  ├─> tools-integration-ci (provider abstraction: GitHub/GitLab)
  └─> triage_helpers (ref-toon-format) — shared triage, error handling
```

### Internal Dependencies

The `pr.py` script imports `ci.py`, `github.py`, and `gitlab.py` directly from `tools-integration-ci` (via PYTHONPATH). This creates a compile-time dependency on those modules' internal API (`get_provider()`, `view_pr_data()`, `fetch_pr_comments_data()`). If `tools-integration-ci` refactors these functions, `pr.py` must be updated in lockstep. The provider contract is validated at import time.

> **Design note:** This skill uses direct Python imports for provider abstraction (code-level coupling), unlike `workflow-integration-sonar` and `workflow-permission-web` which use data-driven JSON config files. The import approach was chosen because CI provider logic requires function-level abstraction (GitHub vs GitLab APIs), not just data-driven classification.

## Workflows

### Workflow 1: Fetch Comments

**Purpose:** Fetch all review comments for a PR.

**Input:** PR number (optional, defaults to current branch's PR)

**Steps:**

1. **Get PR Comments via CI Integration**

   Use the workflow script (recommended — handles provider detection and output structuring):

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr fetch-comments [--pr {number}]
   ```

   Alternatively, use the low-level CI router directly (when you only need raw comments without structuring):

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments \
       --pr-number {number} [--unresolved-only]
   ```

   Output (TOON format):
   ```toon
   pr_number: 123
   provider: github|gitlab
   total_comments: N
   unresolved_count: N
   comments:
     - id: PRRC_abc
       thread_id: PRRT_abc
       author: alice
       body: Fix security issue
       path: src/Auth.java
       line: 42
       resolved: false
       created_at: 2025-01-15T10:30:00Z
   status: success
   ```

2. **Return Comment List**

**Output:** Structured list of comments for triage

---

### Workflow 2: Handle Review

**Purpose:** Process review comments and respond appropriately.

**Input:** PR number or comment list from Fetch workflow

**Steps:**

1. **Get Comments**
   If not provided, use Fetch Comments workflow first.

2. **Triage All Comments (Batch)**
   Collect all unresolved comments into a JSON array and triage in a single call:

   Script: `plan-marshall:workflow-integration-ci`

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage-batch --comments '[{"id":"PRRC_abc","body":"Fix this bug","path":"src/Main.java","line":42,"author":"alice"},{"id":"PRRC_def","body":"LGTM","path":null,"line":null,"author":"bob"}]'
   ```

   Script outputs all decisions at once:
   ```toon
   results[N]:
     - comment_id: ...
       action: code_change|explain|ignore
       reason: ...
       priority: high|medium|low|none
       suggested_implementation: ...
   summary:
     total: N
     code_change: N
     explain: N
     ignore: N
   status: success
   ```

   For single-comment edge cases, `triage --comment '{json}'` is also available.

3. **Process by Action Type**

   **For code_change:**
   - Read file at comment location
   - Implement suggested change using Edit tool
   - Reply to comment with commit reference

   **For explain:**
   - Generate explanation based on code context
   - Reply to comment via CI router:
     ```bash
     python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply \
         --pr-number {pr} --body "..."
     ```
   - Resolve the thread after replying:
     ```bash
     python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
         --pr-number {pr} --thread-id {thread_id}
     ```

   **For ignore:**
   - Resolve the thread (no reply needed):
     ```bash
     python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
         --pr-number {pr} --thread-id {thread_id}
     ```
   - Log as skipped

4. **Group by Priority**
   - Process high priority first
   - Then medium, then low

5. **Return Summary**

**Output:**
```toon
pr_number: 123
processed:
  code_changes: 3
  explanations: 1
  ignored: 1
files_modified[1]:
  - ...
status: success
```

---

## Scripts

Script: `plan-marshall:workflow-integration-ci` → `pr.py`

### pr.py fetch-comments

**Purpose:** Fetch PR review comments from GitHub.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr fetch-comments [--pr <number>]
```

**Requirements:** gh CLI installed and authenticated

**Output:** TOON with comments array

### pr.py triage

**Purpose:** Analyze a single comment and determine action.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage --comment '{"id":"...", "body":"...", ...}'
```

**Optional:** Pass `--context` with surrounding code to improve classification accuracy for ambiguous comments:
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage \
    --comment '{"id":"C1", "body":"This getValue call..."}' \
    --context "public String getValue() { return this.value; }"
```

The context is injected into the comment object's `context` field. Comments longer than 20 characters that reference identifiers found in the context are boosted from `ignore` to `code_change`. Short comments (<20 chars) skip context matching since they rarely contain meaningful code references.

**Output:** TOON with action decision

### pr.py triage-batch

**Purpose:** Triage multiple comments in a single call, reducing subprocess overhead.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage-batch --comments '[{"id":"C1", "body":"..."}, ...]'
```

**Output:** TOON with results array and summary counts

## Comment Classification

Classification patterns are data-driven — loaded from `standards/comment-patterns.json`:

| Pattern | Action | Priority |
|---------|--------|----------|
| security, vulnerability, injection | code_change | high |
| bug, error, fix, broken | code_change | high |
| please add/remove/change | code_change | medium |
| rename, variable name, typo | code_change | low |
| nit:, nitpick: | code_change | low |
| why, explain, reasoning, ? | explain | low |
| lgtm, approved, looks good | ignore | none |

To add or update comment classification patterns, edit `standards/comment-patterns.json` instead of the script.

## Triage Override Guidance

The script triage uses regex pattern matching and will sometimes misclassify nuanced comments. When the script's `action` or `priority` doesn't match the semantic intent of the comment, override it. For example, "Why did you fix it this way?" semantically asks for an explanation even though it contains the word "fix". Use the script result as a starting point, not a final answer.

Note: The classification priority is code_change > ignore > explain. This means actionable content always wins — "LGTM, but please fix the typo" is classified as `code_change`, not `ignore`.

## Error Handling

Error codes follow the shared `ErrorCode` enum from `triage_helpers` (`NOT_FOUND`, `INVALID_INPUT`, `PARSE_ERROR`, `PROVIDER_NOT_CONFIGURED`).

| Failure | Action |
|---------|--------|
| fetch-comments failure | Report error to caller with stderr details. Do not proceed to triage. |
| triage failure | Log warning, skip the comment, continue processing remaining comments. |
| CI router failure (thread-reply, resolve-thread) | Log warning, continue — replies and resolutions are best-effort. |

## Related

Orchestrated by `plan-marshall:workflow-pr-doctor` alongside `workflow-integration-sonar` and `workflow-integration-git`.
