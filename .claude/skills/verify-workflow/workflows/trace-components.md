# Trace Components Workflow

Collects all skills, commands, agents, and scripts used during workflow execution. Assigns sequential identifiers (C1, C2, C3...) for test addressability.

## Purpose

After running a workflow trigger, this workflow parses execution history to build an inventory of all invoked components. The resulting trace enables precise attribution of findings to specific components.

## Output

Creates `{results_dir}/component-trace.md` (in the verification results directory) with:
- Sequential component IDs (C1, C2, ...)
- Invocation order and dependencies
- Component type and notation
- Summary statistics

## Step 1: Initialize Trace Document

Create the trace output file in the results directory:

```
Write: {results_dir}/component-trace.md
```

Initial content:

```markdown
# Component Trace: {test-id}

Generated: {timestamp}
Plan ID: {plan_id}

## Invocation Sequence

| ID | Type | Component | Notation | Invoked By |
|----|------|-----------|----------|------------|
```

## Step 2: Parse Execution History

Review the conversation history from the workflow execution. Identify each component invocation:

**Commands** (user-invocable entry points):
- Pattern: `/command-name` or `Skill: skill-name` activation
- Example: `/plan-manage create`, `/verify-workflow test`

**Skills** (loaded via Skill tool):
- Pattern: `Skill: bundle:skill-name` or direct skill loading
- Example: `Skill: pm-workflow:manage-solution-outline`

**Scripts** (executed via execute-script.py):
- Pattern: `python3 .plan/execute-script.py {notation}`
- Example: `python3 .plan/execute-script.py pm-workflow:manage-config:manage-config get`

**Agents** (Task tool with subagent):
- Pattern: Task tool invocation with `subagent_type`
- Example: `Task: pm-workflow:solution-outline-agent`

## Step 3: Build Invocation Sequence

For each component found in Step 2:

1. Assign next sequential ID (C1, C2, C3, ...)
2. Determine component type (command, skill, script, agent)
3. Extract component name and notation
4. Identify what invoked it (user, or another component ID)

**Invocation Chain Rules:**
- User-initiated commands: `Invoked By = user`
- Skills loaded by commands: `Invoked By = C{command_id}`
- Scripts called by skills: `Invoked By = C{skill_id}`
- Nested invocations follow the same pattern

## Step 4: Populate Trace Table

Add each component to the trace table in invocation order:

```markdown
| C1 | command | plan-manage | /plan-manage | user |
| C2 | skill | phase-1-init | pm-workflow:phase-1-init | C1 |
| C3 | script | manage-config | pm-workflow:manage-config:manage-config | C2 |
| C4 | skill | phase-2-outline | pm-workflow:phase-2-outline | C1 |
| C5 | script | manage-solution-outline | pm-workflow:manage-solution-outline:manage-solution-outline | C4 |
```

## Step 5: Add Summary Statistics

After the invocation table, add:

```markdown
## Component Summary

- Commands: {count}
- Skills: {count}
- Scripts: {count}
- Agents: {count}
- Total: {total_count}

## Test References

Use these IDs to reference specific components in test criteria:
- C1: {description of C1}
- C2: {description of C2}
- ...
```

## Step 6: Write Final Trace Document

Update the trace file with complete content:

```
Edit: {results_dir}/component-trace.md
```

## Output Format Example

```markdown
# Component Trace: migrate-json-to-toon

Generated: 2025-01-19T10:30:00Z
Plan ID: test-migrate-001

## Invocation Sequence

| ID | Type | Component | Notation | Invoked By |
|----|------|-----------|----------|------------|
| C1 | command | plan-manage | /plan-manage | user |
| C2 | skill | phase-1-init | pm-workflow:phase-1-init | C1 |
| C3 | script | manage-config | pm-workflow:manage-config:manage-config | C2 |
| C4 | skill | phase-2-outline | pm-workflow:phase-2-outline | C1 |
| C5 | script | manage-solution-outline | pm-workflow:manage-solution-outline:manage-solution-outline | C4 |
| C6 | skill | phase-3-plan | pm-workflow:phase-3-plan | C1 |
| C7 | script | manage-tasks | pm-workflow:manage-tasks:manage-tasks | C6 |

## Component Summary

- Commands: 1
- Skills: 3
- Scripts: 3
- Agents: 0
- Total: 7

## Test References

Use these IDs to reference specific components in test criteria:
- C1: Initial trigger command (plan-manage)
- C2: Plan initialization (phase-1-init)
- C3: Configuration management (manage-config)
- C4: Solution outline generation (phase-2-outline)
- C5: Solution outline script (manage-solution-outline)
- C6: Task planning (phase-3-plan)
- C7: Task management script (manage-tasks)
```

## Usage

This workflow is called by `test-and-verify.md` as Step V1.5 after the results directory is created. The `{results_dir}` variable is set in Step V4 of test-and-verify.md.
