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

## What This Skill Provides

### Workflows (Absorbs 2 Agents)

1. **Fetch Comments Workflow** - Retrieves PR review comments
   - Uses `tools-integration-ci` abstraction (GitHub or GitLab)
   - Replaces: review-comment-fetcher agent

2. **Handle Review Workflow** - Processes and responds to comments
   - Triages each comment for appropriate action
   - Implements code changes or generates explanations
   - Replaces: review-comment-triager agent

3. **Automated Review Lifecycle** - Complete CI-wait → fetch → triage → respond → resolve cycle
   - Used by phase-6-finalize when `3_automated_review == true`
   - Orchestrates Workflows 1 and 2 with CI wait and thread resolution

## When to Activate This Skill

- Responding to PR review comments
- Processing review feedback
- Implementing reviewer-requested changes
- Generating explanations for reviewers
- Running automated review lifecycle during finalize phase

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

2. **Triage Each Comment**
   For each unresolved comment:

   Script: `plan-marshall:workflow-integration-ci`

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage --comment '{json}'
   ```

   Script outputs decision:
   ```toon
   comment_id: ...
   action: code_change|explain|ignore
   reason: ...
   priority: high|medium|low|none
   suggested_implementation: ...
   ```

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

   **For ignore:**
   - No action required
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

### Workflow 3: Automated Review Lifecycle

**Purpose:** Complete automated review cycle for a PR — wait for CI, fetch review comments, triage, respond, and resolve threads. Used by phase-6-finalize when `3_automated_review == true`.

**Input:**
- `plan_id` — for logging and Q-Gate findings
- `pr_number` — PR number (from phase-6-finalize Step 4 or pr-view)
- `review_bot_buffer_seconds` — seconds to wait after CI for review bots (from config)

**Steps:**

1. **Wait for CI**

   Use the built-in `ci wait` command which handles polling internally:

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
     --pr-number {pr_number}
   ```

   **Bash tool timeout**: 1800000ms (30-minute safety net). Internal timeout managed by script.

   - **`final_status: success`** → proceed to step 2
   - **`final_status: failure`** → return `{status: ci_failure, details: ...}` for loop-back
   - **`status: timeout`** → ask user (continue/skip/abort)

2. **Buffer for Review Bots**

   Wait for automated review bots (Gemini Code Assist, etc.) to post comments:

   ```bash
   sleep {review_bot_buffer_seconds}
   ```

3. **Fetch Comments**

   Use Workflow 1 (Fetch Comments) with `--unresolved-only`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr fetch-comments --pr {pr_number} --unresolved-only
   ```

4. **Triage Each Comment**

   Use Workflow 2 (Handle Review) triage for each unresolved comment:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-ci:pr triage --comment '{comment_json}'
   ```

5. **Process by Action Type**

   **ID format rules** (from fetch-comments output):
   - `thread-reply --thread-id`: Use the comment's `id` field (GraphQL node ID, format: `PRRC_kwDO...`). This is the `inReplyTo` target.
   - `resolve-thread --thread-id`: Use the `thread_id` field (GraphQL node ID, format: `PRRT_kwDO...`).
   - NEVER use numeric IDs — GitHub GraphQL requires global node IDs.

   For each triaged comment:

   **code_change** (requires implementation):
   - Persist as Q-Gate finding:
     ```bash
     python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
       qgate add --plan-id {plan_id} --phase 6-finalize --source qgate \
       --type pr-comment --title "{comment summary}" \
       --detail "{comment body} at {path}:{line}"
     ```
   - Reply acknowledging the finding:
     ```bash
     python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
         --pr-number {pr_number} --thread-id {comment_id} --body "Acknowledged — creating fix task."
     ```

   **explain** (reply with explanation):
   - Generate explanation based on code context
   - Reply to thread:
     ```bash
     python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr thread-reply \
         --pr-number {pr_number} --thread-id {comment_id} --body "{explanation}"
     ```
   - Resolve thread:
     ```bash
     python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
         --pr-number {pr_number} --thread-id {thread_id}
     ```

   **ignore** (dismiss):
   - Resolve thread:
     ```bash
     python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr resolve-thread \
         --pr-number {pr_number} --thread-id {thread_id}
     ```

6. **Return Summary**

**Output:**
```toon
status: success
pr_number: {pr_number}
ci_status: success
comments_total: {N}
comments_unresolved: {N}
processed:
  code_changes: {N}
  explanations: {N}
  ignored: {N}
threads_resolved: {N}
loop_back_needed: {true|false}
findings_created: {N}
```

If `loop_back_needed == true`, phase-6-finalize creates fix tasks and loops back to phase-5-execute.

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

**Output:** TOON with action decision

## References (Load On-Demand)

### Review Response Guide
```
Read references/review-response-guide.md
```

Provides:
- Comment classification patterns
- Response templates
- Best practices for reviewer communication

## Comment Classification

| Pattern | Action | Priority |
|---------|--------|----------|
| security, vulnerability, injection | code_change | high |
| bug, error, fix, broken | code_change | high |
| please add/remove/change | code_change | medium |
| rename, variable name, typo | code_change | low |
| why, explain, reasoning, ? | explain | low |
| lgtm, approved, looks good | ignore | none |

## Integration

### Commands Using This Skill
- **/pr-handle-pull-request** - Full PR workflow
- **/pr-respond-to-review-comments** - Comment response

### Related Skills
- **sonar-workflow** - Often used together in PR workflows
- **git-workflow** - Commits changes after responses

## Quality Verification

- Self-contained with relative path pattern
- Progressive disclosure (references loaded on-demand)
- Scripts output TOON for machine processing
- Both fetcher and triager agents absorbed
- Clear workflow definitions
- Provider-agnostic via tools-integration-ci

## References

- tools-integration-ci: `plan-marshall:tools-integration-ci` skill
- GitHub CLI: https://cli.github.com/
- GitLab CLI: https://gitlab.com/gitlab-org/cli
- Code Review Best Practices: https://google.github.io/eng-practices/review/
