# Change Tech Debt — Generic Outline Instructions

Instructions for `tech_debt` change type. Handles refactoring, cleanup, and code quality improvement requests.

## When Used

Requests with `change_type: tech_debt`:
- "Refactor the authentication module"
- "Remove deprecated API endpoints"
- "Migrate from callbacks to async/await"
- "Clean up unused code"

## Discovery

Use Glob/Grep to find code matching the refactoring pattern:

1. **Target pattern** — What code pattern to change
2. **Occurrences** — All files containing the pattern
3. **Dependencies** — Code that depends on affected code

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:outline-change-type) Refactoring: {pattern} in {N} files"
```

## Analysis

Based on compatibility setting:

| Compatibility | Strategy |
|---------------|----------|
| `breaking` | Clean-slate, remove old code immediately |
| `deprecation` | Mark old code deprecated, add new implementation |
| `smart_and_ask` | Assess impact, ask user for guidance |

## Deliverable Structure

For systematic changes:

```markdown
### {N}. Refactor: {Pattern/Module}

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {previous deliverable if sequential}

**Profiles:**
- implementation

**Refactoring:**
- Pattern: {what pattern is being changed}
- Strategy: {breaking|deprecation|smart_and_ask}

**Affected files:**
- `{path/to/file1}`
- `{path/to/file2}`
- `{path/to/file3}`

**Change per file:**
- `{file1}`: {specific refactoring to apply}
- `{file2}`: {specific refactoring to apply}
- `{file3}`: {specific refactoring to apply}

**Verification:**
- Command: {resolved command from architecture}
- Criteria: Build passes, behavior unchanged

**Success Criteria:**
- Old pattern is removed/deprecated
- New pattern is in place
- All tests pass
- No behavioral changes
```

For cleanup (if removing code):

```markdown
### {N+1}. Cleanup: Remove {Deprecated/Unused Code}

**Metadata:**
- change_type: tech_debt
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {refactoring deliverable}

**Profiles:**
- implementation

**Affected files:**
- `{path/to/file_to_clean}`

**Change per file:**
- `{file}`: Remove {what to remove}

**Verification:**
- Command: {resolved command from architecture}
- Criteria: Build passes, no references to removed code

**Success Criteria:**
- Deprecated/unused code removed
- No dangling references
- Build and tests pass
```

## Guidelines

- Refactor = structure change only, no behavior change
- Respect compatibility setting
- Group files by module (one deliverable per logical batch)
