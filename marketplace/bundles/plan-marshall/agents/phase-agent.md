---
name: phase-agent
description: Generic phase agent that loads a caller-specified skill and delegates execution
tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Skill
model: sonnet
---

# Phase Agent

Generic thin wrapper — loads a caller-specified skill and delegates all work to it.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skill` | string | Yes | Fully qualified skill name (e.g., `plan-marshall:phase-1-init`) |
| `plan_id` | string | Conditional | Plan identifier (required by most skills) |
| `source` | string | No | Source type for phase-1-init |
| `content` | string | No | Content for phase-1-init |
| `task_number` | number | No | Task number for phase-5-execute |

## Step 1: Load Foundational Practices

```
Skill: plan-marshall:dev-general-practices
```

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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-agent) Loaded {skill}"
```

## Step 3: Execute

Follow the loaded skill's workflow with all provided parameters. The skill contains the complete logic — do not add, skip, or modify steps. Return the skill's output verbatim.

