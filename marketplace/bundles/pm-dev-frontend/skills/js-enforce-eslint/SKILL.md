---
name: js-enforce-eslint
description: ESLint v10, Prettier, and Stylelint configuration and rule standards for JavaScript projects
user-invocable: false
---

# JavaScript Linting and Formatting Standards

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

ESLint v10, Prettier, and Stylelint configuration standards for JavaScript projects.

## Prerequisites

- ESLint v10+ with flat config (`eslint.config.js`)
- `"type": "module"` in package.json

## Workflow

### Step 1: Load ESLint Configuration

Load this standard when setting up or modifying ESLint configuration.

```
Read: standards/eslint-configuration.md
```

Covers ESLint v10 flat config, dependencies, and plugin setup.

### Step 2: Load Additional Standards (As Needed)

**ESLint Rules** (load for rule customization):
```
Read: standards/eslint-rules.md
```

Use when: Adding or modifying ESLint rules, configuring JSDoc rules, security rules, SonarJS, or framework-specific overrides.

**ESLint Integration** (load for build pipeline work):
```
Read: standards/eslint-integration.md
```

Use when: Configuring npm scripts, Maven phases, CI/CD integration, or performance optimization for linting.

**Prettier Configuration** (load for formatting setup):
```
Read: standards/prettier-configuration.md
```

Use when: Setting up Prettier, editor integration, pre-commit hooks, or resolving ESLint/Prettier conflicts.

**Stylelint Setup** (load for CSS-in-JS linting):
```
Read: standards/stylelint-setup.md
```

Use when: Configuring Stylelint for CSS-in-JS or Lit components, setting up CSS linting rules, or integrating with build pipelines.

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

- `pm-dev-frontend:javascript` — JavaScript standards including JSDoc
- `pm-dev-frontend:css` — CSS standards (Stylelint)
- `pm-dev-frontend-cui:cui-javascript-project` — Project structure and Maven integration
