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
- Each workflow step that invokes a script has an explicit bash code block with the full `python3 .plan/execute-script.py` command
- Fixes require build verification before committing
- Review comment responses must explain the fix or provide rationale for disagreement
- All user interactions use `AskUserQuestion` tool with proper YAML structure
- CI wait timeout (30 minutes) must be respected with user prompt on expiry

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `pr` | optional | Pull request number/URL (auto-detects current if not provided) |
| `checks` | optional | build\|reviews\|sonar\|all (default: all) |
| `auto-fix` | optional | Auto-apply fixes without prompting (default: false). CLI flag is boolean — pass `auto-fix=true` to enable, omit to use default or handoff value |
| `wait` | optional | Wait for CI/Sonar to complete (default: true) |
| `handoff` | optional | Handoff structure from previous phase (JSON, see schema below) |
| `max-fix-attempts` | optional | Maximum fix-verify-commit cycles before giving up (default: 3) |

## Mode Selection

This skill operates in two modes based on invocation context:

| Mode | Trigger | Steps |
|------|---------|-------|
| **Interactive** (default) | `/workflow-pr-doctor` or explicit parameters | Steps 0-7 below |
| **Automated Review Lifecycle** | phase-6-finalize handoff with `decisions.automated_review: true` | See `standards/automated-review-lifecycle.md` |

## Prerequisites

Always loaded:
```
Skill: plan-marshall:workflow-integration-ci
Skill: plan-marshall:workflow-integration-sonar
Skill: plan-marshall:workflow-integration-git
```

Loaded on-demand (only when the specific check requires them):
```
Skill: plan-marshall:manage-architecture    # Step 5 BUILD_FAILURE only
Skill: plan-marshall:manage-findings        # Automated Review Lifecycle mode only
```

For orchestration context and shared infrastructure, see `ref-workflow-architecture` → "Workflow Skill Orchestration".

## Architecture

Delegates to skills:
```
/workflow-pr-doctor (orchestrator)
  ├─> workflow-integration-ci skill (Fetch Comments, Handle Review)
  │     └─> triage_helpers (ref-toon-format) — shared triage, error handling
  ├─> workflow-integration-sonar skill (Fetch Issues, Fix Issues)
  │     └─> triage_helpers (ref-toon-format) — shared triage, error handling
  ├─> workflow-integration-git skill (Commit workflow)
  │     └─> triage_helpers (ref-toon-format) — shared error handling
  └─> manage-architecture skill (Build command resolution)
```

All workflow scripts share `triage_helpers` from `ref-toon-format` for JSON parsing, TOON serialization, error codes, and batch triage processing.

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
/workflow-pr-doctor checks=all auto-fix=true
```

**Skip CI wait, fix current PR:**
```
/workflow-pr-doctor wait=false
```

**Script subcommands:**
```bash
# Generate diagnostic report
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor diagnose \
  --build-status failure --build-failures '[{"step":"test","message":"3 failed"}]'

# Parse handoff from phase-6
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor parse-handoff \
  --handoff '{"artifacts":{"pr_number":123}}'

# Check attempt limit
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor track-attempt \
  --category build --current 0
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
    "skip_sonar": false,
    "automated_review": false
  },
  "constraints": {
    "max_fix_attempts": 3,
    "protected_files": ["README.md"]
  }
}
```

Field notes:
- `skip_sonar`: When `true`, skip Sonar diagnosis entirely (equivalent to `checks` excluding `sonar`). Parsed and passed through by `parse-handoff` — the caller must check this value and skip the Sonar workflow accordingly.
- `automated_review`: When `true`, activates the Automated Review Lifecycle mode instead of the interactive workflow.

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

**Build**: `ci ci status --pr-number {pr}` → BUILD_FAILURE if `overall_status: failure`. If CI status check fails, report error and skip build diagnosis.

**Reviews**: workflow-integration-ci (Fetch Comments) → REVIEW_COMMENTS ({count}). If fetch fails, report error and skip review diagnosis.

**Sonar**: workflow-integration-sonar (Fetch Issues) → SONAR_QUALITY ({count}/{severity}). If Sonar MCP is unavailable, skip Sonar checks and report as "skipped — MCP not connected".

### Step 4: Generate Diagnostic Report

Use the `diagnose` script to aggregate data into a deterministic report:

```bash
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor diagnose \
    [--build-status success|failure] \
    [--build-failures '<json>'] [--review-comments '<json>'] [--sonar-issues '<json>']
```

Display format:
```
────────────────────────────────────────────────
PR Diagnostic Report: #{pr}
────────────────────────────────────────────────

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
1. Fetch build logs via `ci ci status --pr-number {pr}` — the `checks` array in the output contains per-check `name`, `status`, and `conclusion` fields; failed checks include a `details_url` for full logs
2. Identify failing step (compile, test, lint) from the check `name` field
3. Read failing files from the build log output (fetch via `details_url` or re-run locally)
4. Apply fix using Edit tool
5. Resolve build command via architecture API, then verify:
   ```
   Skill: plan-marshall:manage-architecture
   ```
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture resolve
   ```
   Use the returned `executable` to run verify.

**REVIEW_COMMENTS**: Delegate to workflow-integration-ci Workflow 2 (Handle Review). The CI skill handles: fetching comments, batch triage, and classifying actions. The pr-doctor then processes each action (code_change → Edit files, explain → reply, ignore → resolve thread) and commits via the git skill.

**SONAR_QUALITY**: Delegate to workflow-integration-sonar Workflow 2 (Fix Issues). The Sonar skill handles: batch triage and fix-vs-suppress classification. The pr-doctor then executes each action (fix → Edit files, suppress → add NOSONAR comment) and commits via the git skill.

**Protected files check**: Before applying any fix, check the file path against `protected_files` from the handoff constraints. If a fix would modify a protected file, skip that fix and report it as "skipped — protected file" in the summary. Do not prompt the user for each protected file — just skip and log.

**Iteration guard**: Maintain a counter per category (`build_attempts`, `sonar_attempts`, `review_attempts`) in the LLM's working memory, starting at 0. Increment after each fix → verify cycle. After reaching `max-fix-attempts` (default: 3) for a category, stop that category and report remaining issues to the user rather than looping indefinitely. The `track-attempt` subcommand is available for validation but simple counter arithmetic is preferred over a subprocess call for each iteration check.

### Step 6: Verify and Commit

After fixes:
1. Verify build passes (via architecture API)
2. Commit via workflow-integration-git skill (which includes artifact cleanup in Step 3)
3. Push to PR branch

### Step 7: Generate Summary

Display a final diagnostic summary:

```
PR #{pr} Summary
  Fixed: {count}
  Remaining: {count}
  Next action: {description}
```

---

### Mode: Automated Review Lifecycle

Autonomous CI → review → respond → resolve cycle, activated only via phase-6-finalize handoff with `decisions.automated_review: true`. Not invoked via `/workflow-pr-doctor` directly. See `standards/automated-review-lifecycle.md` for the full procedure.

**Input:** `plan_id`, `pr_number`, `review_bot_buffer_seconds`

**Output:**
```toon
status: success|ci_failure
loop_back_needed: true|false
```

---

## Scripts

Script: `plan-marshall:workflow-pr-doctor` → `pr_doctor.py`

### pr_doctor.py diagnose

**Purpose:** Aggregate CI, review, and Sonar data into a deterministic diagnostic report with categorized issues and recommended actions.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor diagnose \
    [--build-status success|failure] \
    [--build-failures '[{"step":"test","message":"3 tests failed"}]'] \
    [--review-comments '[{"priority":"high"}]'] \
    [--sonar-issues '[{"severity":"BLOCKER"}]']
```

**Parameters:**
- `--build-status`: Overall build status (`success` or `failure`)
- `--build-failures`: JSON array of build failure objects with `step` and `message` keys
- `--review-comments`: JSON array of unresolved review comments with `priority` key
- `--sonar-issues`: JSON array of Sonar issues with `severity` key

**Output** (TOON):
```toon
overall: pass|fail
build_status: PASS|FAIL|UNKNOWN
review_comments: 3
sonar_issues: 5
issues[N]{category,severity,detail}:
  - category: build|reviews|sonar
    severity: high|medium
    detail: ...
recommended_actions[N]:
  - Fix build failures before other issues
status: success
```

### pr_doctor.py track-attempt

**Purpose:** Check whether a fix attempt should proceed or stop, enforcing the `max-fix-attempts` iteration guard programmatically.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor track-attempt \
    --category build --current 0 [--max-attempts 3]
```

**Parameters:**
- `--category` (required): Fix category (`build`, `reviews`, `sonar`)
- `--current` (required): Current attempt count (0-based, pre-increment)
- `--max-attempts`: Maximum allowed attempts (default: 3)

**Output** (TOON):
```toon
category: build
attempt: 1
max_attempts: 3
remaining: 2
proceed: true
reason: within limit
status: success
```

### pr_doctor.py parse-handoff

**Purpose:** Parse and validate handoff JSON from phase-6-finalize, merge with explicit parameters. See Step 0 above for the handoff schema.

**Usage:**
```bash
python3 .plan/execute-script.py plan-marshall:workflow-pr-doctor:pr_doctor parse-handoff \
    --handoff '{"artifacts":{"pr_number":123},"decisions":{"auto_fix":true}}' \
    [--pr 456] [--checks build] [--auto-fix] [--max-fix-attempts 5]
```

**Output:** TOON with merged parameters and validation warnings. Explicit CLI parameters always take precedence over handoff values.

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

## Standards (Load On-Demand)

| Standard | When to Load |
|----------|-------------|
| `standards/automated-review-lifecycle.md` | Automated Review Lifecycle mode (phase-6-finalize handoff) |
| `standards/pr-doctor-config.json` | Adding/updating build step severity or valid checks |

## Related

See `ref-workflow-architecture` → "Workflow Skill Orchestration" for the full dependency graph and shared infrastructure documentation.
