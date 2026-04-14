# Planning Compliance Standard

Enforces proper access patterns and audit-trail verification for planning-related commands and skills.

## Overview

Planning operations MUST use the official manage-* APIs for all `.plan` directory access. Direct file manipulation bypasses validation, audit trails, and can corrupt plan state. This standard defines the detection pattern for violations and the audit-trail checks that guarantee consistent plan state.

## Core Principles

1. **Abstraction Enforcement** — all `.plan` access goes through manage-* scripts.
2. **Audit Trail Integrity** — every operation records to work-log.
3. **State Consistency** — status reflects the actual phase and progress.
4. **No Silent Mutations** — all changes are tracked and verifiable.

---

## MANDATORY: Post-Phase Verification Protocol

Execute this protocol after EVERY phase transition (1-init → 3-outline, 4-plan → 5-execute, 5-execute → 6-finalize). It is not optional.

### Step 1 — Chat History Error Check

Scan the conversation for non-zero exit codes, error messages in tool output, `status: error` in script responses, and agent failures/exceptions since the phase started. If any are found, STOP and run `Skill: pm-plugin-development:tools-analyze-script-failures` before proceeding.

### Step 2 — Script Execution Log Check

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging read \
  --plan-id {plan_id} --type script
```

Scan for `[ERROR]` entries, retry patterns (an `[ERROR]` followed by `[INFO]` for the same notation indicates a silent retry), and argument errors (`usage:` or `argument`). STOP and analyze any failure before continuing.

### Step 3 — Workflow Skill API Contract Verification

Load the contract skill and verify artifacts for the phase that just completed:

```
Skill: plan-marshall:extension-api
```

| Completed Phase | Contract to Verify | Command |
|-----------------|--------------------|---------|
| 1-init | references.json required fields (domains) | `manage-references:manage-references read --plan-id {plan_id}` |
| 3-outline | solution-outline-standard.md | `manage-solution-outline:manage-solution-outline validate --plan-id {plan_id}` |
| 4-plan | task-contract.md | `manage-tasks:manage-tasks list --plan-id {plan_id}` plus `manage-tasks:manage-tasks get --plan-id {plan_id} --number {N}` for each task |
| 5-execute | task verification criteria | Execute each task's `verification.commands` after calling `manage-tasks get` |

All commands must be invoked via `python3 .plan/execute-script.py plan-marshall:...`. For phase 4-plan, also verify the work-log contains `[ARTIFACT]` entries for every task created. STOP and remediate any violations before proceeding.

### Step 4 — Status Consistency Check

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Verify `current_phase` matches the expected next phase, the previous phase status is `done`, and the `updated` timestamp is recent.

### Verification Output Template

After completing all four steps, report the result as a concise table listing, per step, the check name (chat history failures, script-log errors, contract status, status consistency) and its PASS/FAIL state. Finish with an overall `**PASS / FAIL**` line and a one-sentence summary.

### Failure Response

On any failed step, STOP immediately, run `pm-plugin-development:analyze-script-failures` (for script issues), report the failure to the user with full context, and wait for user direction before continuing.

---

## Compliance Rules

### Rule 0 — Allowed `.plan` Access

These files are designed for direct access and do NOT trigger compliance alerts:

| File | Access | Purpose |
|------|--------|---------|
| `.plan/execute-script.py` | Execute | Universal script executor with embedded mappings |
| `.plan/plan_logging.py` | Import | Logging module |
| `.plan/local/marshall-state.toon` | Read/Write | Executor generation metadata |
| `.plan/local/logs/script-execution-*.log` | Append | Global execution logs |
| `.plan/local/lessons-learned/*.md` | Read/Write | Lessons-learned content (always via the manage-lessons skill) |

All other marketplace scripts must be invoked via the executor: `python3 .plan/execute-script.py {notation} [subcommand] {args...}`. Direct script invocation via an absolute path is a violation — it bypasses logging and response standardization.

### Rule 1 — No Direct `.plan/plans/**` Access

Plan data must use the manage-* API. Prohibited operations and their correct alternatives:

| Tool | Prohibited Pattern | Correct Alternative |
|------|--------------------|---------------------|
| Read | `.plan/plans/{id}/status.toon` | `manage-status:manage_status read --plan-id {id}` |
| Read | `.plan/plans/{id}/references.json` | `manage-references:manage-references read --plan-id {id}` |
| Read | `.plan/plans/{id}/work.log` | `manage-logging:manage-logging read --plan-id {id} --type work` |
| Read | `.plan/plans/{id}/solution_outline.md` | `manage-solution-outline:manage-solution-outline read --plan-id {id}` |
| Read | `.plan/plans/{id}/tasks/TASK-*.toon` | `manage-tasks:manage-tasks get --plan-id {id} --number {N}` |
| Write / Edit | any file under `.plan/plans/{id}/` | corresponding manage-* create/update subcommand |
| Glob / find / ls | anything under `.plan/plans/` | corresponding manage-* list subcommand |

**Allowed direct write pattern**: `Write(.plan/plans/{plan_id}/solution_outline.md)` is permitted when the path was obtained via `manage-solution-outline resolve-path --plan-id {id}` AND the write is immediately followed by `manage-solution-outline write` (or `update`) to validate.

Complete script coverage:

| File | Read | Write |
|------|------|-------|
| `request.md` | `manage-plan-documents:manage-plan-documents request read` | `manage-plan-documents:manage-plan-documents request create` |
| `solution_outline.md` | `manage-solution-outline:manage-solution-outline read` | `resolve-path` → `Write({path})` → `manage-solution-outline write` |
| `work.log` | `manage-logging:manage-logging read --type work` | `manage-logging:manage-logging work` |
| `lessons-learned/*.md` | `manage-lessons:manage-lessons get` | `manage-lessons:manage-lessons add` |
| Any plan file | `manage-files:manage-files read` | `manage-files:manage-files write` |

### Rule 2 — Work-Log Population Verification

After any planning operation completes, query `manage-logging:manage-logging read --plan-id {id} --type work` and verify that the most recent entry matches the operation (recent timestamp, correct entry type, current phase, and a meaningful summary). The required entry types by operation are: phase transitions → `progress`; decisions → `decision` with rationale detail; artifact creation → `artifact` with the artifact type and id; task completion → `outcome`; errors → `error` with error detail.

### Rule 3 — Status Consistency Verification

After phase transitions or progress updates, read status via `manage-status:manage_status read --plan-id {id}` and confirm `current_phase` matches the expected phase, every phase entry has the correct status, and the `updated` timestamp is recent. Verification triggers: phase transitions (`current_phase` updated, previous phase marked `done`), task completion (phase progress reflects completed tasks), error states (status shows `error`/`blocked`), and plan completion (all phases `done`).

### Rule 4 — Script Execution via Executor (Mandatory)

All marketplace script execution MUST use `python3 .plan/execute-script.py {bundle}:{skill}:{script} {subcommand} {args...}`.

**CRITICAL** — singular vs plural script names:

| Skill Name | Script Name | Full Notation |
|------------|-------------|---------------|
| `manage-plan-documents` | `manage-plan-document` | `plan-marshall:manage-plan-documents:manage-plan-documents` |
| `manage-tasks` | `manage-task` | `plan-marshall:manage-tasks:manage-tasks` |
| `manage-lessons` | `manage-lesson` | `plan-marshall:manage-lessons:manage-lessons` |
| `manage-status` | `manage_status` | `plan-marshall:manage-status:manage_status` |
| `manage-references` | `manage-references` | `plan-marshall:manage-references:manage-references` |
| `manage-files` | `manage-files` | `plan-marshall:manage-files:manage-files` |
| `manage-logging` | `manage-log` | `plan-marshall:manage-logging:manage-logging` |

Prohibited patterns: `python3 {script_path} {verb}`, `python3 marketplace/.../script.py`, and any direct-path form that embeds the bundle's scripts-subdirectory — always replace with the executor notation. The executor provides execution logging, notation consistency, error standardization, and a hook for future metrics or caching.

### Rule 5 — CI/Git Provider Access via Integration Scripts (Mandatory)

All GitHub (`gh`) and GitLab (`glab`) operations MUST use the CI integration scripts via the executor. Direct `Bash(gh ...)` or `Bash(glab ...)` calls are **blocking violations** — the process MUST stop immediately when detected. There are NO exceptions: every operation has a corresponding integration subcommand. If one is missing, extend the CI integration scripts instead of bypassing them.

| Command | Subcommands | Replaces |
|---------|-------------|----------|
| `pr` | `create`, `view`, `reply`, `resolve-thread`, `thread-reply`, `reviews`, `comments`, `merge`, `auto-merge`, `close`, `ready`, `edit` | `gh pr *` |
| `ci` | `status`, `wait`, `rerun`, `logs` | `gh pr checks`, `gh run *` |
| `issue` | `create`, `view`, `close` | `gh issue *` |

Required pattern: `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci {command} {subcommand} {args...}`.

### Rule 6 — Log File Verification and Issue Detection

Plan-related log files must exist, be well-formed, remain consistent, and be scanned for script-execution issues.

| File | Location | Purpose |
|------|----------|---------|
| `work.log` | `.plan/plans/{id}/work.log` | Semantic work entries (decisions, artifacts, progress) |
| `script-execution.log` | `.plan/plans/{id}/script-execution.log` | Script execution records for plan-scoped operations |
| `script-execution-*.log` | `.plan/logs/script-execution-{date}.log` | Global execution records (non-plan operations) |

Entries follow the format `[{timestamp}] [{level}] [SCRIPT] {notation} {subcommand} ({duration}s)` (success) and `[{timestamp}] [ERROR] [SCRIPT] {notation} {subcommand} failed (exit {code})` (failure).

Scan log files for common issue classes and respond per severity: `[ERROR]` entries (investigate root cause), repeated failures (systemic bug, fix immediately), slow executions over 30 s for simple ops (optimize or investigate hang), missing expected executions (executor not used), `usage:` or `argument` errors (wrong caller arguments), `ModuleNotFoundError`/`ImportError` (missing dependency), and `Permission denied` (access issue). Read logs via `manage-logging read` commands — direct `grep` inside the plan log tree is acceptable only for quick scans such as `grep '[ERROR]' .plan/plans/{plan_id}/script-execution.log`.

---

## Workflow Skill API Contract Verification (per phase)

After each planning phase completes, verify the artifacts comply with the workflow skill API contract. Reference: `plan-marshall:extension-api` (SKILL.md).

### Phase 1 — Init Complete

Contract: `plan-marshall:phase-1-init/SKILL.md`. Verify `manage-references:manage-references read --plan-id {plan_id}` exposes the required `domains` field (non-empty list of domain identifiers such as `java`, `javascript`, `plan-marshall-plugin-dev`, `generic`).

### Phase 2 — Solution Outline Complete

Contract: `plan-marshall:manage-solution-outline/standards/solution-outline-standard.md`. Verify via `manage-solution-outline:manage-solution-outline validate --plan-id {plan_id}`. Every deliverable must carry: `change_type` (create|modify|refactor|migrate|delete), `execution_mode` (automated|manual|mixed), `domain` (valid domain value), `profile` (`implementation` or `module_testing`), `depends` (`none`, `N`, `N. Title`, or `N, M`), explicit `Affected files` (no glob patterns), and a `Verification` entry (command + criteria). Optional fields: `suggested_skill`, `suggested_workflow`, `context_skills`.

Common violations and fixes: vague file references → enumerate explicitly; missing `depends` → add `depends: none` or proper reference; title-only `depends` → use `N. Title`; missing `domain` → add a valid domain from config; missing `context_skills` in delegation block → add empty list or valid skills.

### Phase 3 — User Review (Mandatory)

User must explicitly approve the solution outline before task creation. Verify via `manage-logging read --plan-id {plan_id} --type work` and confirm an entry recording approval exists. Task creation without user approval is a CRITICAL violation.

### Phase 4 — Tasks Created

Contract: `plan-marshall:manage-tasks/standards/task-contract.md`. Verify via `manage-tasks list` and `manage-tasks get --number {N}`. Required task fields: `deliverables` (non-empty), `depends_on` (`none` or `TASK-N`), `delegation.{skill,workflow,domain}`, `delegation.context_skills` (may be empty list), `steps` in TOON tabular format with file paths in the target column, `verification.commands`, and `verification.criteria`.

**Steps field contract (CRITICAL)**: steps MUST be file paths from the deliverable's `Affected files`, NEVER action descriptions. Format: `steps[N]{number,target,status}:` with file paths as targets.

Common violations: missing `context_skills`, descriptive step text, missing `deliverables` references → always map back to the solution outline.

---

## Automated Verification Rules

After each planning command/skill execution, verify:

- No direct `.plan` file access (except `request.md` read and the allow-listed files in Rule 0).
- A `work.log` entry exists for every significant operation.
- Status reflects the current phase correctly.
- All artifacts were created via manage-* scripts.
- No orphaned files exist in the `.plan` structure.
- `work.log` and `script-execution.log` exist and use the standard format.
- `script-execution.log` contains recent entries for all script calls and has been scanned for `[ERROR]` entries (none remaining unaddressed).
- No repeated script failures are visible in the logs.

## Integration with Commands

When `/plan-marshall` runs phases 1-4, verify after each action: `1-init` emits an `artifact` work-log entry and sets `phases[1-init]=in_progress`; configuration completion emits a `progress` entry and sets `phases[1-init]=done`, `current_phase=3-outline`; `3-outline` emits `artifact` entries per deliverable with progress updates; outline completion emits an `outcome` entry and sets `phases[3-outline]=done`, `current_phase=4-plan`.

When `/plan-marshall` runs phases 5-7, verify after each task: task started → `progress` entry, task status `in_progress`; step completed → `progress` entry, step marked complete; task completed → `outcome` entry, task status `done`; build verified → `outcome` entry; error → `error` entry with detail (may set blocked state); all tasks done → `progress` entry, `current_phase=6-finalize`.

## Common Violations

1. **Direct status read** — `Read .plan/plans/my-plan/status.toon`. Use `manage-status:manage_status read --plan-id my-plan`. Direct reads bypass the managed parser, may see partial data during atomic writes, and skip script validation.
2. **Missing work-log entry** — an artifact is created but no work-log entry exists. Breaks the audit trail and blocks debugging/progress tracking.
3. **Stale status after transition** — all tasks are done but `current_phase` is still the old phase. Phase routing will execute the wrong phase and the plan lifecycle breaks.
4. **Direct file creation** — `Write .plan/plans/my-plan/tasks/TASK-003.toon`. Use `manage-tasks add` (singular script name `manage-task`, full notation `plan-marshall:manage-tasks:manage-tasks`) with the task definition passed via stdin heredoc to avoid shell metacharacter issues. Bypassing this skips numbering, validation, and work-log entries.

## Exception Handling

Legitimate exceptions are lessons-learned access (always via the manage-lessons skill) and ad-hoc diagnostics/debugging **with explicit user approval**. Note that `request.md` and `solution_outline.md` are now managed via `manage-plan-documents` / `manage-solution-outline`. When an exception is truly required, document its justification, risk mitigation, scope (exact files and operations), and whether user approval was obtained.

## Post-Run Verification Pattern

Use after major operations:

```bash
# Verify work.log has recent entry
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging read \
  --plan-id {plan_id} --type work --limit 20

# Verify status is consistent
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}

# Verify no orphaned files
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files list \
  --plan-id {plan_id}
```

Expected: a work-log entry within the last few seconds, `current_phase` matches the expected value, and all files are properly registered.

## Post-Run Verification: Executor Pattern

After script operations complete, confirm the executor was used. For plan-scoped operations, query `manage-logging read --plan-id {plan_id} --type script --limit 20` and verify the entries match the scripts that were invoked. For global operations (no plan context), inspect the current-day global log at `.plan/logs/script-execution-$(date +%Y-%m-%d).log` — direct read access to global logs is acceptable. Success entries use the format `[{timestamp}] [INFO] [SCRIPT] {notation} {subcommand} ({duration}s)` and error entries use `[{timestamp}] [ERROR] [SCRIPT] {notation} {subcommand} failed (exit {code})`. Verify the timestamp is recent, the notation matches the expected script, and the level is INFO for success or ERROR for failures.
