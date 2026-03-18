---
name: cui-javascript-project
description: JavaScript project structure, package.json configuration, dependency management, and Maven integration standards for consistent project setup and builds
user-invocable: false
---

# JavaScript Project Structure and Build Standards

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Standards for JavaScript project setup, structure, dependencies, and Maven integration in CUI projects.

## Prerequisites

- npm package management
- Maven build lifecycle
- Node.js development

## Standards

| Standard | Purpose |
|----------|---------|
| `standards/project-structure.md` | Directory layouts, file naming, package.json, .gitignore |
| `standards/dependency-management.md` | Semantic versioning, security, ES module config |
| `standards/maven-integration.md` | frontend-maven-plugin, Maven phases, SonarQube |

## Project Types

| Type | Source Directory |
|------|----------------|
| Standard Maven | `src/main/resources/static/js/` |
| Quarkus DevUI | `src/main/resources/dev-ui/` |
| NiFi Extension | `src/main/webapp/js/` |
| Standalone | `src/main/js/` |

## Key Requirements

- `"type": "module"` in package.json for ES module support
- Required npm scripts: `lint`, `format`, `test`, `test:ci-strict`, `quality`
- Always commit `package-lock.json`, never commit `node_modules/`
- Node.js LTS version managed by frontend-maven-plugin

## Scripts

Script: `pm-dev-frontend:cui-javascript-project` → `npm-output.py`

| Subcommand | Description |
|------------|-------------|
| `parse` | Parse npm/npx build output logs and categorize issues |

## Related Skills

- `pm-dev-frontend:cui-javascript` — Core JavaScript development standards
- `pm-dev-frontend:js-enforce-eslint` — ESLint, Prettier, Stylelint configuration
- `pm-dev-frontend:js-fix-jsdoc` — JSDoc documentation standards
- `pm-dev-frontend:cui-cypress` — Cypress E2E testing
