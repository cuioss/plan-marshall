# pm-dev-frontend

Frontend development standards and tools - modern JavaScript (ES2022+), CSS, and web development.

## Scope

This bundle covers **vanilla JavaScript** (.js, .mjs) and **CSS**. TypeScript (.ts), JSX (.jsx/.tsx), and framework-specific tooling (React, Angular, Vue) are out of scope.

## Purpose

This bundle provides general frontend development expertise through domain knowledge skills with integrated automation workflows and build system integration.

## Components Included

### Skills (8 skills)

1. **javascript** - Core JavaScript development standards
   - ES modules, modern patterns, async programming, code quality
   - JSDoc documentation standards and patterns
   - `jsdoc.py` analyzer script for violation detection

2. **css** - CSS development standards
   - Responsive design patterns
   - Quality tooling and linting

3. **lint-config** - ESLint, Prettier, Stylelint configuration
   - Flat config setup and rule management
   - Build integration standards

4. **jest-testing** - JavaScript unit testing standards
   - Jest framework setup and configuration
   - DOM and web component testing patterns
   - Mocking, async testing, and coverage

5. **javascript-security** - JavaScript security standards
   - DOM trust boundaries and XSS sinks (innerHTML/outerHTML/insertAdjacentHTML)
   - Safe text rendering, sanitization (DOMPurify), and Trusted Types

6. **arch-gate-js** - JavaScript architectural-fitness gate
   - dependency-cruiser-based structural-boundary check emitting arch-constraint findings

7. **ext-triage-js** - Extension point for JavaScript finding triage

8. **plan-marshall-plugin** - JavaScript domain registration (extension implementor discovered via the Extension API, registered in plugin.json)

> **Companion bundle**: `pm-dev-frontend-cui` provides additional standards (Maven integration, Quarkus DevUI, NiFi).

> **Planning Integration**: Frontend domain skills are loaded by plan-marshall task executors during plan execution via `task.skills` array.

## Architecture

```
pm-dev-frontend/
└── skills/
    ├── javascript/              # Core JS standards + JSDoc
    │   └── scripts/
    │       └── jsdoc.py
    ├── css/                     # CSS standards
    ├── lint-config/       # ESLint, Prettier, Stylelint
    ├── jest-testing/            # Jest testing standards
    ├── ext-triage-js/           # Triage extension point
    └── plan-marshall-plugin/    # JavaScript domain registration
```

## Dependencies

### External Dependencies

- Python 3 for automation scripts
- Node.js and npm for JavaScript builds

## See Also

- **Anthropic `frontend-design` skill** — Anthropic ships an official `frontend-design` skill for visual-aesthetic guidance (distinctive, production-grade UI; avoiding generic "AI slop" design). `pm-dev-frontend` and `frontend-design` are complementary: this bundle governs **code standards** (JavaScript/CSS correctness, structure, quality, tooling), while `frontend-design` governs **visual aesthetics** (layout, typography, design quality). Reach for `frontend-design` when the task is making an interface look distinctive and polished; reach for `pm-dev-frontend` when the task is writing correct, well-structured frontend code. This is a pointer only — `pm-dev-frontend` does not vendor or restate the `frontend-design` content.

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-frontend/
