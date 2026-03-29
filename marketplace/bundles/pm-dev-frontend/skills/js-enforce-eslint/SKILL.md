---
name: js-enforce-eslint
description: Enforce ESLint standards by fixing violations systematically
user-invocable: false
---

# JavaScript Linting and Formatting Standards

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

ESLint v9, Prettier, and Stylelint configuration standards for JavaScript projects.

## Prerequisites

- ESLint v9+ with flat config (`eslint.config.js`)
- `"type": "module"` in package.json

## Standards

| Standard | Purpose |
|----------|---------|
| `standards/eslint-configuration.md` | ESLint v9 flat config, dependencies, plugins |
| `standards/eslint-rules.md` | Rule definitions: JSDoc, security, SonarJS, framework overrides |
| `standards/eslint-integration.md` | Build pipeline, Maven phases, npm scripts, CI/CD |
| `standards/prettier-configuration.md` | Prettier setup, editor integration, pre-commit hooks |
| `standards/stylelint-setup.md` | Stylelint for CSS-in-JS / Lit components |

## Required npm Scripts

```json
{
  "scripts": {
    "lint:js": "eslint src/**/*.js",
    "lint:js:fix": "eslint --fix src/**/*.js",
    "format": "prettier --write \"src/**/*.js\"",
    "format:check": "prettier --check \"src/**/*.js\"",
    "quality": "npm run lint && npm run format:check",
    "quality:fix": "npm run lint:fix && npm run format"
  }
}
```

## Related Skills

- `pm-dev-frontend:javascript` — Core JavaScript standards
- `pm-dev-frontend:css` — CSS standards (Stylelint)
- `pm-dev-frontend:js-fix-jsdoc` — JSDoc documentation
- `pm-dev-frontend-cui:cui-javascript-project` — Project structure and Maven integration
