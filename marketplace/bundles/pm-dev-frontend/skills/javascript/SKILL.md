---
name: javascript
description: Core JavaScript development standards covering ES modules, modern patterns, code quality, async programming, and tooling
user-invocable: false
---

# JavaScript Development Standards

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Core JavaScript development standards covering modern JavaScript features (ES2022+), code quality practices, and async programming patterns.

## Prerequisites

- ES2015+ and ES modules
- npm and JavaScript build tools

## Standards

| Standard | Purpose |
|----------|---------|
| `standards/javascript-fundamentals.md` | ES modules, variables, functions, vanilla JS preference |
| `standards/code-quality.md` | Complexity limits, refactoring, code organization |
| `standards/modern-patterns.md` | Destructuring, template literals, spread/rest, array methods |
| `standards/async-programming.md` | Promises, async/await, error handling, concurrency |

For ESLint, Prettier, and Stylelint configuration, see `pm-dev-frontend:js-enforce-eslint`.

## Related Skills

- `plan-marshall:dev-general-code-quality` — Language-agnostic code quality principles
- `plan-marshall:dev-general-code-documentation` — Language-agnostic documentation principles
- `pm-dev-frontend:css` — CSS standards
- `pm-dev-frontend:js-enforce-eslint` — ESLint, Prettier, Stylelint configuration
