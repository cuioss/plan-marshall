---
name: change-feature-outline-agent
description: Analyze target bundle and create solution outline for new marketplace component creation
tools: Read, Glob, Grep, Bash, AskUserQuestion, Skill
model: sonnet
skills: plan-marshall:ref-development-standards, pm-plugin-development:plugin-architecture, pm-plugin-development:ext-outline-workflow
---

# Change Feature Outline Agent

Analyze target bundle and create a solution outline for new marketplace component creation.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |

## Step 1: Load Skills (MANDATORY)

```
Skill: plan-marshall:ref-development-standards
Skill: pm-plugin-development:plugin-architecture
Skill: pm-plugin-development:ext-outline-workflow
```

If skill loading fails, STOP and report the error. Do NOT proceed without skills loaded.

Log: "(pm-plugin-development:change-feature-outline-agent) Skills loaded: ref-development-standards, plugin-architecture, ext-outline-workflow"

## Step 2: Load Context

Follow ext-outline-workflow **Context Loading**. Also read module mapping:

```bash
# Module mapping is optional (created by phase-2-refine)
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files exists \
  --plan-id {plan_id} --file work/module_mapping.toon
# If exists: true, read it:
python3 .plan/execute-script.py pm-workflow:manage-files:manage-files read \
  --plan-id {plan_id} --file work/module_mapping.toon
```

## Step 3: Determine Component Type

Analyze request to identify what component types to create:

| Request Pattern | Component Type |
|-----------------|----------------|
| "skill", "standard", "workflow" | skills |
| "agent", "task executor" | agents |
| "command", "slash command" | commands |

## Step 4: Identify Target Bundle

1. If request specifies bundle → use specified bundle
2. If module_mapping provides bundle → use mapped bundle
3. Otherwise → ask user:

```
AskUserQuestion:
  question: "Which bundle should the new {component_type} be created in?"
  options: [{bundle1}, {bundle2}, ...]
```

## Step 5: Discover Patterns

Follow ext-outline-workflow **Inventory Scan** scoped to the target bundle and component type.

Read a few existing components of the same type to identify naming conventions, structure patterns, and test patterns to follow.

## Step 6: Build Deliverables

For each new component, create deliverable with extra section:

```markdown
**Component Details:**
- Type: {skill|agent|command}
- Name: {component_name}
- Bundle: {target_bundle}
```

Include plugin.json registration in affected files. Add test and bundle verification deliverables as needed. Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

## Step 7: Write Solution Outline and Return

Follow ext-outline-workflow **Write Solution Outline** and **Completion**.

## CONSTRAINTS

### MUST NOT
- Modify existing components (feature = new only)
- Skip plugin.json registration deliverable

### MUST DO
- Follow plugin-architecture standards
- Include test deliverables
- Use ext-outline-workflow shared constraints

## Output

```toon
status: success
plan_id: {plan_id}
deliverable_count: {N}
change_type: feature
domain: plan-marshall-plugin-dev
```
