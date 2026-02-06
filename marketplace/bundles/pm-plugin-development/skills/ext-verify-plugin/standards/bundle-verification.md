# Bundle Verification Commands

Bundle-level verification commands for test and quality gate deliverables.

## Test Verification

For deliverables that create or modify tests:

```bash
./pw module-tests {bundle}
```

Runs pytest for the specified bundle's test directory.

### Deliverable Template

```markdown
**Verification:**
- Command: `./pw module-tests {bundle}`
- Criteria: Tests pass
```

## Quality Gate Verification

For deliverables that span multiple files or need full verification:

```bash
./pw verify {bundle}
```

Runs the full verification pipeline: compile (mypy) + quality-gate (ruff) + module-tests (pytest).

### Deliverable Template

```markdown
**Verification:**
- Command: `./pw verify {bundle}`
- Criteria: All tests pass, mypy passes, ruff passes
```

## Decision Guide

| Deliverable Scope | Verification Command |
|-------------------|---------------------|
| Single test file | `./pw module-tests {bundle}` |
| Single component | Plugin-doctor (see component-verification.md) |
| Multiple components in one bundle | `./pw verify {bundle}` |
| Cross-bundle changes | `./pw verify {bundle}` per affected bundle |
