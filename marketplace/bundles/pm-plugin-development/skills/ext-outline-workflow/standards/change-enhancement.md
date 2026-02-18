# Change Enhancement — Plugin Development Outline Instructions

Domain-specific instructions for `enhancement` change type in the plugin development domain. Handles enhancing existing marketplace components.

## Additional Skills Required

The parent skill (outline-change-type) loads `pm-plugin-development:ext-outline-workflow`. Additionally load:

```
Skill: pm-plugin-development:plugin-architecture
```

## Step 1: Determine Component Scope

Analyze request to identify which component types are affected:

| Component Type | Include if request mentions... |
|----------------|-------------------------------|
| skills | skill, standard, workflow, template |
| agents | agent, task executor |
| commands | command, slash command |
| scripts | script, Python, output, format |
| tests | test, testing, coverage |

## Step 2: Inventory Scan and Analysis

Follow ext-outline-workflow **Inventory Scan** with the component types and bundle scope from Step 1.

Clear stale assessments (ext-outline-workflow **Assessment Pattern**).

For each component file from inventory:

1. **Scope boundary check**: Does request define explicit exclusions? If matched content falls into excluded category -> CERTAIN_EXCLUDE.
2. **Relevance assessment**: Does this component contain functionality being enhanced? Would it need changes? Is it a test covering affected functionality?
3. Log assessment per file (ext-outline-workflow **Assessment Pattern**).

Verify via **Assessment Gate**.

## Step 3: Resolve Uncertainties

Follow ext-outline-workflow **Uncertainty Resolution** for any UNCERTAIN assessments.

## Step 4: Build Deliverables

For each CERTAIN_INCLUDE component, create deliverable. Add test update and bundle verification deliverables as needed. Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

## Constraints

### MUST NOT
- Create new files (enhancement = modify existing)
- Skip analysis step (must assess each component)

### MUST DO
- Resolve uncertainties with user
- Use ext-outline-workflow shared constraints
