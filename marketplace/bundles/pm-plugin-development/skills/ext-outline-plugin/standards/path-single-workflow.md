# Path-Single Workflow

Workflow for isolated changes that affect 1-3 components in a single bundle with no cross-references or dependencies.

## Workflow Steps

For isolated changes, identify the target components directly:

1. **Identify target bundle and component type**
2. **Read existing component** (if modify/refactor scope)
3. **Build deliverables section** for each component to create/modify

## Decision Logging

Log path selection and targets:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[DECISION] (pm-plugin-development:ext-outline-plugin) Path-Single: {N} components, bundle={bundle}"

python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "[ARTIFACT] (pm-plugin-development:ext-outline-plugin) Targets: {component-list}"
```

## Deliverable Template

Build a deliverables markdown section following the contract from `pm-workflow:manage-solution-outline/standards/deliverable-contract.md`.

**IMPORTANT**: Every field shown below is REQUIRED. Missing fields will cause validation to fail.

```markdown
### 1. {Action Verb} {Component Type}: {Name}

**Metadata:**
- change_type: {create|modify|refactor}
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- suggested_skill: pm-plugin-development:{plugin-create|plugin-maintain}
- suggested_workflow: {create-skill|create-command|create-agent|update-component}
- context_skills: []
- depends: none

**Affected files:**
- `marketplace/bundles/{bundle}/{type}/{name}.md`

**Change per file:** {What will be created or modified in each file}

**Verification:**
- Command: `/pm-plugin-development:plugin-doctor --component marketplace/bundles/{bundle}/{type}/{name}.md`
- Criteria: No quality issues detected

**Success Criteria:**
- {Specific measurable criterion 1}
- {Specific measurable criterion 2}
```

### Field Reference

| Field | Valid Values | Description |
|-------|--------------|-------------|
| `change_type` | create, modify, refactor | What kind of change |
| `execution_mode` | automated, manual, mixed | Can it run without human intervention |
| `domain` | plan-marshall-plugin-dev | Always "plan-marshall-plugin-dev" for marketplace components |
| `suggested_skill` | pm-plugin-development:plugin-create, pm-plugin-development:plugin-maintain | Skill to delegate to |
| `suggested_workflow` | create-skill, create-command, create-agent, update-component | Workflow within skill |
| `context_skills` | [] or [skill1, skill2] | Additional skills to load |
| `depends` | none, or deliverable number(s) | Dependencies on other deliverables |

## Decomposition Patterns

| Request Pattern | Typical Deliverables |
|-----------------|----------------------|
| "Add new skill" | 1. Create SKILL.md 2. Add standards docs 3. Create scripts 4. Update plugin.json |
| "Add new command" | 1. Create command.md 2. Implement skill delegation 3. Update plugin.json |
| "Add new agent" | 1. Create agent.md 2. Define tool requirements 3. Update plugin.json |
| "Fix command X" | 1. Update command with fix |
