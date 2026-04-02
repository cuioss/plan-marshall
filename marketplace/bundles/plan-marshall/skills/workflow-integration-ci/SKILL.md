---
name: workflow-integration-ci
description: PR review response workflow - fetch comments, triage, and respond to review feedback (GitHub and GitLab)
user-invocable: false
---

# PR Workflow Skill (Provider-Agnostic)

Handles PR review comment workflows - fetching comments, triaging them, and generating appropriate responses. Works with both GitHub and GitLab via the unified `tools-integration-ci` abstraction.

## Enforcement

**Execution mode**: Fetch PR review comments, triage each for action, implement fixes or generate responses, resolve threads.

**Prohibited actions:**
- Never resolve review comments without addressing the reviewer's concern
- Never force-push or amend published commits in response to reviews
- Never dismiss reviews without documented justification

**Constraints:**
- Each workflow step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- Review comment responses must explain the fix or provide rationale for disagreement
- CI wait timeout must be respected with user prompt on expiry

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `pr` | optional | PR number (auto-detects current branch's PR if omitted) |
| `unresolved-only` | optional | Only return unresolved comments (fetch-comments) |

## What This Skill Provides

### Workflows

1. **Fetch Comments Workflow** - Retrieves PR review comments via `tools-integration-ci` abstraction (GitHub or GitLab)

2. **Handle Review Workflow** - Processes and responds to comments, triages each for appropriate action, implements code changes or generates explanations

### Internal Dependencies

The `pr.py` script imports `ci.py`, `github.py`, and `gitlab.py` directly from `tools-integration-ci` (via PYTHONPATH). This avoids subprocess overhead but creates a compile-time dependency on those modules' internal API (`get_provider()`, `view_pr_data()`, `fetch_pr_comments_data()`). If `tools-integration-ci` refactors these functions, `pr.py` must be updated in lockstep.

## When to Activate This Skill

- Responding to PR review comments
- Processing review feedback
- Implementing reviewer-requested changes
- Generating explanations for reviewers

## Workflows

### Workflow 1: Fetch Comments

**Purpose:** Fetch all review comments for a PR.

**Input:** PR number (optional, defaults to current branch's PR)

**Steps:**

1. **Get PR Comments via CI Integration**

   Use the `pr-comments` command from marshal.json (provider-agnostic):

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments \
       --pr-number {number} [--unresolved-only]
   ```

   Or use the workflow script for additional processing:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr fetch-comments [--pr {number}]
   ```

   Output (TOON format):
   ```toon
   status: success
   operation: pr_comments
   provider: github|gitlab
   pr_number: 123
   total: N
   unresolved: N

   comments[N]{id,thread_id,author,body,path,line,resolved,created_at}:
   c1	PRRT_abc	alice	Fix security issue	src/Auth.java	42	false	2025-01-15T10:30:00Z
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
   python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage-batch --comments '[{comment1}, {comment2}, ...]'
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

The context is injected into the comment object's `context` field. Comments that reference identifiers found in the context are boosted from `ignore` to `code_change`.

**Output:** TOON with action decision

### pr.py triage-batch

**Purpose:** Triage multiple comments in a single call, reducing subprocess overhead.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage-batch --comments '[{"id":"C1", "body":"..."}, ...]'
```

**Output:** TOON with results array and summary counts

## Comment Classification

| Pattern | Action | Priority |
|---------|--------|----------|
| security, vulnerability, injection | code_change | high |
| bug, error, fix, broken | code_change | high |
| please add/remove/change | code_change | medium |
| rename, variable name, typo | code_change | low |
| nit:, nitpick: | code_change | low |
| why, explain, reasoning, ? | explain | low |
| lgtm, approved, looks good | ignore | none |

## Triage Override Guidance

The script triage uses regex pattern matching and will sometimes misclassify nuanced comments. When the script's `action` or `priority` doesn't match the semantic intent of the comment, override it. For example, "Why did you fix it this way?" semantically asks for an explanation even though it contains the word "fix". Use the script result as a starting point, not a final answer.

Note: The classification priority is code_change > ignore > explain. This means actionable content always wins — "LGTM, but please fix the typo" is classified as `code_change`, not `ignore`.

## Error Handling

| Failure | Action |
|---------|--------|
| fetch-comments failure | Report error to caller with stderr details. Do not proceed to triage. |
| triage failure | Log warning, skip the comment, continue processing remaining comments. |
| CI router failure (thread-reply, resolve-thread) | Log warning, continue — replies and resolutions are best-effort. |

## Integration

### Related Skills
- **workflow-integration-sonar** - Often used together in PR workflows
- **workflow-integration-git** - Commits changes after responses
- **workflow-pr-doctor** - Orchestrates this skill with Sonar and git workflows
