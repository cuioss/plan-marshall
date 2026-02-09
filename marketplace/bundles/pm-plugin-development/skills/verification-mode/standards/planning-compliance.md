# Planning Compliance Standard

Enforces proper access patterns and audit trail verification for planning-related commands and skills.

## Overview

Planning operations MUST use the official manage-* APIs for all .plan directory access. Direct file manipulation bypasses validation, audit trails, and can corrupt plan state. This standard detects violations and ensures proper audit trail population.

## Core Principles

1. **Abstraction Enforcement** - All .plan access goes through manage-* scripts
2. **Audit Trail Integrity** - Every operation records to work-log
3. **State Consistency** - Status reflects actual phase and progress
4. **No Silent Mutations** - All changes are tracked and verifiable

---

## MANDATORY: Post-Phase Verification Protocol

**CRITICAL**: Execute this protocol after EVERY phase transition (1-init→3-outline, 4-plan→5-execute, 5-execute→6-verify). This is NOT optional.

### Step 1: Chat History Error Check

Scan the conversation history for failures since the phase started:

**Look for**:
- Tool calls with non-zero exit codes
- Error messages in tool output
- `status: error` in script responses
- Agent failures or exceptions

**If errors found** → **STOP**. Do not proceed. Analyze the error using:
```
Skill: pm-plugin-development:analyze-script-failures
```

### Step 2: Script Execution Log Check

Query the execution log for the plan:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read \
  --plan-id {plan_id} --type script
```

**Scan for**:
- `[ERROR]` entries - any script failures
- Retry patterns: `[ERROR]` followed by `[INFO]` for same script (indicates hidden failure + recovery)
- Argument errors: entries containing "usage:" or "argument"

**If errors found** → **STOP**. Analyze the failure before proceeding.

**Retry Pattern Detection**:
```
[timestamp1] [ERROR] {notation} {subcommand} ...
[timestamp2] [INFO] {notation} {subcommand} ...
```
This indicates an agent silently retried after failure. Investigate WHY the first attempt failed.

### Step 3: Workflow Skill API Contract Verification

Load the contract skill and verify artifacts for the **completed phase**:

```
Skill: pm-workflow:workflow-extension-api
```

| Completed Phase | Contract to Verify |
|-----------------|-------------------|
| 1-init | references.json required fields (domains) |
| 3-outline | deliverable-contract.md |
| 4-plan | task-contract.md |
| 5-execute | task verification criteria |

**Exact Verification Commands** (copy-paste ready):

**1-Init Phase** - Verify references.json:
```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references read --plan-id {plan_id}
```

**Refine (solution)** - Validate solution outline:
```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline validate --plan-id {plan_id}
```

**Refine (tasks)** - List and verify each task:
```bash
# List all tasks
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks list --plan-id {plan_id}

# Get each task by number (replace {N} with 1, 2, 3, etc.)
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get --plan-id {plan_id} --number {N}

# Verify work-log has entry for each task creation
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read --plan-id {plan_id} --type work
# Check output contains "[ARTIFACT]" entries for each TASK-N created
```

**4-Execute Phase** - Run task verification commands:
```bash
# Get task to retrieve verification.commands
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get --plan-id {plan_id} --number {N}

# Then execute each command from the task's verification.commands array
```

**If violations found** → **STOP**. Report violations and remediate before proceeding.

### Step 4: Status Consistency Check

Verify plan status reflects the transition:

```bash
python3 .plan/execute-script.py pm-workflow:manage-status:manage_status read \
  --plan-id {plan_id}
```

**Verify**:
- `current_phase` matches expected next phase
- Previous phase status is `done`
- `updated` timestamp is recent

### Verification Output Template

After completing all steps, output:

```
## POST-PHASE VERIFICATION: {phase_name} Complete

### Step 1: Chat History
| Check | Result |
|-------|--------|
| Tool failures | None / {count} found |
| Error messages | None / {count} found |

### Step 2: Script Execution Log
| Check | Result |
|-------|--------|
| ERROR entries | None / {count} found |
| Retry patterns | None / {count} detected |

### Step 3: Contract Verification
| Contract | Status | Issues |
|----------|--------|--------|
| {contract} | PASS/FAIL | {details} |

### Step 4: Status Consistency
| Field | Expected | Actual | Status |
|-------|----------|--------|--------|
| current_phase | {phase} | {actual} | PASS/FAIL |
| prev phase status | done | {actual} | PASS/FAIL |

### Assessment
**{PASS / FAIL}** - {summary}
```

### Failure Response

If ANY step fails:

1. **STOP** - Do not proceed to next phase
2. **Analyze** - Use `pm-plugin-development:analyze-script-failures` for script issues
3. **Report** - Show user the verification failure with full context
4. **Wait** - Ask user how to proceed before continuing

---

## Compliance Rules

### Rule 0: Allowed .plan Access

Some `.plan` files are designed for direct access:

| File | Access | Purpose |
|------|--------|---------|
| `.plan/execute-script.py` | Execute | Universal script executor with embedded mappings |
| `.plan/plan_logging.py` | Import | Logging module |
| `.plan/marshall-state.toon` | Read/Write | Executor generation metadata |
| `.plan/logs/script-execution-*.log` | Append | Global execution logs |
| `.plan/lessons-learned/*.md` | Read/Write | Lessons learned via manage-lessons skill |

These are NOT violations and should not trigger compliance alerts.

**Approved Script Execution Pattern**:

All marketplace scripts should be executed via the executor:

```bash
python3 .plan/execute-script.py {notation} [subcommand] {args...}
```

Examples:
- `python3 .plan/execute-script.py pm-workflow:manage-files:manage-files add --plan-id my-plan`
- `python3 .plan/execute-script.py pm-dev-builder:builder-maven-rules:maven run --targets verify`

**Violation** (after executor migration complete):
- Direct script execution: `python3 /path/to/script.py {args}` (bypasses logging and standardization)

### Rule 1: No Direct .plan/plans/** Access

**Prohibited Operations** (plan data must use manage-* API):

| Tool | Prohibited Pattern | Correct Alternative |
|------|-------------------|---------------------|
| Read | `.plan/plans/{id}/status.toon` | `python3 .plan/execute-script.py pm-workflow:manage-status:manage_status read --plan-id {id}` |
| Read | `.plan/plans/{id}/references.json` | `python3 .plan/execute-script.py pm-workflow:manage-references:manage-references read --plan-id {id}` |
| Read | `.plan/plans/{id}/work.log` | `python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read --plan-id {id} --type work` |
| Read | `.plan/plans/{id}/solution_outline.md` | `python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline read --plan-id {id}` |
| Read | `.plan/plans/{id}/tasks/TASK-*.toon` | `python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get --plan-id {id} --number 1` |
| Write | `.plan/plans/{id}/*` | Use appropriate manage-* create/update via execute-script.py |
| Edit | `.plan/plans/{id}/*` | Use appropriate manage-* update via execute-script.py |
| Glob | `.plan/plans/**/*.toon` | Use manage-* list operations via execute-script.py |
| Glob | `.plan/plans/{id}/solution_outline.md` | `python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline read --plan-id {id}` |
| Glob | `.plan/plans/{id}/tasks/*` | `python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks list --plan-id {id}` |
| Bash find | `find .plan/plans -name "*.toon"` | Use manage-* list operations via execute-script.py |
| Bash ls | `ls .plan/plans/{id}/tasks/` | `python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks list --plan-id {id}` |

**No Exceptions**: All .plan file access must go through manage-* scripts. The following scripts provide complete coverage:

| File | Read Script | Write Script |
|------|-------------|--------------|
| `request.md` | `pm-workflow:manage-plan-documents:manage-plan-documents request read --plan-id {id}` | `pm-workflow:manage-plan-documents:manage-plan-documents request create --plan-id {id} --title ... --source ... --body ...` |
| `solution_outline.md` | `pm-workflow:manage-solution-outline:manage-solution-outline read --plan-id {id}` | `pm-workflow:manage-solution-outline:manage-solution-outline write --plan-id {id} <<'EOF'` then validate |
| `work.log` | `plan-marshall:manage-logging:manage-log read --plan-id {id} --type work` | `plan-marshall:manage-logging:manage-log work --plan-id {id} --level {level} --message "{message}"` |
| `lessons-learned/*.md` | `plan-marshall:manage-lessons:manage-lesson get --id {lesson_id}` | `plan-marshall:manage-lessons:manage-lesson add` |
| Any plan file | `pm-workflow:manage-files:manage-files read --plan-id {id} --file {path}` | `pm-workflow:manage-files:manage-files write --plan-id {id} --file {path}` |

**Detection Pattern**:

When you observe tool calls that directly access .plan structure files:

```
## PLANNING COMPLIANCE Violation Detected

### Issue Detected
Direct .plan file access bypassing manage-* API

### Context
- **Operation**: [Read/Write/Edit/Glob]
- **Target**: [.plan/plans/{id}/status.toon]
- **Expected**: Use `python3 .plan/execute-script.py pm-workflow:manage-status:manage_status read`
- **Actual**: Direct file read attempted

### Root Cause Analysis
Calling code is accessing .plan files directly instead of using the
manage-* abstraction layer. This bypasses:
- Input validation
- Audit trail logging
- Format consistency checks
- Atomic write guarantees

### Impact Assessment
| Aspect | Impact |
|--------|--------|
| Blocking | No - but should not proceed |
| Data Loss Risk | Yes - no atomic writes |
| Audit Trail | Broken - no work-log entry |
| State Corruption | Possible - no validation |

### Options
1. **Use manage-* API**: Replace direct access with appropriate script
2. **Investigate why**: Determine if manage-* is missing functionality
3. **Document exception**: If truly needed, document why direct access required

### Recommendation
Use manage-* API - this is a design violation, not a missing feature case
```

### Rule 2: Work-Log Population Verification

After any planning operation completes, verify work-log contains appropriate entry.

**Required Work-Log Entries**:

| Operation | Required Entry Type | Required Fields |
|-----------|-------------------|-----------------|
| Phase transition | `progress` | phase, summary |
| Decision made | `decision` | phase, summary, detail (rationale) |
| Artifact created | `artifact` | phase, summary (artifact type and id) |
| Task completed | `outcome` | phase, summary |
| Error occurred | `error` | phase, summary, detail (error info) |

**Verification Steps**:

1. After operation completes, query work-log:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read --plan-id {plan_id} --type work
   ```

2. Verify most recent entry matches operation:
   - Timestamp is within last few seconds
   - Type matches operation category
   - Phase matches current phase
   - Summary describes what happened

**Verification Template**:

```
## POST-OPERATION Audit Verification

### Operation Completed
[Description of what was just executed]

### Work-Log Check
```toon
[Output from plan-marshall:manage-logging:manage-log read]
```

### Verification Result
| Check | Status | Notes |
|-------|--------|-------|
| Entry exists | Pass/Fail | [Details] |
| Correct type | Pass/Fail | Expected: {type}, Found: {type} |
| Correct phase | Pass/Fail | Expected: {phase}, Found: {phase} |
| Meaningful summary | Pass/Fail | [Assessment] |

### Assessment
[PASS/FAIL with explanation]
```

### Rule 3: Status Consistency Verification

After phase transitions or progress updates, verify status reflects correct state.

### Rule 4: Script Execution via Executor (Mandatory)

All marketplace script execution MUST use the universal executor pattern.

**Required Pattern**:
```bash
python3 .plan/execute-script.py {notation} {subcommand} {args...}
```

**Notation Format**: `{bundle}:{skill}:{script}` (e.g., `pm-workflow:manage-files:manage-files`)

**CRITICAL - Singular vs Plural Script Names**:

| Skill Name (plural) | Script Name (SINGULAR) | Full Notation |
|---------------------|------------------------|---------------|
| `manage-plan-documents` | `manage-plan-document` | `pm-workflow:manage-plan-documents:manage-plan-documents` |
| `manage-tasks` | `manage-task` | `pm-workflow:manage-tasks:manage-tasks` |
| `manage-lessons` | `manage-lesson` | `plan-marshall:manage-lessons:manage-lesson` |
| `manage-lifecycle` | `manage-lifecycle` | `pm-workflow:manage-lifecycle:manage-lifecycle` |
| `manage-references` | `manage-references` | `pm-workflow:manage-references:manage-references` |
| `manage-files` | `manage-files` | `pm-workflow:manage-files:manage-files` |
| `logging` | `manage-log` | `plan-marshall:manage-logging:manage-log` |

**Prohibited Operations** (direct script paths must use executor):

| Tool | Prohibited Pattern | Correct Alternative |
|------|-------------------|---------------------|
| Bash | `python3 {script_path} {verb}` | `python3 .plan/execute-script.py {notation} {verb}` |
| Bash | `python3 marketplace/.../script.py` | `python3 .plan/execute-script.py {notation}` |
| Bash | `python3 {bundle}/scripts/foo.py` | `python3 .plan/execute-script.py {bundle}:{skill}` |

**Why This Matters**:
- **Execution logging**: All invocations are logged with timestamps and duration
- **Notation consistency**: Single canonical way to reference scripts
- **Error standardization**: Consistent error output format
- **Cross-cutting features**: Enables future metrics, caching, etc.

**Detection Pattern**:

When you observe tool calls that directly execute scripts:

```
## PLANNING COMPLIANCE Violation Detected

### Issue Detected
Direct script execution bypassing execute-script.py

### Context
- **Operation**: Bash
- **Target**: `python3 {path}/manage-files.py add --plan-id my-plan`
- **Expected**: `python3 .plan/execute-script.py pm-workflow:manage-files:manage-files add --plan-id my-plan`
- **Actual**: Direct script path used

### Root Cause Analysis
Calling code is executing scripts directly instead of using the
execute-script.py proxy. This bypasses:
- Execution logging
- Notation consistency
- Error standardization
- Cross-cutting features

### Options
1. **Use executor**: Replace direct path with executor notation
2. **Update caller**: Fix the SKILL.md/agent/command documentation

### Recommendation
Use executor pattern - this is a design violation
```

### Rule 5: Log File Verification and Issue Detection

Plan-related log files must exist, be properly formatted, remain consistent, and be actively scanned to detect script execution issues.

**Log File Types**:

| File | Location | Purpose |
|------|----------|---------|
| `work.log` | `.plan/plans/{id}/work.log` | Semantic work entries (decisions, artifacts, progress) |
| `script-execution.log` | `.plan/plans/{id}/script-execution.log` | Script execution records for plan-scoped operations |
| `script-execution-*.log` | `.plan/logs/script-execution-{date}.log` | Global execution records (non-plan operations) |

**Log Entry Format** (script-execution.log):

Standard entry:
```
[{timestamp}] [{level}] [SCRIPT] {notation} {subcommand} ({duration}s)
```

Example:
```
[2025-12-11T12:14:26Z] [INFO] [SCRIPT] pm-workflow:manage-files:manage-files create (0.19s)
[2025-12-11T12:17:50Z] [ERROR] [SCRIPT] pm-workflow:manage-task:manage-task add failed (exit 1)
```

**Verification Checks**:

| Check | What to Verify | When |
|-------|---------------|------|
| Existence | `work.log` exists for every active plan | After plan creation |
| Existence | `script-execution.log` exists after first plan-scoped script call | After executor runs with plan_id |
| Format | `work.log` follows standard log format | After any log operation |
| Format | `script-execution.log` uses standard log format | After executor runs |
| Consistency | work.log entries match expected operations | After phase transitions |
| Consistency | script-execution.log records match script calls | After any executor call |

**Issue Detection via Log Scanning**:

Actively scan execution logs to detect script issues:

| Issue Type | Detection Pattern | Severity | Action |
|------------|-------------------|----------|--------|
| Script failure | Lines containing `[ERROR]` | High | Investigate log, fix root cause |
| Repeated failures | Same notation with multiple ERROR entries | Critical | Script is broken, needs immediate fix |
| Slow execution | Duration > 30s for simple operations | Medium | Optimize script or investigate hang |
| Missing executions | Expected script calls not in log | High | Executor not used (compliance violation) |
| Argument errors | Log contains "usage:" or "argument" | Medium | Caller using wrong arguments |
| Import/module errors | Log contains "ModuleNotFoundError" or "ImportError" | Critical | Missing dependency or path issue |
| Permission errors | Log contains "Permission denied" | High | File/directory access issue |

**Log Scanning Commands**:

1. Find all errors in plan execution log:
   ```bash
   grep '\[ERROR\]' .plan/plans/{plan_id}/script-execution.log
   ```

2. Find repeated failures (same script failing):
   ```bash
   grep '\[ERROR\]' .plan/plans/{plan_id}/script-execution.log | sort | uniq -c | sort -rn
   ```

3. Find slow executions (>10s):
   ```bash
   grep -E '\([0-9]{2,}\.[0-9]+s\)' .plan/plans/{plan_id}/script-execution.log
   ```

4. Scan global logs for today's issues:
   ```bash
   grep '\[ERROR\]' .plan/logs/script-execution-$(date +%Y-%m-%d).log
   ```

**Verification Steps**:

1. Check work.log exists and has entries:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read \
     --plan-id {plan_id} --type work --limit 20
   ```

2. Check script-execution.log exists and scan for issues:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read \
     --plan-id {plan_id} --type script --limit 20
   ```

3. Verify format compliance:
   - work.log: Standard log format `[timestamp] [level] [WORK] message`
   - script-execution.log: Standard log format `[timestamp] [level] [SCRIPT] notation subcommand (duration)`

**Detection Pattern for Log Issues**:

```
## PLANNING COMPLIANCE Violation Detected

### Issue Detected
[Log file integrity issue / Script execution failure detected]

### Context
- **Check Type**: [existence/format/consistency/script-failure]
- **File**: [path to log file]
- **Expected**: [what should exist or match]
- **Actual**: [what was found]

### Log Scan Results (if script failure)
| Metric | Value |
|--------|-------|
| Total executions | {count} |
| Failed executions | {error_count} |
| Unique failing scripts | {list} |
| Most recent error | {timestamp} |

### Error Details
```
{stderr content from log}
```

### Root Cause Analysis
[Explanation of why this matters for audit trail integrity or script health]

### Impact Assessment
| Aspect | Impact |
|--------|--------|
| Audit Trail | Incomplete or corrupted |
| Debugging | Missing operation history |
| Compliance | Cannot verify operations occurred |
| Script Health | [Broken/Degraded/Healthy] |

### Options
1. **Fix script**: Address the error shown in stderr
2. **Regenerate entries**: Use manage-log to add missing entries
3. **Investigate cause**: Determine why log was not updated
4. **Manual recovery**: Reconstruct from other sources if possible

### Recommendation
[Specific action based on violation type]
```

**Common Log Violations and Script Issues**:

| Violation | Symptom | Cause |
|-----------|---------|-------|
| Missing work.log | work.log file not found | Plan created without init entry |
| Empty work.log | No entries after operations | Operations bypassed logging |
| Stale script-execution.log | Old timestamps only | Executor not used for recent calls |
| Format corruption | Parse errors | Direct file edit instead of API |
| Script failure | ERROR entries in log | Bug in script or invalid arguments |
| Repeated failures | Same script failing multiple times | Systemic issue needs investigation |
| Import errors | ModuleNotFoundError in log | Missing dependency or wrong Python path |
| Timeout patterns | Very long durations (>60s) | Script hanging or performance issue |

**Status Verification Points**:

| Trigger | What to Verify |
|---------|---------------|
| Phase transition | `current_phase` updated, previous phase marked `done` |
| Task completion | Phase progress reflects completed tasks |
| Error state | Status shows `error` or `blocked` if applicable |
| Plan completion | All phases marked `done` |

**Verification Steps**:

1. After phase-affecting operation, query status:
   ```bash
   python3 .plan/execute-script.py pm-workflow:manage-status:manage_status read --plan-id {plan_id}
   ```

2. Verify status consistency:
   - `current_phase` matches expected phase
   - Phases array shows correct `status` for each phase
   - `updated` timestamp is recent

**Verification Template**:

```
## STATUS Consistency Check

### Expected State
- Current phase: {phase}
- Previous phases: {list of done phases}
- Phase status: {expected statuses}

### Actual State
```toon
[Output from pm-workflow:manage-status:manage_status read]
```

### Consistency Check
| Field | Expected | Actual | Status |
|-------|----------|--------|--------|
| current_phase | {phase} | {actual} | Pass/Fail |
| phases[1-init] | done | {actual} | Pass/Fail |
| phases[3-outline] | done | {actual} | Pass/Fail |
| phases[5-execute] | in_progress | {actual} | Pass/Fail |
| updated | recent | {timestamp} | Pass/Fail |

### Assessment
[PASS/FAIL with explanation]
```

## Workflow Skill API Contract Verification

After each planning phase completes, verify artifacts comply with the workflow skill API contracts. Reference: [pm-workflow:workflow-extension-api](../../../pm-workflow/skills/workflow-extension-api/SKILL.md)

### Phase 1: Init Complete

**Contract Reference**: Phase skills are self-documenting. See `pm-workflow:phase-1-init/SKILL.md`

**Verification**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-references:manage-references read --plan-id {plan_id}
```

**Required Fields**:
| Field | Required | Description |
|-------|----------|-------------|
| `domains` | Yes | Domain identifiers array (java, javascript, plan-marshall-plugin-dev, generic) |

### Phase 2: Solution Outline Complete

**Contract Reference**: [manage-solution-outline/standards/deliverable-contract.md](../../../pm-workflow/skills/manage-solution-outline/standards/deliverable-contract.md)

**Verification**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline validate --plan-id {plan_id}
```

**Required Deliverable Fields**:
| Field | Required | Description |
|-------|----------|-------------|
| `change_type` | Yes | create/modify/refactor/migrate/delete |
| `execution_mode` | Yes | automated/manual/mixed |
| `domain` | Yes | Valid domain (java/javascript/plan-marshall-plugin-dev etc.) |
| `profile` | Yes | `implementation` or `module_testing` |
| `depends` | Yes | `none` or `N` or `N. Title` or `N, M` |
| `Affected files` | Yes | Explicit file paths (not glob patterns) |
| `Verification` | Yes | Command and criteria |
| `suggested_skill` | No | Optional override: explicit skill `{bundle}:{skill-name}` |
| `suggested_workflow` | No | Optional override: workflow within explicit skill |
| `context_skills` | No | List of optional skills from domain |

**Common Violations**:
| Violation | Description | Fix |
|-----------|-------------|-----|
| Vague file references | "All files matching X" instead of explicit paths | Enumerate all files explicitly |
| Missing `depends` | No dependency specification | Add `depends: none` or proper reference |
| Wrong `depends` format | Using title without number | Use `N. Title` format |
| Missing `domain` | Skill loading will fail | Add valid domain from config |
| Missing `context_skills` | Key in delegation block | Add empty list `[]` or valid skills |

### Phase 3: User Review (Mandatory)

**Contract Reference**: [workflow-extension-api/standards/protocols/user-review.md](../../../pm-workflow/skills/workflow-extension-api/standards/protocols/user-review.md)

**Verification**: Check work.log for user approval entry

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read --plan-id {plan_id} --type work | grep -i "approved\|proceed"
```

**Required**: User explicitly approved solution outline before task creation. Task creation without user approval is a CRITICAL violation.

### Phase 4: Tasks Created

**Contract Reference**: [manage-tasks/standards/task-contract.md](../../../pm-workflow/skills/manage-tasks/standards/task-contract.md)

**Verification**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks list --plan-id {plan_id}
```

For each task, verify:
```bash
python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks get --plan-id {plan_id} --number {N}
```

**Required Task Fields**:
| Field | Required | Description |
|-------|----------|-------------|
| `deliverables` | Yes | List of deliverable numbers (non-empty) |
| `depends_on` | Yes | `none` or `TASK-N` references |
| `delegation.skill` | Yes | Format: `{bundle}:{skill-name}` |
| `delegation.workflow` | Yes | Workflow within skill |
| `delegation.domain` | Yes | Valid domain value |
| `delegation.context_skills` | Yes* | From deliverable's context_skills (*may be empty list) |
| `steps` | Yes | TOON tabular format with file paths |
| `verification.commands` | Yes | List of verification commands |
| `verification.criteria` | Yes | Success criteria |

**Steps Field Contract** (CRITICAL):
- Steps MUST be file paths from deliverable's `Affected files`
- Steps MUST NOT be action descriptions
- TOON format: `steps[N]{number,title,status}:` with file paths in title column

**Common Violations**:
| Violation | Description | Fix |
|-----------|-------------|-----|
| Missing `context_skills` | Delegation block incomplete | Add context_skills from deliverable |
| Descriptive steps | Steps contain action text, not file paths | Use file paths from deliverable |
| Missing `deliverables` | No traceability to solution outline | Add deliverable number references |

### Post-Phase Verification Template

After each phase completes, use this verification template:

```
## Workflow Skill API Contract Verification

### Phase Completed
{init | outline | plan | execute | finalize}

### Contract Checks
| Check | Status | Notes |
|-------|--------|-------|
| Required fields present | Pass/Fail | [Details] |
| Field formats correct | Pass/Fail | [Details] |
| References valid | Pass/Fail | [Details] |
| No anti-patterns | Pass/Fail | [Details] |

### Violations Found
| Artifact | Field | Issue | Severity |
|----------|-------|-------|----------|
| {file} | {field} | {description} | Critical/High/Medium |

### Remediation
[Actions taken or required]

### Assessment
[PASS/FAIL with explanation]
```

## Automated Verification Checklist

After each planning command/skill execution, verify:

- [ ] No direct .plan file access (except request.md read)
- [ ] work.log entry added for significant operations
- [ ] Status reflects current phase correctly
- [ ] All artifacts created via manage-* scripts
- [ ] No orphaned files in .plan structure
- [ ] Log files exist and are properly formatted (work.log, script-execution.log)
- [ ] script-execution.log contains recent entries for script calls
- [ ] script-execution.log scanned for ERROR entries - none found or issues addressed
- [ ] No repeated script failures detected in logs

## Integration with Commands

### plan-marshall Command (Phases 1-4)

When `/plan-marshall` executes init/outline actions, verify after each action:

| Action | Expected Work-Log Entry | Expected Status Change |
|--------|------------------------|----------------------|
| `1-init` | type=artifact, summary=plan created | phases[1-init]=in_progress |
| configure complete | type=progress, summary=configuration complete | phases[1-init]=done, current_phase=3-outline |
| `3-outline` | type=artifact per deliverable created | phases[3-outline] progress updates |
| outline complete | type=outcome, summary=3-outline complete | phases[3-outline]=done, current_phase=4-plan |

### plan-marshall Command (Phases 5-7)

When `/plan-marshall` executes execute/verify/finalize actions, verify after each task:

| Event | Expected Work-Log Entry | Expected Status Change |
|-------|------------------------|----------------------|
| Task started | type=progress, summary=task title | task status=in_progress |
| Step completed | type=progress, summary=step description | step marked complete |
| Task completed | type=outcome, summary=task completion | task status=done |
| Build verified | type=outcome, summary=verification passed | - |
| Error occurred | type=error, detail=error info | may set blocked state |
| All tasks done | type=progress, summary=5-execute phase complete | current_phase=6-verify |

## Common Violations

### Violation 1: Direct Status Read

```
Claude uses: Read .plan/plans/my-plan/status.toon
Should use: python3 .plan/execute-script.py pm-workflow:manage-status:manage_status read --plan-id my-plan
```

**Note**: Script notation is `pm-workflow:manage-status:manage_status` for status reads.

**Why It Matters**: Direct reads bypass the managed parser, may read stale data during atomic writes, and don't leverage script validation.

### Violation 2: Missing Work-Log Entry

```
Operation: Created solution_outline.md with 3 goals
Work-log: No entry found for artifact creation
```

**Why It Matters**: Audit trail is incomplete, making debugging and progress tracking impossible.

### Violation 3: Stale Status After Transition

```
Operation: Completed all 5-execute phase tasks
Expected: current_phase=6-verify
Actual: current_phase=5-execute (not updated)
```

**Why It Matters**: Phase routing will execute wrong phase, plan lifecycle is broken.

### Violation 4: Direct File Creation

```
Claude uses: Write .plan/plans/my-plan/tasks/TASK-003.toon
Should use: python3 .plan/execute-script.py pm-workflow:manage-tasks:manage-tasks add --plan-id my-plan <<'EOF'
title: Task title
deliverable: 1
domain: java
steps:
  - Step A
  - Step B
EOF
```

**Note**: Script notation uses SINGULAR `manage-task` (not `manage-tasks`). Full notation: `pm-workflow:manage-tasks:manage-tasks`. Task definitions are passed via stdin using heredoc to avoid shell metacharacter issues.

**Why It Matters**: Bypasses numbering logic, validation, and work-log entry creation.

## Exception Handling

Some operations legitimately need direct access:

### Legitimate Exceptions

1. **Lessons learned** - standalone markdown files accessed via manage-lessons skill
2. **Diagnostics/debugging** - when investigating issues with user approval

**Note**: `request.md` and `solution_outline.md` are now managed via `pm-workflow:manage-plan-documents` skill.

### Documenting Exceptions

When direct access is truly required, document it:

```
## EXCEPTION: Direct .plan Access

### Justification
[Why manage-* cannot be used]

### Risk Mitigation
[How data integrity is preserved]

### Scope
[Exactly which files and operations]

User approval obtained: [Yes/No]
```

## Post-Run Verification Script

Use this verification pattern after major operations:

```bash
# Verify work.log has recent entry
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read \
  --plan-id {plan_id} --type work --limit 20

# Verify status is consistent
python3 .plan/execute-script.py pm-workflow:manage-status:manage_status read \
  --plan-id {plan_id}

# Verify no orphaned files (optional)
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files list \
  --plan-id {plan_id}
```

Expected output should show:
- Work-log entry within last few seconds
- Status current_phase matches expected
- All files properly registered

## Post-Run Verification: Executor Pattern

After script operations complete, verify proper executor usage:

**For plan-scoped operations** (when plan_id was provided):
```bash
# Verify execution logged to plan
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log read \
  --plan-id {plan_id} --type script --limit 20
```

**For global operations** (no plan context):
```bash
# Verify execution logged to daily global log (direct access acceptable for global logs)
tail -5 .plan/logs/script-execution-$(date +%Y-%m-%d).log
```

**Success entry format**:
```
[{timestamp}] [INFO] [SCRIPT] {notation} {subcommand} ({duration}s)
```

**Error entry format**:
```
[{timestamp}] [ERROR] [SCRIPT] {notation} {subcommand} failed (exit {code})
```

Expected verification:
- Timestamp is recent (within last few seconds)
- Notation matches expected script
- Level is INFO for success, ERROR for failures
