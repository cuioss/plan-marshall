---
name: verify-plan
description: Verify consistency across all artifacts of a plan
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Verify Plan Consistency

Reads all plan artifacts and cross-checks them for consistency. Reports findings.

## PARAMETERS

**plan** - Optional plan_id. If omitted, auto-detect the active plan.

## Step 1: Resolve Plan

If `plan` parameter provided, use it. Otherwise auto-detect:

```bash
python3 .plan/execute-script.py pm-workflow:manage-lifecycle:manage-lifecycle list
```

Pick the plan with `in_progress` phase. If multiple, pick most recently updated. If none, report "No active plan found" and stop.

Store as `{plan_id}`.

## Step 2: Gather All Artifacts

Read these in parallel — collect all outputs before analyzing:

```bash
# A: Status
python3 .plan/execute-script.py pm-workflow:manage-status:manage_status read --plan-id {plan_id}

# B: References
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references read --plan-id {plan_id}

# C: Solution outline
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline read --plan-id {plan_id}

# D: Solution outline validation
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline validate --plan-id {plan_id}

# E: Task list
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks list --plan-id {plan_id}

# F: Assessments summary
python3 .plan/execute-script.py pm-workflow:manage-assessments:manage-assessments query --plan-id {plan_id} --certainty CERTAIN_INCLUDE

# G: Script execution log (errors only)
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read --plan-id {plan_id} --type script
```

If an artifact does not exist yet (phase not reached), note it and skip. Only check artifacts that should exist given the current phase.

**Phase → Required Artifacts:**

| Phase reached | Required |
|---------------|----------|
| 1-init done | A, B |
| 2-refine done | A, B |
| 3-outline done | A, B, C, D, F |
| 4-plan done | A, B, C, D, E, F |
| 5-execute+ | A, B, C, D, E, F |

## Step 3: Read Individual Tasks

For each task from E, read full task content:

```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get --plan-id {plan_id} --number {N}
```

## Step 4: Cross-Check Consistency

Run these checks. For each, record PASS or FAIL with detail.

### 4a: References ↔ Outline

- Every file in `references.json → affected_files` appears in at least one deliverable's "Affected files"
- Every file in any deliverable's "Affected files" appears in `references.json → affected_files`
- Symmetric difference = FAIL

### 4b: Outline ↔ Tasks

- Every deliverable number (1..N) in the outline has at least one task with `deliverable: N`
- Every task's `deliverable` value points to a deliverable that exists in the outline
- Orphan tasks or uncovered deliverables = FAIL

### 4c: Task Dependencies

- Every `depends_on` entry (e.g., "TASK-3") references a task number that exists
- No circular dependencies
- Dangling reference = FAIL

### 4d: Task File Paths

- Every file path in task `steps[].title` (when it looks like a path) exists on disk
- Use `ls` to verify. Missing file = FAIL

### 4e: Assessments ↔ Outline

- Every CERTAIN_INCLUDE assessment file_path appears in at least one deliverable
- Every deliverable affected file has a CERTAIN_INCLUDE assessment
- Mismatch = FAIL

### 4f: Script Log

- Scan script execution log for `[ERROR]` entries
- Any errors = FAIL with the error lines

### 4g: Status Progression

- Phases are in valid order (no done phase after a pending phase, except current in_progress)
- current_phase matches the first in_progress phase

## Step 5: Report

Present results as a single table:

```
## Plan Consistency: {plan_id}

| # | Check | Result | Detail |
|---|-------|--------|--------|
| a | References ↔ Outline | PASS/FAIL | {detail} |
| b | Outline ↔ Tasks | PASS/FAIL | {detail} |
| c | Task Dependencies | PASS/FAIL | {detail} |
| d | Task File Paths | PASS/FAIL | {detail} |
| e | Assessments ↔ Outline | PASS/FAIL | {detail} |
| f | Script Log Errors | PASS/FAIL | {detail} |
| g | Status Progression | PASS/FAIL | {detail} |

**Verdict**: {CONSISTENT / INCONSISTENT — N issues found}
```

For each FAIL, include the specific mismatches (files, task numbers, etc.).

## CRITICAL RULES

1. **Read-only** — this command never modifies any artifact
2. **Use manage-* scripts** — never read .plan files directly
3. **Report all findings** — do not stop at first failure
4. **Skip unavailable artifacts** — if phase hasn't produced an artifact yet, skip checks that need it
5. **No fixes** — only report. User decides what to do with findings
