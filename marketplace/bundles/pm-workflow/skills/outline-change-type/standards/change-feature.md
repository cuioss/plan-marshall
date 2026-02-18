# Change Feature — Generic Outline Instructions

Instructions for `feature` change type. Handles requests to create new functionality.

## When Used

Requests with `change_type: feature`:
- "Add user authentication"
- "Create a new API endpoint"
- "Implement dark mode"

## Discovery

Use Glob/Grep to understand the target area:

1. **Existing patterns** — Find similar components to follow conventions
2. **Target location** — Where new code should be created
3. **Dependencies** — What existing code the new feature interacts with

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:outline-change-type) Feature: {component_type} in {target_location}"
```

## Analysis

Determine:

1. **Component type** — What to create (class, module, endpoint, etc.)
2. **Interface points** — How it connects to existing code
3. **Test requirements** — What tests are needed

## Deliverable Structure

For each new component, create deliverable:

```markdown
### {N}. Create: {Component Name}

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {none|N}

**Profiles:**
- implementation
- module_testing (if test files are created)

**Affected files:**
- `{path/to/new/file1}`
- `{path/to/new/file2}`

**Change per file:**
- `{file1}`: Create {description}
- `{file2}`: Create {description}

**Verification:**
- Command: {resolved command from architecture}
- Criteria: Build passes, new component functional

**Success Criteria:**
- New component created following project conventions
- Integration points connected
- Tests pass (if included)
```

## Guidelines

- Follow existing project conventions for naming and structure
- Include interface/integration deliverables when the feature connects to existing code
- Add test deliverables where appropriate
