---
name: js-testing
description: JavaScript unit testing standards covering Jest and Vitest frameworks, DOM and web component testing, mocking patterns, async testing, and coverage configuration
user-invocable: false
---

# JavaScript Testing Standards

Unit testing standards for JavaScript projects using Jest or Vitest, covering test structure, DOM interaction, web component testing, mocking, async patterns, and coverage.

## Enforcement

- **Execution mode**: Reference — load specific standards on-demand based on current task
- **Prohibited actions**: Do not generate tests that depend on implementation internals; do not use arbitrary `setTimeout` waits in tests
- **Constraints**: Tests must follow AAA (Arrange-Act-Assert) pattern; each test verifies one behavior

## Prerequisites

- Jest 29+ or Vitest 1+
- jsdom test environment (for DOM/component testing)
- @testing-library/jest-dom (recommended for DOM assertions)

## Workflow

### Step 1: Load Test Fundamentals

Load this standard for any JavaScript test work.

```
Read: standards/test-fundamentals.md
```

Covers framework setup (Jest/Vitest), test structure, naming, AAA pattern, parameterized tests, coverage configuration, and ESLint integration for tests.

### Step 2: Load Additional Standards (As Needed)

**DOM and Component Testing** (load for UI/component tests):
```
Read: standards/dom-component-testing.md
```

Use when: Testing DOM manipulation, web components (Lit/custom elements), Testing Library queries, container-based component testing, or accessibility assertions.

**Mocking and Async Patterns** (load for mocking or async code):
```
Read: standards/mocking-async.md
```

Use when: Mocking modules or APIs, working with fetch mocks, testing async/await code, controlling timers, or managing test isolation.

## Related Skills

- `plan-marshall:dev-general-module-testing` — Language-agnostic testing methodology (AAA, coverage, reliability)
- `pm-dev-frontend:javascript` — Core JavaScript development standards
- `pm-dev-frontend:js-enforce-eslint` — ESLint configuration including Jest/Vitest plugins
