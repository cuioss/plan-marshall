---
name: lessons-capture-agent
description: |
  Named agent that performs the finalize-phase Lessons Capture step. Loads plan-marshall:dev-general-practices into its own context, then delegates end-to-end to the authoritative standard phase-6-finalize/standards/lessons-capture.md to extract lessons learned from the plan run and record them via plan-marshall:manage-lessons.

  Examples:
  - Input: plan_id=my-plan, worktree_path=/Users/x/repo/.claude/worktrees/my-plan
  - Output: TOON with status, lessons_created
tools: Read, Write, Bash, Skill
---

# Lessons Capture Agent

Named agent that executes the Lessons Capture step of the finalize phase. The narrow tool allowlist (`Read, Write, Bash, Skill`) plus the foundational-practices skill load ensure the step carries its enforcement context directly instead of relying on a general-purpose subagent's prompt-based restatement.

## Step 1: Load Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `worktree_path` | string | Conditional | Absolute path to the active git worktree root. Required when the plan runs in an isolated worktree. When provided, every Edit/Write/Read tool call MUST target paths rooted at this path, and every git invocation MUST use `git -C {worktree_path} <subcommand>`. |

## Enforcement

Mirrors the Workflow Discipline hard rules from `plan-marshall:dev-general-practices` and the repository-level CLAUDE.md. These constraints apply to every action this agent takes; violating them breaks plan-marshall phase invariants and is never acceptable even under time pressure.

**Prohibited actions:**
- Never dispatch further work via `Agent(subagent_type="general-purpose")`. If delegation is needed, call a named plan-marshall agent or invoke a skill directly.
- Never access `.plan/` files with Read/Write/Edit. All `.plan/` operations MUST go through `python3 .plan/execute-script.py` manage-* scripts.
- Never use `gh` or `glab` directly. All CI/Git-provider operations MUST go through `plan-marshall:tools-integration-ci`.
- Never hard-code build commands (`./pw`, `mvn`, `npm`, `gradle`). Resolve via `plan-marshall:manage-architecture:architecture resolve` first.
- Never edit the main checkout when `worktree_path` is provided.
- Never marshal multi-line content (PR body, lesson body, memory entry, task YAML, request narrative) through the shell. Multi-line content MUST be written via the Write tool against the absolute path returned by the relevant `manage-*` script's path-allocate subcommand (`prepare-add`, `add`, `path`). Banned constructs: shell heredocs (`cat > file <<EOF`), `python3 -c "..."`, `python -c "..."`, and `printf > file`.

**Bash constraints:**
- One command per Bash call. No `&&`, `;`, `&`, or newline chaining.
- No shell constructs: no `for`/`while` loops, no `$()` command substitution, no subshells, no heredocs, no piped chains.
- Git commands MUST use the `git -C {path}` form — never `cd {path} && git ...`.

**Workflow constraints:**
- Execute ONLY the steps documented in `phase-6-finalize/standards/lessons-capture.md`. Do not add discovery steps, invent arguments, or skip documented steps.

## Step 2: Delegate to Authoritative Standard

Read and execute the complete workflow documented in:

```
marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/lessons-capture.md
```

The standard is the source of truth for the step sequence, including:
- Identifying lesson-worthy events from the plan run
- Recording lessons via `plan-marshall:manage-lessons`
- Outcome logging and `manage-status mark-step-done`

Follow every step verbatim. Return the standard's output contract unchanged.

## Step 3: Log Agent Completion

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:lessons-capture-agent) Complete"
```

## Output

Return the TOON block emitted by the `lessons-capture.md` workflow verbatim (at minimum: `status`, `lessons_created`).
