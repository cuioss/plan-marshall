---
name: phase-5-execute
description: Execute phase skill for plan management. DUMB TASK RUNNER that executes tasks from TASK-*.json files sequentially.
user-invocable: false
---

# Phase Execute Skill

**Role**: DUMB TASK RUNNER that executes tasks from TASK-*.json files sequentially.

**Execution Pattern**: Locate current task → Execute steps → Mark progress → Next task

**Phase Handled**: execute

## Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: DUMB TASK RUNNER — locate task, execute steps, mark progress, next task. Follow workflow steps sequentially.

**Prohibited actions:**
- Never access `.plan/` files directly — use manage-* scripts via Bash (Edit/Write tools trigger permission prompts on `.plan/` directories)
- Never skip the phase transition — use `manage-status transition`
- Never improvise script subcommands — use only those documented below
- Never target file paths outside the active git worktree. When a plan runs in an isolated worktree, all Edit/Write/Read tool calls during execution MUST use the worktree's absolute path (e.g., `<root>/.claude/worktrees/{plan_id}/...`), never the main checkout (e.g., `/Users/oliver/git/{repo}/...`). Editing the main checkout pollutes uncommitted state, bypasses worktree isolation, and lets tests silently load stale source via PYTHONPATH.

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline
- On phase entry (Step 4), resolve the active worktree absolute path and surface it as a `[STATUS]` work-log line so it stays visible in model context throughout the run. If present, every subsequent Edit/Write/Read must reference that path as the root.
- Every subagent dispatch (Task / Skill / phase-agent invocation) MUST embed the `worktree_path` directly in the dispatch prompt when a worktree is active (see **Dispatch Protocol** below) AND MUST pass it as an input parameter to satisfy the subagent's Input Contract (e.g., `execute-task`, `phase-agent`). Prompt embedding and parameter passing are both required — the former propagates the constraint through free-form delegation, the latter satisfies the structured interface.

## Dispatch Protocol (Worktree Header)

**REQUIREMENT**: When the plan runs in an isolated worktree (see the `[STATUS] Active worktree` work-log line from Step 4), every subagent dispatch prompt — including `Task:`, `Skill:` invocations that accept free-form prompts, and `phase-agent` delegations — MUST begin with the following header:

```
WORKTREE: {worktree_path}
All Edit/Write/Read tool calls MUST target paths under this worktree. Raw git/mvn/npm commands MUST operate against this path. Bucket B .plan/execute-script.py invocations (build/CI/Sonar) MUST pass --project-dir {worktree_path}; Bucket A manage-* scripts remain cwd-agnostic and MUST NOT receive --project-dir. NEVER edit the main checkout.
```

The `[STATUS] Active worktree: ...` work-log line remains the observability signal that the worktree was detected, but it is informational only — the active propagation mechanism is embedding the header in every dispatch prompt. Skip the header only when no worktree is active.

This applies to every dispatch in the execution loop, including (but not limited to) **Step 6 (Execute Steps)** task dispatches and **Step 9 (Independent Change Verification)** subagent invocations. Child agents must echo the same header verbatim into any further dispatches they issue. The Bucket B `--project-dir` clause exists so that verification commands resolved by `task-executor` (`module-tests`, `compile`, `quality-gate`, etc.) run against the worktree's uncommitted state rather than the main checkout — without it, pytest silently collects tests from the main working tree and reports green while leaving the worktree's new tests entirely unexercised. See `plan-marshall:tools-script-executor/standards/cwd-policy.md` for the authoritative Bucket A/B split.

See `standards/operations.md` for the complete set of dispatch pattern templates updated with this header.

## cwd for `.plan/execute-script.py` calls

> `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass `--project-dir`, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) take `--project-dir {worktree_path}` explicitly when a worktree is active. `{worktree_path}` is the `[STATUS] Active worktree` line surfaced at Step 4 entry. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status get-routing-context \
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
| **skill** | fully-qualified `bundle:skill` (e.g., `my-bundle:my-verify-step`) | `Skill: {notation}` with interface contract |

**Type detection logic**:
- Starts with `default:` -> built-in type (strip prefix, execute built-in command)
- Starts with `project:` -> project type
- Contains `:` (other) -> fully-qualified skill type

Each verify step declares an `order: <int>` value in its authoritative source — frontmatter on built-in standards docs (`standards/{name}.md`), frontmatter on project-local `SKILL.md` for `project:` steps, and the return-dict `order` field for extension-contributed skills. `marshall-steward` sorts the `steps` list by this value when writing it to `marshal.json`. This skill iterates the list as written and does NOT re-sort or validate `order` at runtime — the persisted order is the runtime order.

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

Input contract: `--plan-id` only. Retry logic is managed by the task runner (Step 11 triage loop with `verification_max_iterations`), not by the step itself.

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
- `status: failed` + `findings[]` → findings fed into Step 11 triage (fix task creation, suppress, or accept)
- `status: failed` without `findings[]` → treated as single unstructured failure, triaged as one finding

---

### Step 3: Sync Worktree With Main (Once per phase)

Before the execute loop begins, bring the feature branch up to date against `origin/{base_branch}` so coding starts on a current base rather than one potentially stale since `phase-1-init`. Full procedure, git invocations, fast-path semantics, conflict contract, and main-checkout fallback are documented in [standards/sync-with-main.md](standards/sync-with-main.md).

Inlined flow:

1. **Read `rebase_on_execute_start`** (default `true`):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan phase-5-execute get --field rebase_on_execute_start --trace-plan-id {plan_id}
   ```

   If the returned `value` is `false`, skip this step and log:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:phase-5-execute) Sync skipped: rebase_on_execute_start=false"
   ```

   Proceed to Step 4.

2. **Read `rebase_strategy`** (default `merge`, valid values `merge` | `rebase`):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     plan phase-5-execute get --field rebase_strategy --trace-plan-id {plan_id}
   ```

   Record the returned `value` as `{strategy}` — it is referenced in points 6, 7, and 8 below.

3. **Resolve `base_branch` and `worktree_path`** from `references.json` (written at `phase-1-init` Step 6):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
     --plan-id {plan_id} --file references.json
   ```

   Extract `base_branch` and `worktree_path`. If `worktree_path` is absent, the plan runs against the main checkout; substitute `.` for `{worktree_path}` in every git command below.

4. **Fetch base**:

   ```bash
   git -C {worktree_path} fetch origin {base_branch}
   ```

5. **Fast-path check** — if the current branch tip already contains `origin/{base_branch}`, skip strategy application:

   ```bash
   git -C {worktree_path} merge-base --is-ancestor origin/{base_branch} HEAD
   ```

   Exit code `0` means already up to date. Log and continue to Step 4:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO \
     --message "[STATUS] (plan-marshall:phase-5-execute) Sync skipped: already up to date with origin/{base_branch}"
   ```

6. **Apply strategy** — first record the current HEAD so the success path (point 8) can compute the incorporated commit range:

   ```bash
   git -C {worktree_path} rev-parse HEAD
   ```

   Record the output as `{previous_HEAD}`. Then apply the chosen strategy:

   - `merge`:

     ```bash
     git -C {worktree_path} merge --no-edit origin/{base_branch}
     ```

   - `rebase`:

     ```bash
     git -C {worktree_path} rebase origin/{base_branch}
     ```

7. **Conflict contract** — if the strategy command exits non-zero, ABORT the phase fail-loud: do NOT auto-resolve, do NOT continue to Step 4. Leave conflict markers in the worktree, surface the failure in `work.log` at ERROR level with `{worktree_path}` and the conflicted files, and exit without entering the task loop. First capture the conflicted files:

   ```bash
   git -C {worktree_path} diff --name-only --diff-filter=U
   ```

   Record the output as `{files}`. Then log the conflict:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level ERROR \
     --message "[ERROR] (plan-marshall:phase-5-execute) Sync conflict at {worktree_path} — strategy={strategy}, conflicted files: {files}. Phase aborted; resolve manually and re-run."
   ```

8. **Success** — compute the incorporated commit range from `{previous_HEAD}` captured in point 6:

   ```bash
   git -C {worktree_path} rev-list --abbrev-commit --reverse {previous_HEAD}..HEAD
   ```

   Record the output as `{short_sha_range}`. Then record to `decision.log`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     decision --plan-id {plan_id} --level INFO \
     --message "(plan-marshall:phase-5-execute) Synced worktree with origin/{base_branch} via {strategy} — commits {short_sha_range}"
   ```

Proceed to Step 4.

### Step 4: Log Phase Start and Surface Active Worktree (Once per phase)

At the start of execute or finalize phase:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Starting {phase} phase"
```

**Surface the active worktree absolute path** so it remains visible in model context for every subsequent Edit/Write/Read call. Read the worktree path from status metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Extract `worktree_path` from the output. If present (plan runs in an isolated worktree), emit:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Active worktree: {worktree_path} — all Edit/Write/Read tool calls MUST target this path, NOT the main checkout. ALL git commands MUST use 'git -C {worktree_path} <subcommand>' — NEVER 'cd {worktree_path} && git ...' (compound form trips the bare-repository security prompt and violates Bash one-command-per-call)."
```

If `worktree_path` is absent (plan runs against the main checkout), skip emission. If present, every file path used in Edit/Write/Read from this point on MUST be resolved against `{worktree_path}` rather than the main checkout, and every git command MUST use `git -C {worktree_path} <subcommand>` rather than `cd {worktree_path} && git ...`.

When `worktree_path` is absent (main-checkout mode), the `cd && git` prohibition still applies — use `git -C .`. The rule is enforced at the foundational layer in [`dev-general-practices` Hard Rules](../dev-general-practices/SKILL.md#git-always-use-git--c-path-never-cd-path--git-) and reinforced inline here so agents see it next to the worktree path they would use it with.

For each task in current phase:

### Step 5: Locate Task with Context

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next \
  --plan-id {plan_id} \
  --include-context
```

Returns next task with status `pending` or `in_progress`, including embedded goal context (title, body) for immediate use without additional script calls.

### Step 6: Execute Steps

For each step in task's `steps[]` array:
1. Parse the step text
2. Execute the action (delegate if specified) — when delegating to a subagent via `Task:`, `Skill:` (prompt-accepting), or `phase-agent`, the prompt MUST begin with the Worktree Header from the **Dispatch Protocol** section above (omit only when no worktree is active).
3. Mark step complete via `manage-tasks:finalize-step`

### Step 7: Mark Step Complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step \
  --plan-id {plan_id} \
  --task {task_number} \
  --step {step_number} \
  --outcome done
```

### Step 8: Log Task Completion

After each task completes:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[OUTCOME] (plan-marshall:phase-5-execute) Completed {task_id}: {task_title} ({steps_completed} steps)"
```

### Step 9: Independent Change Verification

**Applies to**: `implementation` and `module_testing` profile tasks only. Skip this step for `verification` profile tasks.

After task completion but before committing, independently verify that the task agent produced genuine results rather than trusting self-reports. Any subagent dispatch made during this step (e.g., a follow-up Task invocation) MUST embed the Worktree Header per the **Dispatch Protocol** section above.

**9a. File-change invariant**: Verify that at least one file was modified in the worktree. Run in the worktree directory (or main checkout if no worktree):

```bash
git -C {worktree_path} diff --name-only HEAD
```

If the diff output is empty (no files changed) for an `implementation` or `module_testing` task:
- Mark task `blocked` with reason `no_changes_detected`
- Log:
  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level WARN --message "[VERIFY] (plan-marshall:phase-5-execute) No file-system changes detected for {task_id} — marking blocked"
  ```
- Skip Steps 9b and 9c, proceed to Step 11 (Triage)

**9b. Obfuscation spot-check** (conditional): When the task's verification criteria include checking for absence of a specific token (e.g., "zero grep hits for `--body`"), grep the modified files for common obfuscation patterns around that token:
- String concatenation splitting the token (e.g., `'--' + 'body'`, `"--" + "body"`)
- Variable assignment that reconstructs the token from parts

If any obfuscation pattern is found:
- Log each hit:
  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level WARN --message "[VERIFY] (plan-marshall:phase-5-execute) Obfuscation pattern detected in {file}: {pattern} — manual review recommended"
  ```
- Do NOT auto-block (false positives are possible) — flag for human review only

**9c. Verification cross-check**: Re-execute the task's `verification.commands` independently and compare the exit code against what the agent reported:

```bash
# Run the same verification command the agent claims to have passed
{verification_command}
```

If the agent reported `verification.passed: true` but the independent run returns a non-zero exit code:
- Mark task `blocked` with reason `verification_mismatch`
- Log:
  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --plan-id {plan_id} --level WARN --message "[VERIFY] (plan-marshall:phase-5-execute) Verification mismatch for {task_id}: agent reported pass but independent run failed — marking blocked"
  ```
- Proceed to Step 11 (Triage)

If independent verification also passes, continue to Step 10.

### Step 10: Conditional Per-Deliverable Commit

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
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --plan-id {plan_id} --level INFO --message "[OUTCOME] (plan-marshall:phase-5-execute) Per-deliverable commit: {task_id} ({commit_hash})"
   ```

If `commit_strategy` is `per_plan` or `none` → Skip this step entirely.

### Step 11: Triage Verification Failure

**Applies when**:
- A `profile=verification` task completes with `verification.passed: false` / `next_action: requires_triage`, OR
- Step 9 marked a task `blocked` with reason `no_changes_detected` or `verification_mismatch`

**For `no_changes_detected` blocks**: The implementation task produced no file changes. Triage options:
- **RETRY** → reset task to `pending` for re-execution
- **FAIL** → mark task `failed` with outcome `no_changes_detected`, log, continue

**For `verification_mismatch` blocks**: The agent claimed verification passed but independent re-run failed. Triage options:
- **FIX** → create fix task to address the actual verification failure
- **RETRY** → reset task to `pending` for re-execution
- **FAIL** → mark task `failed` with outcome `verification_mismatch`, log, continue

**For verification task failures** (original behavior):

**11a**: Read `verify_iteration` counter from task metadata (default: 0).

**11b**: If `verify_iteration >= verification_max_iterations` (from phase-5-execute config, default 5) → mark task `blocked`, log, continue to Step 12.

**11c**: Load domain triage extension via extension-api (`provides_triage()`).

**11d**: Persist findings to Q-Gate:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 5-execute \
  --source qgate --type {finding_type} --severity {severity} \
  --message "{finding_message}" --detail "{file}:{line}"
```

**11e**: Triage each finding:
- **FIX** → create fix task (`origin: fix`, `profile: implementation`, depends on nothing)
- **SUPPRESS** → log suppression, resolve finding
- **ACCEPT** → log as technical debt, resolve finding

**11f**: If fix tasks created → increment `verify_iteration` in task metadata, reset verification task to `pending`, continue execution loop (fix tasks will execute before the re-queued verification task via `depends_on`).

**11g**: If no fix tasks → mark verification task complete (all findings suppressed/accepted), continue to Step 12.

### Step 12: Next Task or Phase

- If more tasks in phase → Continue to next task
- If phase complete → Log phase outcome and auto-transition to next phase
- If all phases complete → Mark plan complete

### Step 13: Log Phase Completion (When phase completes)

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-5-execute) Completed {phase} phase: {tasks_completed} tasks"
```

**Add visual separator** after END log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
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
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} \
  --completed 5-execute
```

This automatically updates status.json and moves to the next phase.

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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
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

