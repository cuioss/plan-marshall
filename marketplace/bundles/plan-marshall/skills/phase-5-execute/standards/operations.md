# Delegation Operations

Reference for executing common checklist items. The executor uses these patterns when encountering specific checklist items.

**Manifest-driven execution**: This document does not encode any skip-conditional language for verification steps. Whether `quality-gate`, `module-tests`, or `coverage` fires at the end of Phase 5 is decided by the per-plan execution manifest (`manage-execution-manifest read`) Step 2 of `SKILL.md` consumes — the dispatch templates here are unconditional and only run when the manifest's `phase_5.verification_steps` list includes the corresponding step name.

## Worktree Header Protocol (Applies to ALL Dispatch Patterns)

When the plan runs in an isolated worktree, every `Task:` dispatch (and every other subagent dispatch that accepts a free-form prompt) below MUST have its `prompt:` block BEGIN with the following header, with `{worktree_path}` substituted by the active worktree absolute path surfaced by phase-5-execute's `[STATUS] Active worktree` work-log line:

```
WORKTREE: {worktree_path}
All Edit/Write/Read tool calls MUST target paths under this worktree. Raw tool invocations (git, mvn, npm, uv, pytest, ruff, …) MUST use the tool's native cwd flag against this path — `git -C`, `mvn -f`, `npm --prefix`, `uv --directory`, `pytest --rootdir`, `ruff <path>` (positional). The compound `cd <path> && <tool>` form is forbidden for every tool, not just git — it violates Bash one-command-per-call. File contents MUST be written via the Write/Edit tools, never via Bash redirects (`echo >>`, `cat <<EOF >`, `python3 -c "open(...).write(...)"`, `printf >`). See `dev-general-practices/standards/tool-usage-patterns.md` for the full rule and the native-cwd-flag table. NEVER edit the main checkout.
```

Omit the header only when no worktree is active (plan runs against the main checkout). The templates below show the header inline for every dispatch example.

## Build Operations

### Maven Build
**Trigger**: "Run build", "maven", "mvn verify"

```
Task:
  subagent_type: pm-dev-builder:maven-builder
  prompt: |
    WORKTREE: {worktree_path}
    All Edit/Write/Read tool calls MUST target paths under this worktree. Raw tool invocations (git, mvn, npm, uv, pytest, ruff, …) MUST use the tool's native cwd flag against this path. The `cd <path> && <tool>` form is forbidden. File contents MUST be written via Write/Edit, never via Bash redirects. See dev-general-practices/standards/tool-usage-patterns.md. NEVER edit the main checkout.

    Execute mvn clean verify, report results and coverage
```

### npm Build
**Trigger**: "npm build", "npm test"

```
Task:
  subagent_type: pm-dev-builder:npm-builder
  prompt: |
    WORKTREE: {worktree_path}
    All Edit/Write/Read tool calls MUST target paths under this worktree. Raw tool invocations (git, mvn, npm, uv, pytest, ruff, …) MUST use the tool's native cwd flag against this path. The `cd <path> && <tool>` form is forbidden. File contents MUST be written via Write/Edit, never via Bash redirects. See dev-general-practices/standards/tool-usage-patterns.md. NEVER edit the main checkout.

    Execute npm build and test, report results and coverage
```

## Quality Operations

### JavaScript Lint
**Trigger**: "lint", "eslint" (JavaScript context)

```bash
npm run lint
```

### Sonar Check
**Trigger**: "sonar", "quality gate"

```
mcp__sonarqube__search_sonar_issues_in_projects
```

## Implementation Operations

### JavaScript Implementation
**Trigger**: "implement" (JavaScript context)

```
Task:
  subagent_type: pm-dev-builder:npm-builder
  prompt: |
    WORKTREE: {worktree_path}
    All Edit/Write/Read tool calls MUST target paths under this worktree. Raw tool invocations (git, mvn, npm, uv, pytest, ruff, …) MUST use the tool's native cwd flag against this path. The `cd <path> && <tool>` form is forbidden. File contents MUST be written via Write/Edit, never via Bash redirects. See dev-general-practices/standards/tool-usage-patterns.md. NEVER edit the main checkout.

    Execute Task {N}: {name}, Goal: {goal}, Criteria: {list}
```

### Post-dispatch: Persist subagent usage to accumulator

**Applies to**: every Task / `execute-task` Skill dispatch above that returns a `<usage>` tag (i.e., every concrete task agent dispatched from the phase-5-execute task loop). Inline-only tasks skip this call.

After parsing the agent's returned `<usage>...</usage>` block, persist the totals to the on-disk per-phase accumulator so the orchestrator's end-of-phase `manage-metrics phase-boundary` call can read them even when the model context has been compacted between dispatches:

```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics accumulate-agent-usage \
  --plan-id {plan_id} --phase 5-execute \
  --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}
```

This call is documented as **Step 8b** in `phase-5-execute/SKILL.md`. The accumulator file lives at `.plan/plans/{plan_id}/work/metrics-accumulator-5-execute.toon` — see `manage-metrics/standards/data-format.md` § "Per-Phase Subagent Accumulator" for the schema.

## Git Operations

### Commit
**Trigger**: "commit", "create commit"

```
Skill: plan-marshall:workflow-integration-git
operation: commit
message: {from task title}
push: true
```

### Create PR
**Trigger**: "create PR", "pull request"

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
  --title "{task-title}" \
  --body "## Summary
{description}

**Related Issue**: {issue-link}

## Changes
{key changes}

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

## Plugin Operations

### Plugin Doctor
**Trigger**: "/plugin-doctor", "verify component"

```
SlashCommand: /plugin-doctor {type}={name}
```

## Documentation Operations

### JSDoc Check
**Trigger**: "jsdoc", "documentation check" (JavaScript)

```bash
npm run docs:check
```

## Logging Operations

### Work Log Entry
**Trigger**: "**Log**:", "Record completion"

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "{what was done}: {outcome}"
```

### Lesson Learned
**Trigger**: "**Learn**:", "Capture lesson"

Only execute if unexpected behavior occurred. Follow `plan-marshall:script-runner` Error Handling workflow.
