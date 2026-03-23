---
name: cui-javascript-project
description: JavaScript project structure, package.json configuration, dependency management, and Maven integration standards for consistent project setup and builds
user-invocable: false
---

# JavaScript Project Structure and Build Standards

## Enforcement

**Execution mode**: Reference skill with script automation. Load standards on-demand based on current task; invoke scripts via executor only.

**Prohibited actions:**
- Do not invent script notations -- use only the documented `pm-dev-frontend-cui:cui-javascript-project:npm-output` notation
- Do not import external dependencies in scripts -- stdlib-only

**Constraints:**
- Every script invocation uses the full `python3 .plan/execute-script.py` command with 3-part notation (Rule 9)
- Use `pm-dev-frontend-cui:cui-javascript-project:npm-output` notation for npm output parsing

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

**npm-output.py**: Parse npm/npx build output logs and categorize issues

| Subcommand | Description |
|------------|-------------|
| `parse` | Parse npm/npx build output logs and categorize issues |

**Usage**:
```bash
python3 .plan/execute-script.py pm-dev-frontend-cui:cui-javascript-project:npm-output parse --log {log_path}
python3 .plan/execute-script.py pm-dev-frontend-cui:cui-javascript-project:npm-output parse --log {log_path} --mode structured
```

## Related Skills

- `pm-dev-frontend:javascript` — Core JavaScript development standards
- `pm-dev-frontend:js-enforce-eslint` — ESLint, Prettier, Stylelint configuration
- `pm-dev-frontend:js-fix-jsdoc` — JSDoc documentation standards
