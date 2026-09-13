---
name: pm-dev-frontend-lint-config
description: ESLint flat config, Prettier, and Stylelint configuration, rule customization, and build integration standards for JavaScript projects
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# JavaScript Linting and Formatting Standards

## Enforcement

- **Prohibited actions**: Do not generate legacy ESLint config (`.eslintrc.*`); always use flat config (`eslint.config.js`)
- **Constraints**: All configurations require `"type": "module"` in package.json; flat config only

ESLint, Prettier, and Stylelint configuration standards for JavaScript projects.

## Prerequisites

- ESLint with flat config (`eslint.config.js`)
- `"type": "module"` in package.json

## Workflow

### Step 1: Load ESLint Configuration

Load this standard when setting up or modifying ESLint configuration.

```text
Call the `read` tool with `{ filePath: "standards/eslint-configuration.md" }` before continuing.
```

Covers ESLint flat config, dependencies, and plugin setup.

### Step 2: Load Additional Standards (As Needed)

**ESLint Rules** (load for rule customization):
```text
Call the `read` tool with `{ filePath: "standards/eslint-rules.md" }` before continuing.
```

Use when: Adding or modifying ESLint rules, configuring JSDoc rules, security rules, SonarJS, or framework-specific overrides.

**ESLint Integration** (load for build pipeline work):
```text
Call the `read` tool with `{ filePath: "standards/eslint-integration.md" }` before continuing.
```

Use when: Configuring npm scripts, Maven phases, CI/CD integration, or performance optimization for linting.

**Prettier Configuration** (load for formatting setup):
```text
Call the `read` tool with `{ filePath: "standards/prettier-configuration.md" }` before continuing.
```

Use when: Setting up Prettier, editor integration, or resolving ESLint/Prettier conflicts.

**Stylelint Setup** (load for CSS-in-JS linting):
```text
Call the `read` tool with `{ filePath: "standards/stylelint-setup.md" }` before continuing.
```

Use when: Configuring Stylelint for CSS-in-JS or Lit components, setting up CSS linting rules, or integrating with build pipelines.

## Related Skills

- `pm-dev-frontend:javascript` — JavaScript standards including JSDoc
- `pm-dev-frontend:css` — CSS standards (Stylelint)
- `pm-dev-frontend-cui:cui-javascript-project` — Project structure and Maven integration
