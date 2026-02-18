# Change Bug Fix — Generic Outline Instructions

Instructions for `bug_fix` change type. Handles requests to fix defects.

## When Used

Requests with `change_type: bug_fix`:
- "Fix the login timeout issue"
- "Resolve the null pointer exception"
- "Correct the date formatting bug"

## Discovery

Use targeted search to find the bug:

1. **Bug location** — Identify the specific file and code with the defect
2. **Bug symptoms** — What incorrect behavior occurs
3. **Expected behavior** — What should happen instead

If request provides stack trace or error message, extract file paths and error location.

Log findings:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  decision --plan-id {plan_id} --level INFO --message "(pm-workflow:outline-change-type) Bug fix: {bug_location}, root cause: {root_cause}"
```

## Analysis

1. **Root cause** — The actual defect
2. **Triggering conditions** — When does it happen
3. **Minimal fix** — Smallest change to fix it
4. **Regression scenario** — Test that would catch this bug

## Deliverable Structure

Always exactly 2 deliverables:

```markdown
### {N}. Fix: {Bug Description}

**Metadata:**
- change_type: bug_fix
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: none

**Profiles:**
- implementation

**Root Cause:**
{Brief description of what's causing the bug}

**Affected files:**
- `{path/to/buggy/file}`

**Change per file:**
- `{file}`: {specific fix to apply}

**Verification:**
- Command: {resolved command from architecture}
- Criteria: Bug no longer reproduces, existing tests pass

**Success Criteria:**
- Root cause addressed
- Bug no longer reproduces
- No regression introduced

### {N+1}. Add regression test for {bug description}

**Metadata:**
- change_type: bug_fix
- execution_mode: automated
- domain: {domain}
- module: {module}
- depends: {N}

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `{path/to/test/file}`

**Change per file:**
- `{test_file}`: Add test that reproduces the bug scenario

**Verification:**
- Command: {resolved test command from architecture}
- Criteria: Test passes with fix, would fail without fix

**Success Criteria:**
- Test covers the bug scenario
- Test passes
```

## Guidelines

- Keep fix minimal and focused
- Always include regression test deliverable
- Document root cause in fix deliverable
