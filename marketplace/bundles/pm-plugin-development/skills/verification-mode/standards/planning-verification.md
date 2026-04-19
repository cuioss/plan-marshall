# Planning-Specific Verification Protocol

Applies when `scope: planning` is specified. These checks supplement the base verification mode with planning command/skill access patterns.

## Before Each Operation

1. Check if operation will access .plan files directly
2. Verify manage-* script is being used instead

## After Each Phase Completes (MANDATORY)

**CRITICAL**: Execute the **Post-Phase Verification Protocol** after EVERY phase transition (1-init→3-outline, 4-plan→5-execute, 5-execute→6-finalize, 6-finalize completion). This is NOT optional.

**6-finalize ORDERING**: For 6-finalize, run the verification protocol **between** the phase transition (Step 9: `manage-status transition --completed 6-finalize`) and the archive (Step 10: `manage-status archive`). The archive moves plan files to `.plan/archived-plans/`, making `manage-status read` fail with `file_not_found`. Always verify before archiving.

Load and follow the protocol from `standards/planning-compliance.md`:

```
Read standards/planning-compliance.md
```

The protocol has **4 steps** - ALL are MANDATORY:

| Step | Check | Action |
|------|-------|--------|
| 1 | Chat History Error Check | Scan for tool failures, error messages |
| 2 | Script Execution Log Check | See command below, look for ERROR entries |
| 3 | **Workflow Skill API Contract Verification** | **CRITICAL** - See commands below |
| 4 | Status Consistency Check | See command below |

**Step 2 Command**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging read --plan-id {plan_id} --type script
```

**Step 4 Command**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read --plan-id {plan_id}
```

**Step 3 Contract Verification Details**:

| Completed Phase | Contract |
|-----------------|----------|
| 1-init | references.json required fields (domains) |
| 3-outline | solution-outline-standard.md |
| 4-plan | task-contract.md |
| 5-execute | task verification criteria |

**Exact Verification Commands** (copy-paste ready):

**1-Init Phase** - Verify references.json:
```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references read --plan-id {plan_id}
```

**2-Outline Phase** - Validate solution outline:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline validate --plan-id {plan_id}
```

**3-Plan Phase** - List and verify each task:
```bash
# List all tasks
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list --plan-id {plan_id}

# Get each task by number (replace {N} with 1, 2, 3, etc.)
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get --plan-id {plan_id} --task {N}

# Verify work-log has entry for each task creation
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging read --plan-id {plan_id} --type work
# Check output contains "[ARTIFACT]" entries for each TASK-N created
```

**Execute Phase** - Run task verification commands:
```bash
# Get task to retrieve verification.commands
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks get --plan-id {plan_id} --task {N}

# Then execute each command from the task's verification.commands array
```

**If ANY step fails** → STOP, analyze, present to user, wait for decision.

## After Each Operation (Non-Phase)

1. Query work-log for recent entry matching operation
2. Query status for consistency with expected phase
3. Report any discrepancies

## Planning Compliance Violations

These checks apply ONLY when `scope: planning` is specified:

**Single Allowed `.plan` Access Pattern**:
```bash
python3 .plan/execute-script.py {notation} {subcommand} {args...}
```

This is the ONLY allowed way to interact with `.plan` files. All other access is a violation.

**Allowed Direct Write Pattern**:
- `Write(.plan/plans/{plan_id}/solution_outline.md)` is permitted when the path
  was obtained via `manage-solution-outline resolve-path` and is immediately
  followed by `manage-solution-outline validate` (or `write`/`update`). This replaces heredoc stdin.

**Prohibited `.plan` Access** (ALL violations):
- Direct Read/Write/Edit of ANY `.plan/**` file (except via execute-script.py invocation or the allowed direct write pattern above)
- Direct Read/Write/Edit of `.plan/plans/*/status.toon`
- Direct Read/Write/Edit of `.plan/plans/*/references.json`
- Direct Read/Write/Edit of `.plan/plans/*/work.log`
- Direct Read/Write/Edit of `.plan/local/marshall-state.toon`
- Direct Read/Write/Edit of `.plan/local/logs/*.log`
- Direct Read/Write/Edit of `.plan/local/lessons-learned/*.md`
- Direct access to goals/tasks directories
- Glob patterns targeting `.plan/**`
- Bash find/ls/cat commands accessing `.plan/` structure
- Missing work.log entry after significant operation
- Status not updated after phase transition
- Artifacts created without manage-* scripts

**Rationale**: All `.plan` access must go through manage-* scripts to ensure:
- Consistent audit trail via script execution logging
- Validation and error handling
- Single source of truth for file format changes

## Example Planning Violation

```
User: Continue executing the current plan

Claude: Verification Mode Active

Checking plan status...

## PLANNING COMPLIANCE Violation Detected

### Issue Detected
Direct .plan file access bypassing manage-* API

### Context
- **Operation**: Read
- **Target**: .plan/plans/jwt-auth/status.toon
- **Expected**: Use `python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read --plan-id jwt-auth`
- **Actual**: Direct file read attempted

### Root Cause Analysis
Command is reading status.toon directly instead of using
`python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read`.
This bypasses audit trail and validation.

### Impact Assessment
| Aspect | Impact |
|--------|--------|
| Blocking | No - but should not proceed |
| Data Loss Risk | No (read-only) |
| Audit Trail | Not broken but inconsistent pattern |
| Maintainability | Poor - mixed access patterns |

### Options
1. **Use plan-marshall:manage-status:manage_status**: Consistent abstraction layer
2. **Proceed with warning**: Log deviation but continue

### Recommendation
Use `python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read` for all status access

---
**Verification Mode Active** - Awaiting user decision before proceeding.
```

## Example Post-Operation Audit

```
User: (approved using plan-marshall:manage-status:manage_status)

Claude: Task TASK-001 completed successfully.

## POST-OPERATION Audit Verification

### Operation Completed
Marked TASK-001 as complete, transitioned to TASK-002

### Work-Log Check
entries[1]{timestamp,type,phase,summary}:
2025-12-07T14:30:00Z,outcome,execute,Completed TASK-001: Implement JWT generator

### Status Check
current_phase: 5-execute
phases[7]{name,status}:
1-init,done
2-refine,done
3-outline,done
4-plan,done
5-execute,in_progress
6-finalize,pending

### Verification Result
| Check | Status | Notes |
|-------|--------|-------|
| Work-log entry exists | Pass | Entry within last 5 seconds |
| Correct type | Pass | outcome matches task completion |
| Correct phase | Pass | 5-execute phase |
| Meaningful summary | Pass | Describes completed task |
| Status consistent | Pass | 5-execute phase in_progress |

### Assessment
PASS - All audit trail and status checks verified
```
