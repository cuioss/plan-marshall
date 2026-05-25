# Change Enhancement — Generic Outline Instructions

Instructions for `enhancement` change type. Handles requests to improve existing functionality.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — the failure mode documented in lesson `2026-04-29-23-002` (silent swallowing of `wrong_parameters` rejections). "Log and continue" is the prohibited anti-pattern.

Step-level exceptions — calls whose non-zero exit is itself the signal (e.g., `manage-files exists` returning `exists: false`) — are documented inline in the step that issues them.

## When Used

Requests with `change_type: enhancement`:
- "Improve error messages in the login flow"
- "Add validation to the existing form"
- "Extend the search to support filters"

## Discovery

Use `architecture files --module X` / `architecture which-module --path P` for module-scoped discovery; fall back to Glob/Grep when narrowing to sub-module components, scanning content inside a known file, or when the architecture verb returns elision.

Identify:

1. **Target component** — Which existing code to modify
2. **Scope of change** — How much of the component is affected
3. **Downstream dependencies** — What other code depends on the modified component

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Enhancement: {N} files affected in {module}"
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
