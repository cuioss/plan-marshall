# Change Enhancement — Generic Outline Instructions

Instructions for `enhancement` change type. Handles requests to improve existing functionality.

## When Used

Requests with `change_type: enhancement`:
- "Improve error messages in the login flow"
- "Add validation to the existing form"
- "Extend the search to support filters"

## Discovery

Use Glob/Grep to find affected components:

1. **Target component** — Which existing code to modify
2. **Scope of change** — How much of the component is affected
3. **Downstream dependencies** — What other code depends on the modified component

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:outline-change-type) Enhancement: {N} files affected in {module}"
```

## Analysis

For each affected component:

1. **What changes** — Specific modifications needed
2. **What stays** — Behavior that must be preserved
3. **Test impact** — Which tests need updating

## Deliverable Structure

For each modification scope:

```markdown
### {N}. Enhance: {Component/Feature Name}

**Metadata:**
- change_type: enhancement
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {none|N}

**Profiles:**
- implementation
- module_testing (if test files are modified)

**Affected files:**
- `{path/to/existing/file1}`
- `{path/to/existing/file2}`

**Change per file:**
- `{file1}`: {specific modification}
- `{file2}`: {specific modification}

**Verification:**
- Command: {resolved command from architecture}
- Criteria: Build passes, enhanced functionality works

**Success Criteria:**
- Enhancement implemented as requested
- Existing behavior preserved
- Tests updated and passing
```

## Guidelines

- Enhancement = modify existing, not create new files (unless extending requires new files)
- Preserve existing behavior unless explicitly changing it
- Update affected tests
