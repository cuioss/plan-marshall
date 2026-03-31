---
name: phase-5-execute
description: Execute phase skill for plan management. DUMB TASK RUNNER that executes tasks from TASK-*.json files sequentially.
user-invocable: false
---

# Phase Execute Skill

**Role**: DUMB TASK RUNNER that executes tasks from TASK-*.json files sequentially.

**Execution Pattern**: Locate current task → Execute steps → Mark progress → Next task

**Phase Handled**: execute

**CRITICAL**: Use manage-* scripts via Bash for plan file updates (Edit/Write tools trigger permission prompts on `.plan/` directories).

---

## Standards (Load On-Demand)

### Workflow
```
Read standards/workflow.md
```
Contains: Task execution pattern, phase transition, auto-continue behavior

### Operations
```
Read standards/operations.md
```
Contains: Delegation patterns for builds, quality checks, PR creation

---

## Execution Loop

### Step 1: Get Routing Context (Once at start)

Get current phase, skill routing, and progress in a single call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle get-routing-context \
  --plan-id {plan_id}
```

Returns:
```toon
status: success
plan_id: {plan_id}
current_phase: 5-execute
skill: plan-marshall:phase-5-execute
skill_description: Execute phase skill for task implementation
total_phases: 4
completed_phases: 2
phases:
- init: complete
- refine: complete
- execute: in_progress
- finalize: pending
```

Use `current_phase` for logging, `skill` for dynamic routing, and `completed_phases/total_phases` for progress display.

### Step 2: Read Commit Strategy (Once at start)

Cache the commit strategy for the entire execute loop:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --trace-plan-id {plan_id}
```

Extract `commit_strategy` from output. Valid values: `per_deliverable`, `per_plan`, `none`.

Also extract the `steps` list — these are the verification steps to execute as verification tasks. See **Verification Step Types** below for dispatch rules.

---

## Verification Step Types

The `steps` list in phase-5-execute config contains verification step references. Three step types are supported, distinguished by prefix notation (same model as phase-6-finalize):

| Type | Notation | Resolution |
|------|----------|------------|
| **built-in** | `default:` prefix (e.g., `default:quality_check`) | Execute built-in verification command (see dispatch table) |
| **project** | `project:` prefix (e.g., `project:verify-step-lint`) | `Skill: {notation}` with interface contract |
| **skill** | fully-qualified `bundle:skill` (e.g., `pm-documents:doc-verify`) | `Skill: {notation}` with interface contract |

**Type detection logic**:
- Starts with `default:` -> built-in type (strip prefix, execute built-in command)
- Starts with `project:` -> project type
- Contains `:` (other) -> fully-qualified skill type

### Built-in Step Dispatch Table

| Step Name | Action | Description |
|-----------|--------|-------------|
| `default:quality_check` | Run quality-gate build command | Code quality checks |
| `default:build_verify` | Run full test suite | Build verification |
| `default:coverage_check` | Run coverage build, then parse JaCoCo report | Coverage threshold verification |

**`coverage_check` dispatch**: Resolve via `architecture resolve --command coverage` to run the coverage build, then invoke `build-maven:maven coverage-report` (or `build-gradle:gradle coverage-report`) to parse the JaCoCo report. Pass `--report-path` pointing to the module's target directory and `--threshold` from config.

### Interface Contract for External Steps

Project and skill steps receive these parameters:

```
Skill: {step_reference}
  Arguments: --plan-id {plan_id}
```

Input contract: `--plan-id` only. Retry logic is managed by the task runner (Step 9 triage loop with `verification_max_iterations`), not by the step itself.

**Return Contract** (required TOON output from external steps):

```toon
status: passed|failed
message: "Human-readable summary"

# Optional — only when status: failed
findings[N]{file,line,message,severity}:
src/Foo.java,42,Unused import,warning
src/Bar.java,10,Missing null check,error
```

- `status: passed` → step complete, continue to next step
- `status: failed` + `findings[]` → findings fed into Step 9 triage (fix task creation, suppress, or accept)
- `status: failed` without `findings[]` → treated as single unstructured failure, triaged as one finding

---

### Step 3: Log Phase Start (Once per phase)

At the start of execute or finalize phase:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Starting {phase} phase"
```

For each task in current phase:

### Step 4: Locate Task with Context

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next \
  --plan-id {plan_id} \
  --include-context
```

Returns next task with status `pending` or `in_progress`, including embedded goal context (title, body) for immediate use without additional script calls.

### Step 5: Execute Steps

For each step in task's `steps[]` array:
1. Parse the step text
2. Execute the action (delegate if specified)
3. Mark step complete via `manage-tasks:finalize-step`

### Step 6: Mark Step Complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} \
  --task {task_number} \
  --step {step_number} \
  --outcome done
```

### Step 7: Log Task Completion

After each task completes:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[OUTCOME] (plan-marshall:phase-5-execute) Completed {task_id}: {task_title} ({steps_completed} steps)"
```

### Step 8: Conditional Per-Deliverable Commit

If `commit_strategy == per_deliverable` (cached from Step 2):

1. **Check dependency chain**: Does any other pending/in-progress task have `depends_on` pointing to the just-completed task?
   - **YES** → Skip commit (a downstream task still needs to run)
   - **NO** → This is the chain tail (all tasks for this deliverable are done) → Commit

2. **Commit** (only when chain tail):
   ```
   Skill: plan-marshall:workflow-integration-git
   Parameters:
     - message: conventional commit derived from task title
     - push: false
     - create-pr: false
   ```

3. **Log commit outcome**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
     work --plan-id {plan_id} --level INFO --message "[OUTCOME] (plan-marshall:phase-5-execute) Per-deliverable commit: {task_id} ({commit_hash})"
   ```

If `commit_strategy` is `per_plan` or `none` → Skip this step entirely.

### Step 9: Triage Verification Failure (verification tasks only)

**Only applies** when a `profile=verification` task completes with `verification.passed: false` / `next_action: requires_triage`.

**9a**: Read `verify_iteration` counter from task metadata (default: 0).

**9b**: If `verify_iteration >= verification_max_iterations` (from phase-5-execute config, default 5) → mark task `blocked`, log, continue to Step 10.

**9c**: Load domain triage extension via extension-api (`provides_triage()`).

**9d**: Persist findings to Q-Gate:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 5-execute \
  --source qgate --type {finding_type} --severity {severity} \
  --message "{finding_message}" --detail "{file}:{line}"
```

**9e**: Triage each finding:
- **FIX** → create fix task (`origin: fix`, `profile: implementation`, depends on nothing)
- **SUPPRESS** → log suppression, resolve finding
- **ACCEPT** → log as technical debt, resolve finding

**9f**: If fix tasks created → increment `verify_iteration` in task metadata, reset verification task to `pending`, continue execution loop (fix tasks will execute before the re-queued verification task via `depends_on`).

**9g**: If no fix tasks → mark verification task complete (all findings suppressed/accepted), continue to Step 10.

### Step 10: Next Task or Phase

- If more tasks in phase → Continue to next task
- If phase complete → Log phase outcome and auto-transition to next phase
- If all phases complete → Mark plan complete

### Step 11: Log Phase Completion (When phase completes)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Completed {phase} phase: {tasks_completed} tasks"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  separator --plan-id {plan_id} --type work
```

---

## Delegation

When checklist items specify delegation, invoke the appropriate agent/skill:

| Checklist Pattern | Delegation |
|-------------------|------------|
| "Run build" / "maven" / "npm" | See `standards/operations.md` |
| "Delegate to {agent}" | `Task: {agent}` |
| "Load skill: {skill}" | `Skill: {skill}` |
| "Run /command" | `SlashCommand: /command` |

---

## Auto-Continue Behavior

Execute continuously without user prompts except:
- Error blocks progress
- Decision genuinely required
- User explicitly requested confirmation

**Do NOT prompt for**:
- Phase transitions
- Task transitions
- Routine confirmations

---

## Phase Transition

When transitioning from execute phase to finalize:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lifecycle:manage-lifecycle transition \
  --plan-id {plan_id} \
  --completed 5-execute
```

This automatically updates status.toon and moves to the next phase.

**After transition**, check `finalize_without_asking` config:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field finalize_without_asking --trace-plan-id {plan_id}
```

- **IF `finalize_without_asking == true`**: Log and auto-continue to finalize phase
- **ELSE (default)**: Stop and display `"Run '/plan-marshall action=finalize plan={plan_id}' when ready."`

---

## Error Handling

On any error, **first log the error** to work-log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-5-execute) {task_id} failed - {error_type}: {error_context}"
```

### Script Failure (Lessons-Learned Capture)

**ON SCRIPT FAILURE**: When any script execution fails (exit != 0):
1. Log error to work-log (see above)
2. Capture error context (script path, exit code, stderr)
3. Continue with normal error recovery (retry, fail task, etc.)

### Other Errors

| Error | Options |
|-------|---------|
| Build failure | Fix and retry / View log / Skip task |
| Test failure | Fix tests / View details / Skip task |
| Dependency not met | Complete dependency / Skip check |

---

## Integration

### Command Integration
- **/plan-marshall action=execute** - Primary entry point invoking this skill

### Related Skills
- **phase-4-plan** - Creates tasks from deliverables (previous phase)
- **phase-6-finalize** - Shipping workflow (commit, PR) (next phase)

