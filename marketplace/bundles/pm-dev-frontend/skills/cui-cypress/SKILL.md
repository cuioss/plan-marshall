---
name: cui-cypress
description: Cypress E2E testing standards including framework adaptations, test organization, and best practices
user-invocable: false
---

# Cypress E2E Testing Standards

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Standards for Cypress End-to-End testing in CUI projects extending base JavaScript testing standards with browser-based test automation patterns.

## Standards

| Standard | Purpose |
|----------|---------|
| `standards/cypress-configuration.md` | ESLint setup, complexity adaptations, global config |
| `standards/test-organization.md` | Directory layout, file naming, custom commands, constants |
| `standards/testing-patterns.md` | Session management, navigation, error handling, anti-patterns |
| `standards/console-monitoring.md` | Zero-error policy, allowed warnings, error tracking |
| `standards/build-integration.md` | npm scripts, Maven integration, CI/CD pipeline |

## Critical Rules

**Mandatory:**
- No branching logic (`if/else`, `switch`, ternary) in tests
- Use navigation helpers instead of direct `cy.visit()` or `cy.url()`
- Always verify session context after authentication
- Implement console error monitoring in all test suites

**Prohibited:**
- `cy.wait()` with fixed timeouts
- Element existence checks in test logic
- Manual session clearing without helpers
- Direct URL manipulation

## Related Skills

- `plan-marshall:dev-general-module-testing` — Language-agnostic testing principles
- `pm-dev-frontend:cui-javascript` — Base JavaScript standards
- `pm-dev-frontend:js-enforce-eslint` — ESLint configuration foundation
- `pm-dev-frontend:cui-javascript-project` — Project structure and dependencies
