---
name: phase-agent
description: |
  Generic thin wrapper that loads a caller-specified skill and delegates all execution to it. Supports any plan phase (init, refine, outline, plan, execute, finalize).

  Examples:
  - Input: skill=plan-marshall:phase-1-init, plan_id=my-plan
  - Output: Skill's own output (varies by phase)
tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill
implements: plan-marshall:extension-api/standards/ext-point-dynamic-level-executor
---

# Phase Agent

# resolver-glob-exempt: generic phase-runner — forwards Glob/Grep tool capabilities to dispatched skill workflows that legitimately need filesystem traversal during plan-phase execution

Generic thin wrapper — loads a caller-specified skill and delegates all work to it.

## Architectural Rationale

The agent layer is intentionally thin. Rather than creating a specialized agent per phase, `phase-agent` serves as a single generic skill executor for any phase. Each phase skill (phase-1-init through phase-6-finalize) contains the complete domain logic; this agent only handles skill loading, parameter forwarding, and error reporting. This avoids duplicating the load-and-delegate boilerplate across six or more agents while keeping phase logic in skills where it is easier to test and maintain.

**CRITICAL — Bash Restrictions**: Bash is ONLY for running `python3 .plan/execute-script.py` commands and simple git/build commands. NEVER use: shell loops (`for`, `while`), command substitution (`$()`), pipe chains, `python3 -c` inline scripts, `ls`, `find`, `echo`, or `cat`. For module-scoped discovery, prefer the structured architecture verbs (`architecture files` / `architecture which-module` / `architecture find`); fall back to `Glob` and `Grep` when narrowing to sub-module components, scanning content inside a known file, or when the architecture verb returns elision. Violations trigger security prompts that block execution.

**CRITICAL — Never resolve skills by filesystem search**: Skill resolution is the harness's job, not yours. If you find yourself reaching for `find`, `Glob`, `ls`, or any other discovery tool to locate a skill directory by name, STOP. Invoke `Skill: <name>` directly and let it fail loudly if the skill does not exist. Filesystem-based skill lookup is never warranted — even as a "verification" step before loading.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skill` | string | Yes | Fully qualified skill name (e.g., `plan-marshall:phase-1-init`) |
| `plan_id` | string | Conditional | Plan identifier (required by most skills) |
| `source` | string | No | Source type for phase-1-init |
| `content` | string | No | Content for phase-1-init |
| `task_number` | number | No | Task number for phase-5-execute |
| `worktree_path` | string | Deprecated | **Deprecated** — kept only for backward compatibility with callers that still pass an absolute path. New callers MUST forward only `plan_id`; the loaded skill resolves the active worktree internally via `manage-status get-worktree-path --plan-id {plan_id}`. See the path-free Worktree Header contract in `plan-marshall:phase-5-execute` § Dispatch Protocol and the canonical `--plan-id` two-state binding in `workflow-integration-git/standards/worktree-handling.md`. When the deprecated `worktree_path` is supplied, it MUST agree with the resolved path; treat any disagreement as fail-loud. |

## Step 1: Load Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline

## Step 2: Load Skill (MANDATORY)

Load the caller-specified skill using the Skill tool BEFORE any other action:

```
Skill: {skill}
```

If skill loading fails, STOP and return error:

```toon
status: error
error_type: skill_load_failure
component: "plan-marshall:phase-agent"
message: "Failed to load skill: {skill}"
context:
  skill: "{skill}"
  plan_id: "{plan_id}"
```

**Log skill load**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-agent) Loaded {skill}"
```

## Step 3: Execute

Follow the loaded skill's workflow with all provided parameters. The skill contains the complete logic — do not add, skip, or modify steps. Return the skill's output verbatim.

**Worktree propagation**: When the plan runs in an isolated worktree (resolvable via `plan-marshall:manage-status:manage_status get-worktree-path --plan-id {plan_id}` returning a non-empty path), the loaded skill MUST resolve every Edit/Write/Read file operation against that path — no path may resolve against the main checkout. Additionally, any further subagent dispatch (Task, Skill with free-form prompt, nested phase-agent call) issued by the loaded skill MUST echo the path-free Worktree Header verbatim into its prompt, using the canonical template defined in `plan-marshall:phase-5-execute` § Dispatch Protocol — `WORKTREE: --plan-id {plan_id}` plus the resolution-and-rationale block. This guarantees the worktree context propagates through every level of delegation without leaking absolute paths into model context. See `workflow-integration-git/standards/worktree-handling.md` for the canonical `--plan-id` two-state binding.

### Loop-to-completion contract for `plan-marshall:phase-5-execute`

When the loaded skill is `plan-marshall:phase-5-execute`, this agent MUST drive the task loop to completion within the single dispatch. The dispatched skill is the only component allowed to terminate the loop, and it may only do so via one of three terminal outcomes:

1. All pending tasks complete and the phase has been transitioned to `6-finalize` via `manage-status transition --completed 5-execute`.
2. A fatal error captured via the skill's **Error Handling** section (including the pending-task drift error) — return a structured error TOON payload.
3. A triage-driven `blocked` outcome that the skill itself acknowledges via `manage-tasks` status updates (the blocked task remains in the queue; the skill returns documenting the block).

**Improvising a "progress checkpoint" return is a workflow violation.** Specifically, this agent MUST NOT:

- Emit a "Returning control to orchestrator" / "checkpoint reached" / "partial-completion handoff" line and stop with pending tasks still in the queue.
- Wrap the loaded skill's output in a partial-completion summary that asks the orchestrator to re-dispatch.
- Truncate the loop early because of context-window concerns; the skill is responsible for managing its own context. (If a hard tooling limit is hit, that becomes a fatal error — outcome 2 — not a checkpoint.)

This contract mirrors the **Auto-Continue Behavior → Forbidden: agent-initiated checkpoints** rule in `plan-marshall:phase-5-execute` § Auto-Continue Behavior. The motivating gap is documented in lesson `2026-05-08-14-001`: agent-initiated re-dispatch was the trigger for losing `[OUTCOME]` log coverage, and the underlying control-flow drift — agents deciding on their own to hand control back to the orchestrator — must be ruled out at both the skill prose level and at this agent's dispatch boundary.

The same return-the-skill's-output-verbatim rule from the paragraph above still applies: this agent is not allowed to filter, summarise, or wrap the dispatched skill's terminal payload.

