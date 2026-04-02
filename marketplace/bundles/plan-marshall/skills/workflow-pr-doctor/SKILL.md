---
name: workflow-pr-doctor
description: Diagnose and fix PR issues (build, reviews, Sonar)
user-invocable: true
---

# PR Doctor Skill

Diagnose and fix pull request issues with parameterized checks.

## Enforcement

**Execution mode**: Diagnose PR issues by category (build, reviews, Sonar), present report, fix with user approval unless auto-fix enabled.

**Prohibited actions:**
- Never force-push or amend published commits
- Never suppress Sonar issues without justification and user approval (unless auto-fix=true)
- Do not resolve review comments without addressing the reviewer's concern

**Constraints:**
- Fixes require build verification before committing
- Review comment responses must explain the fix or provide rationale for disagreement
- All user interactions use `AskUserQuestion` tool with proper YAML structure
- CI wait timeout (30 minutes) must be respected with user prompt on expiry

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `pr` | optional | Pull request number/URL (auto-detects current if not provided) |
| `checks` | optional | build\|reviews\|sonar\|all (default: all) |
| `auto-fix` | optional | Auto-apply fixes without prompting (default: false) |
| `wait` | optional | Wait for CI/Sonar to complete (default: true) |
| `handoff` | optional | Handoff structure from previous phase (JSON, see schema below) |
| `max-fix-attempts` | optional | Maximum fix-verify-commit cycles before giving up (default: 3) |

## Prerequisites

Load required skills:
```
Skill: plan-marshall:workflow-integration-ci
Skill: plan-marshall:workflow-integration-sonar
Skill: plan-marshall:workflow-integration-git
```

## Workflow

### Step 0: Process Handoff Input

If `handoff` parameter provided: Parse JSON with this schema:

```json
{
  "artifacts": {
    "pr_number": 123,
    "branch": "feature/my-feature",
    "commit_hash": "abc123",
    "plan_id": "my-plan"
  },
  "decisions": {
    "auto_fix": true,
    "checks": "all",
    "skip_sonar": false
  },
  "constraints": {
    "max_fix_attempts": 3,
    "protected_files": ["README.md"]
  }
}
```

Extract and merge with explicit parameters (explicit parameters take precedence).

### Step 1: Get PR Information

Auto-detect if not provided:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view
```

Validate: PR must have valid `pr_number` in TOON output.

### Step 2: Wait for Checks (If Requested)

If wait=true:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
    --pr-number {pr_number}
```

**Bash tool timeout**: 1800000ms (30-minute safety net).

On timeout, present using `AskUserQuestion`:

```
AskUserQuestion:
  questions:
    - question: "CI checks timed out after 30 minutes. How would you like to proceed?"
      header: "Timeout"
      options:
        - label: "Continue waiting"
          description: "Keep polling for another 30 minutes"
        - label: "Skip checks"
          description: "Proceed to diagnosis without waiting"
        - label: "Abort"
          description: "Stop PR doctor"
      multiSelect: false
```

### Step 3: Diagnose Issues

Based on `checks` parameter:

**Build**: `ci ci status --pr-number {pr}` → BUILD_FAILURE if `overall_status: failure`

**Reviews**: workflow-integration-ci (Fetch Comments) → REVIEW_COMMENTS ({count})

**Sonar**: workflow-integration-sonar (Fetch Issues) → SONAR_QUALITY ({count}/{severity})

### Step 4: Generate Diagnostic Report

```
═══════════════════════════════════════════════
PR Diagnostic Report: #{pr}
═══════════════════════════════════════════════

Build Status: {PASS|FAIL}
Review Comments: {count} unresolved
Sonar Issues: {count} ({severity breakdown})

Issues Found:
{per-category breakdown}

Recommended Actions:
{action list}
```

### Step 5: Fix Issues

Based on checks parameter:

**BUILD_FAILURE**: Resolve using the build system:
1. Fetch build logs via `ci ci status --pr-number {pr}`
2. Identify failing step (compile, test, lint)
3. Read failing files from error output
4. Apply fix using Edit tool
5. Resolve build command via architecture API, then verify:
   ```
   Skill: plan-marshall:manage-architecture
   ```
   Use `architecture resolve` to get the correct build executable, then run verify.

**REVIEW_COMMENTS**: Use workflow-integration-ci (Handle Review). For each: triage → fix/explain/acknowledge.

**SONAR_QUALITY**: Use workflow-integration-sonar (Fix Issues). For each: triage → fix/suppress (with approval if not auto-fix).

**Iteration guard**: Maintain a counter per category (`build_attempts`, `sonar_attempts`, `review_attempts`), starting at 0. Increment after each fix → verify cycle. After reaching `max-fix-attempts` (default: 3) for a category, stop that category and report remaining issues to the user rather than looping indefinitely.

### Step 6: Verify and Commit

After fixes: Verify build, commit via git workflow, push to PR branch.

### Step 7: Generate Summary

Display: `PASS {fixed} fixed, ⚠ {remaining} remaining, → {next_action}`

---

### Workflow: Automated Review Lifecycle

**Purpose:** Complete automated review cycle — wait for CI, fetch review comments, triage, respond, and resolve threads. Used by phase-6-finalize when `3_automated_review == true`.

**Input:** `plan_id`, `pr_number`, `review_bot_buffer_seconds`

**Steps:**

1. Wait for CI → `ci ci wait --pr-number {pr_number}` (30-min timeout)
2. Buffer for review bots → `sleep {review_bot_buffer_seconds}`
3. Fetch comments → workflow-integration-ci Fetch Comments with `--unresolved-only`
4. Triage each comment → workflow-integration-ci Handle Review triage
5. Process by action type (code_change → Q-Gate finding + reply, explain → reply + resolve, ignore → resolve)
6. Return summary with `loop_back_needed` flag

**Detailed reference:** Read `standards/automated-review-lifecycle.md` for full step-by-step commands, ID format rules, and error handling.

**Output:**
```toon
status: success|ci_failure
loop_back_needed: true|false
```

---

## Usage Examples

**Fix all PR issues:**
```
/workflow-pr-doctor pr=123
```

**Fix only Sonar issues:**
```
/workflow-pr-doctor pr=456 checks=sonar
```

**Auto-fix without prompts:**
```
/workflow-pr-doctor checks=all auto-fix
```

**Skip CI wait, fix current PR:**
```
/workflow-pr-doctor wait=false
```

## Architecture

Delegates to skills:
```
/workflow-pr-doctor (orchestrator)
  ├─> workflow-integration-ci skill (Fetch Comments, Handle Review)
  ├─> workflow-integration-sonar skill (Fetch Issues, Fix Issues)
  └─> workflow-integration-git skill (Commit workflow)
```

## Error Handling

| Failure | Action |
|---------|--------|
| PR not found | Report error. Verify branch has a PR or use `--pr` parameter. |
| CI wait timeout | Ask user via `AskUserQuestion` (continue/skip/abort). |
| CI status check fails | Report error with stderr. Skip build diagnosis. |
| Sonar MCP unavailable | Skip Sonar checks, report as "skipped — MCP not connected". |
| Fix breaks build | Revert fix, report to user. Do not commit broken state. |
| Max fix attempts reached | Report remaining issues with details. Do not loop further. |
| Push failure | Report error. Never force-push as fallback. |

## Related

| Skill | Purpose |
|-------|---------|
| `plan-marshall:workflow-integration-ci` | PR review comment handling |
| `plan-marshall:workflow-integration-sonar` | Sonar quality issue handling |
| `plan-marshall:workflow-integration-git` | Git commit workflow |
| `plan-marshall:task-standalone` | Implement tasks before PR |
