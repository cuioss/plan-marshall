---
name: plugin-create
description: Create new marketplace component (agent, command, skill, or bundle)
allowed-tools: Skill, Read, Write, Edit, Glob, AskUserQuestion
---

# Create Marketplace Component

Create new agents, commands, skills, or bundles following marketplace standards.

## Usage

```
/plugin-create agent
/plugin-create command
/plugin-create skill
/plugin-create bundle
```

## WORKFLOW

When you invoke this command, I will:

1. **Parse component type** from parameters
   - If type provided: Validate it's one of [agent, command, skill, bundle]
   - If no type: Ask user which component type to create

2. **Load plugin-create skill and EXECUTE its workflow**:
   ```
   Skill: pm-plugin-development:plugin-create
   ```

   **CRITICAL HANDOFF RULES**:
   - DO NOT summarize or explain the skill content to the user
   - DO NOT describe what the skill says to do
   - IMMEDIATELY execute the workflow for the specified component type
   - Your next action after loading the skill MUST be a tool call, not text output
   - Follow the skill's workflow steps with MANDATORY markers
   - Execute without commentary until workflow completion

3. **Display result** only after creation workflow completes

## PARAMETERS

**Required**: `component_type` (agent|command|skill|bundle)
**Optional**: None

**Error Handling**:
- Invalid type → Display usage with valid types
- No type → Ask user interactively

## Examples

```
User: /plugin-create agent
Result: Invokes plugin-create:create-agent workflow

User: /plugin-create command
Result: Invokes plugin-create:create-command workflow

User: /plugin-create
Result: Asks "Which component type? (agent/command/skill/bundle)"

User: /plugin-create invalid
Result: Error: Invalid type 'invalid'. Use: agent, command, skill, or bundle
```

## CONTINUOUS IMPROVEMENT RULE

If you discover issues or improvements during execution, record them:

1. **Activate skill**: `Skill: plan-marshall:manage-lessons-learned`
2. **Record lesson** with:
   - Component: `{type: "command", name: "plugin-create", bundle: "pm-plugin-development"}`
   - Category: bug | improvement | pattern | anti-pattern
   - Summary and detail of the finding

## Related

- `/plugin-doctor` - Diagnose and fix issues in components
- `/plugin-maintain` - Update existing components
