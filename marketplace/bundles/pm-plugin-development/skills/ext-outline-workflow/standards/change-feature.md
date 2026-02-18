# Change Feature — Plugin Development Outline Instructions

Domain-specific instructions for `feature` change type in the plugin development domain. Handles new marketplace component creation.

## Additional Skills Required

The parent skill (outline-change-type) loads `pm-plugin-development:ext-outline-workflow`. Additionally load:

```
Skill: pm-plugin-development:plugin-architecture
```

## Step 1: Determine Component Type

Analyze request to identify what component types to create:

| Request Pattern | Component Type |
|-----------------|----------------|
| "skill", "standard", "workflow" | skills |
| "agent", "task executor" | agents |
| "command", "slash command" | commands |

## Step 2: Identify Target Bundle

1. If request specifies bundle -> use specified bundle
2. If module_mapping provides bundle -> use mapped bundle
3. Otherwise -> ask user:

```
AskUserQuestion:
  question: "Which bundle should the new {component_type} be created in?"
  options: [{bundle1}, {bundle2}, ...]
```

## Step 3: Discover Patterns

Follow ext-outline-workflow **Inventory Scan** scoped to the target bundle and component type.

Read a few existing components of the same type to identify naming conventions, structure patterns, and test patterns to follow.

## Step 4: Build Deliverables

For each new component, create deliverable with extra section:

```markdown
**Component Details:**
- Type: {skill|agent|command}
- Name: {component_name}
- Bundle: {target_bundle}
```

Include plugin.json registration in affected files. Add test and bundle verification deliverables as needed. Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

## Constraints

### MUST NOT
- Modify existing components (feature = new only)
- Skip plugin.json registration deliverable

### MUST DO
- Follow plugin-architecture standards
- Include test deliverables
- Use ext-outline-workflow shared constraints
