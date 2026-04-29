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
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-3-outline) Bug fix: {bug_location}, root cause: {root_cause}"
```

## Analysis

1. **Root cause** — The actual defect
2. **Triggering conditions** — When does it happen
3. **Minimal fix** — Smallest change to fix it
4. **Regression scenario** — Test that would catch this bug

## Deliverable Structure

Always exactly 2 deliverables. The "2 deliverables" rule counts deliverables, not files or change-sites.

- **D1 (Fix)** MAY bundle multiple coordinated source edits plus their unit tests when those edits share a single test surface — e.g., a multi-site bug fix where every site is verified by the same test surface. D1 may therefore have multiple `Affected files` entries (production code AND its co-located unit tests).
- **D2 (Regression Test)** is the cross-cutting / end-to-end / integration regression test that exercises the fix from a user-visible angle. It earns its own deliverable because its verification contract differs from D1's local unit tests.
- D1 CANNOT absorb independent regression coverage — coverage with a different verification scope always becomes D2.

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
- `{path/to/buggy/file}` — and additional source files when the fix spans multiple coordinated change-sites
- `{path/to/co-located/unit/test}` — when the bundled unit tests share a single test surface with the fix

**Change per file:**
- `{file}`: {specific fix to apply}
- `{co-located test file}`: {unit-test addition or update covering the bundled change-sites}

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
- `{path/to/cross-cutting/test/file}`

**Change per file:**
- `{test_file}`: Add cross-cutting / end-to-end / integration test that reproduces the bug scenario from a user-visible angle

**Verification:**
- Command: {resolved test command from architecture}
- Criteria: Test passes with fix, would fail without fix

**Success Criteria:**
- Test covers the bug scenario
- Test passes
```

## Guidelines

- Keep fix minimal and focused — but "minimal" means smallest correct fix, not "single file"
- The "2 deliverables" rule counts deliverables, not files: D1 may bundle multiple coordinated source edits plus their co-located unit tests when they share a single test surface
- Always include the cross-cutting regression-test deliverable (D2) — it has a different verification contract from D1's unit tests
- Document root cause in fix deliverable
