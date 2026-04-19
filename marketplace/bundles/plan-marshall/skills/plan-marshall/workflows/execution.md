# Execution Workflows (Phases 5 & 7)

Workflows for plan execution phases: execute (task implementation + verification) and finalize (commit, PR).

> **cwd for `.plan/execute-script.py` calls**: `manage-*` scripts (Bucket A) resolve `.plan/` via `git rev-parse --git-common-dir` and work from any cwd — do **NOT** pin cwd, do **NOT** pass `--project-dir`, and never use `env -C`. Build / CI / Sonar scripts (Bucket B) take `--project-dir {worktree_path}` explicitly when a worktree is active. See `plan-marshall:tools-script-executor/standards/cwd-policy.md`.

## Phase Handshake

Every phase transition is guarded by the `phase_handshake` script, which captures a fingerprint of key invariants on phase completion and verifies them on the next phase's entry. Drift between captured and observed invariants blocks progress until resolved or overridden. See [`../references/phase-handshake.md`](../references/phase-handshake.md) for the full contract, storage format, and invariant registry. The entry/completion protocols in [`phase-lifecycle.md`](../../ref-workflow-architecture/standards/phase-lifecycle.md) invoke the handshake automatically for all 6 phases.

## Action Routing

| Action | Workflow |
|--------|----------|
| `execute` (default) | Run execute phase (task iteration + verification) |
| `finalize` | Run finalize phase (commit, PR) |

### Default (no parameters)

Shows executable plans for selection:

```
Executable Plans:

1. jwt-authentication [execute] - Task 3/12: "Add token validation"
2. user-profile-api [finalize] - Ready to commit

0. Exit (use /plan-marshall to create or refine plans)

Select plan to execute:
```

### With plan parameter

Execute specific plan from its current phase:

If plan is in 1-init, 3-outline, or 4-plan phase:
```
Plan 'jwt-auth' is in '3-outline' phase.

This workflow handles 5-execute/6-finalize phases only.
Use /plan-marshall to complete 1-init through 4-plan phases first.
```

---

## Execute Phase (DUMB LOOP Pattern)

**Metrics**: Record phase start at the beginning of execute:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics start-phase \
  --plan-id {plan_id} --phase 5-execute
```

The execute phase iterates through tasks using a simple loop:

```bash
# Get next pending task
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks next --plan-id {plan_id}

# After each step completion, finalize step
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks finalize-step --plan-id {plan_id} --task {task_number} --step {step_number} --outcome done
```

For each task:
1. Read task details via manage-tasks
2. Delegate to domain agent based on domain
3. Mark task complete
4. Repeat until all tasks done

### Execute Phase Completion

After all tasks complete, transition and check auto-continue:

**Metrics**: During the task loop, maintain a running sum of `total_tokens`, `tool_uses`, and `duration_ms` from each task agent's `<usage>` tag. After all tasks complete, pass the aggregated totals to `end-phase`:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics end-phase \
  --plan-id {plan_id} --phase 5-execute \
  --total-tokens {sum of total_tokens from all task agent <usage> tags} \
  --tool-uses {sum of tool_uses from all task agent <usage> tags} \
  --duration-ms {sum of duration_ms from all task agent <usage> tags}
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics generate \
  --plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status transition \
  --plan-id {plan_id} --completed 5-execute
```

**Config check** — Read `finalize_without_asking` to determine next action:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --field finalize_without_asking --trace-plan-id {plan_id}
```

**IF `finalize_without_asking == true`**:
- Log: `"(plan-marshall:plan-marshall) Config: finalize_without_asking=true — auto-continuing to finalize"`
- Continue to **Finalize Phase** below

**ELSE (default)**:
- Display: `"Execute phase complete. Ready to finalize."`
- Display: `"Run '/plan-marshall action=finalize plan={plan_id}' when ready."`
- **STOP**

---

## Finalize Phase

**Metrics**: Record phase start:
```bash
python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics start-phase \
  --plan-id {plan_id} --phase 6-finalize
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:plan-marshall) Loading plan-marshall:phase-6-finalize"
```

Pass `session_id` (the current Claude Code conversation ID) alongside `plan_id` so `default:record-metrics` can call `manage-metrics enrich` on the live plan directory before `default:archive-plan` moves it:

```
Skill: plan-marshall:phase-6-finalize
operation: finalize
plan_id: {plan_id}
session_id: {session_id}
```

Handles:
- Commit and push changes
- Create PR (if configured)
- Automated review (CI, bot feedback)
- Sonar roundtrip (if configured)
- Knowledge capture (advisory)
- Lessons capture (advisory)
- Record final metrics (`end-phase` + `enrich` + `generate`, inside `default:record-metrics`)
- Mark plan complete
- Archive plan (move to `.plan/archived-plans/`)

All three `manage-metrics` commands (`end-phase`, `enrich`, `generate`) are executed inside `default:record-metrics` on the live plan directory before `default:archive-plan` runs. Do NOT add any `manage-metrics` invocation after `Skill: plan-marshall:phase-6-finalize` returns — a post-archive write recreates `.plan/local/plans/{plan_id}/` as an orphan directory.

### Finalize Validation

If finalize requested but tasks incomplete:
```
Cannot finalize: 5 tasks remaining.

Complete all tasks first, then run:
  /plan-marshall plan="jwt-auth" action="finalize"
```
