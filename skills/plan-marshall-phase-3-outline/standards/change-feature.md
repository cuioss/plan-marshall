# Change Feature — Generic Outline Instructions

Instructions for `feature` change type. Handles requests to create new functionality.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Step-level exceptions — calls whose non-zero exit is itself the signal (e.g., `manage-files exists` returning `exists: false`) — are documented inline in the step that issues them.

## When Used

Requests with `change_type: feature`:
- "Add user authentication"
- "Create a new API endpoint"
- "Implement dark mode"

## Discovery

Use `architecture files --module X` / `architecture which-module --path P` for module-scoped discovery and `architecture find --pattern P` to locate similar components across modules; fall back to Glob/Grep when narrowing to sub-module components, scanning content inside a known file, or when the architecture verb returns elision.

Identify:

1. **Existing patterns** — Find similar components to follow conventions
2. **Target location** — Where new code should be created
3. **Dependencies** — What existing code the new feature interacts with

> **Note**: When a feature deliverable also deletes or renames a public symbol it is replacing (e.g., "add new helper X, removing legacy helper Y"), run the consumer sweep documented in [`consumer-sweep.md`](consumer-sweep.md) before finalizing the deliverable's `Affected files` list.

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Feature: {component_type} in {target_location}"
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
