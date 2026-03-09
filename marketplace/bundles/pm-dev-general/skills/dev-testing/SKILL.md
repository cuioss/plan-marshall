---
name: dev-testing
description: Language-agnostic testing methodology covering AAA pattern, test structure, organization, coverage, and determinism
user-invocable: false
---

# Testing Methodology Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Language-agnostic testing principles applicable across all technology stacks. This skill covers test structure, organization, coverage requirements, and reliability patterns.

## Workflow

### Step 1: Load Testing Methodology

**Important**: Load this standard for any testing work.

```
Read: standards/testing-methodology.md
```

This provides foundational rules for:
- AAA pattern (Arrange-Act-Assert)
- Test class organization (1:1 mapping, splitting thresholds)
- Test naming and readability
- Deterministic test paths (no branching in tests)
- Test data principles (generated, not hardcoded)

### Step 2: Load Coverage Standards (As Needed)

**Coverage Analysis** (load for coverage work):
```
Read: standards/testing-coverage.md
```

Use when: Analyzing test coverage, defining corner cases, or improving coverage metrics.

## Key Rules Summary

### AAA Pattern (Arrange-Act-Assert)

All tests follow three phases separated by blank lines:

1. **Arrange** — Set up test data and preconditions using generated values
2. **Act** — Execute the operation under test (single action)
3. **Assert** — Verify the expected outcome with meaningful messages

No phase comments (`// Arrange`, `// Act`, `// Assert`) — whitespace separation is sufficient.

### Test Organization

- One test class per production class (1:1 mapping)
- Split test classes at ~200 lines into focused groups
- Group related tests (3+ tests on same topic) using nesting constructs
- Separate unit tests from integration tests

### Test Reliability

- No branching logic in tests (`if/else`, `switch`, ternary)
- No fixed delays or sleeps — use polling or event-based waiting
- Deterministic test paths — each test exercises exactly one path
- Explicit assertions over implicit checks

### Coverage Requirements

- Minimum 80% line coverage
- Minimum 80% branch coverage
- Critical paths: near 100% coverage
- All public APIs must be tested

## Related Skills

- `pm-dev-java:junit-core` — JUnit 5 testing patterns
- `pm-dev-frontend:cui-cypress` — Cypress E2E testing
- `pm-dev-java-cui:cui-testing` — CUI test generator framework

## Standards Reference

| Standard | Purpose |
|----------|---------|
| testing-methodology.md | AAA pattern, test structure, naming, organization, determinism |
| testing-coverage.md | Coverage requirements, corner cases, boundary testing |
