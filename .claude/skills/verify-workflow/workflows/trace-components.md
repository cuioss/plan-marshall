# Trace Components Workflow

Collects all components (commands, skills, agents) and scripts used during workflow execution. Uses separate namespaces for attribution:
- **Components** (C1, C2, C3...): commands, skills, agents - decision-making orchestrators
- **Scripts** (S1, S2, S3...): execute-script.py invocations - utility tools

## Purpose

After running a workflow trigger, this workflow parses both conversation history AND work.log to build a complete inventory of all invoked components. The resulting trace enables precise attribution of findings to specific components.

## Output

Creates `{results_dir}/component-trace.md` (in the verification results directory) with:
- Sequential component IDs (C1, C2, ...) for commands, skills, agents
- Sequential script IDs (S1, S2, ...) for scripts
- Invocation order and dependencies
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

## Component Invocation Sequence

| ID | Type | Component | Notation | Invoked By |
|----|------|-----------|----------|------------|
```

## Step 2: Parse Conversation History

Review the conversation history from the workflow execution. Identify **component invocations** (not scripts):

**Commands** (user-invocable entry points):
- Pattern: `/command-name` or `Skill: skill-name` activation
- Example: `/plan-manage create`, `/verify-workflow test`

**Skills** (loaded via Skill tool):
- Pattern: `Skill: bundle:skill-name` or direct skill loading
- Example: `Skill: pm-workflow:phase-2-outline`

**Agents** (Task tool with subagent):
- Pattern: Task tool invocation with `subagent_type`
- Example: `Task: pm-workflow:solution-outline-agent`

**Note**: Scripts are tracked separately in Step 2.5.

## Step 2.5: Extract Components from work.log

The conversation history only shows top-level component invocations. Skills loaded internally by agents log their activity to work.log with component identifiers.

**Read the work.log:**
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  read --plan-id {plan_id} --type work
```

This returns structured TOON output with parsed log entries including timestamp, level, category, and message fields.

**Extract component identifiers:**
Parse log entries for the pattern `({bundle}:{skill})` to identify components:

```
[timestamp] [level] [tag] ({bundle}:{skill}) message
```

Example extractions:
- `(pm-workflow:phase-1-init)` → skill: phase-1-init
- `(pm-plugin-development:ext-outline-plugin)` → skill: ext-outline-plugin
- `(pm-workflow:phase-3-plan)` → skill: phase-3-plan

**Build invocation hierarchy:**
For each component found in work.log:
1. Check if it appears in conversation-visible components
2. If not, add it as an internal component
3. Determine parent by examining which agent was active when the skill logged

**Internal components loaded by agents:**
- Skills with `ext-outline-*` pattern → loaded by solution-outline-agent
- Skills with `ext-triage-*` pattern → loaded by finalize workflows

**Extract scripts from work.log:**
Scripts are identified by `[MANAGE-*]` tags or execute-script.py invocations. Track separately with S1, S2, ... IDs.

## Step 3: Build Component Sequence

Merge components from conversation history (Step 2) and work.log (Step 2.5).

**Component types** (use C1, C2, C3... namespace):
- command: User-invocable entry points
- skill: Loaded knowledge/workflow documents
- agent: Autonomous Task tool subagents

For each component:
1. Assign next sequential ID (C1, C2, C3, ...)
2. Determine component type (command, skill, agent)
3. Extract component name and notation
4. Identify what invoked it (user, or another component ID)

**Invocation Chain Rules:**
- User-initiated commands: `Invoked By = user`
- Skills loaded by commands/agents: `Invoked By = C{parent_id}`
- Internal skills from work.log: `Invoked By = C{agent_id}` (the agent that was active)

## Step 3.5: Build Scripts List

**Script types** (use S1, S2, S3... namespace):
- Scripts are tools invoked via execute-script.py
- Tracked separately as utilities, not decision-making components

For each script invocation found:
1. Assign next sequential ID (S1, S2, S3, ...)
2. Extract script name and notation
3. Identify the component that called it

## Step 4: Populate Trace Tables

**Component Invocation Sequence** (components only, no scripts):

```markdown
| ID | Type | Component | Notation | Invoked By |
|----|------|-----------|----------|------------|
| C1 | command | plan-manage | /plan-manage | user |
| C2 | agent | plan-init-agent | pm-workflow:plan-init-agent | C1 |
| C3 | skill | phase-1-init | pm-workflow:phase-1-init | C2 |
| C4 | agent | solution-outline-agent | pm-workflow:solution-outline-agent | C1 |
| C5 | skill | ext-outline-plugin | pm-plugin-development:ext-outline-plugin | C4 |
| C6 | agent | task-plan-agent | pm-workflow:task-plan-agent | C1 |
| C7 | skill | phase-3-plan | pm-workflow:phase-3-plan | C6 |
```

**Scripts Used** (separate table):

```markdown
| ID | Script | Notation | Called By |
|----|--------|----------|-----------|
| S1 | manage-config | pm-workflow:manage-config:manage-config | C3 |
| S2 | manage-log | plan-marshall:manage-logging:manage-log | C5 |
| S3 | manage-solution-outline | pm-workflow:manage-solution-outline:manage-solution-outline | C4 |
| S4 | manage-tasks | pm-workflow:manage-tasks:manage-tasks | C7 |
```

## Step 5: Add Summary Statistics

After the trace tables, add:

```markdown
## Summary

**Components:**
- Commands: {count}
- Skills: {count}
- Agents: {count}
- Total Components: {total}

**Scripts:**
- Total Scripts: {count}

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

Generated: 2026-01-19T10:30:00Z
Plan ID: migrate-outputs-to-toon

## Component Invocation Sequence

| ID | Type | Component | Notation | Invoked By |
|----|------|-----------|----------|------------|
| C1 | command | plan-manage | /plan-manage | user |
| C2 | agent | plan-init-agent | pm-workflow:plan-init-agent | C1 |
| C3 | skill | phase-1-init | pm-workflow:phase-1-init | C2 |
| C4 | agent | solution-outline-agent | pm-workflow:solution-outline-agent | C1 |
| C5 | skill | ext-outline-plugin | pm-plugin-development:ext-outline-plugin | C4 |
| C6 | agent | task-plan-agent | pm-workflow:task-plan-agent | C1 |
| C7 | skill | phase-3-plan | pm-workflow:phase-3-plan | C6 |

## Scripts Used

| ID | Script | Notation | Called By |
|----|--------|----------|-----------|
| S1 | manage-config | pm-workflow:manage-config:manage-config | C3 |
| S2 | manage-log | plan-marshall:manage-logging:manage-log | C5 |
| S3 | manage-solution-outline | pm-workflow:manage-solution-outline:manage-solution-outline | C4 |
| S4 | manage-tasks | pm-workflow:manage-tasks:manage-tasks | C7 |

## Summary

**Components:**
- Commands: 1
- Skills: 2
- Agents: 3
- Total Components: 6

**Scripts:**
- Total Scripts: 4

## Test References

Use these IDs to reference specific components in test criteria:
- C1: Initial trigger command (plan-manage)
- C2: Plan initialization agent (plan-init-agent)
- C3: Plan initialization skill (phase-1-init)
- C4: Solution outline agent (solution-outline-agent)
- C5: Plugin outline extension (ext-outline-plugin) ← internal skill loaded by C4
- C6: Task planning agent (task-plan-agent)
- C7: Task planning skill (phase-3-plan)
```

## Usage

This workflow is called by `test-and-verify.md` as Step V1.5 after the results directory is created. The `{results_dir}` variable is set in Step V4 of test-and-verify.md.
