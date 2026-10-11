---
name: cui-javascript-project
description: JavaScript project structure, package.json configuration, dependency management, and Maven integration standards for consistent project setup and builds, plus the project-setup review rules a code review cites
user-invocable: false
mode: knowledge
---

# JavaScript Project Structure and Build Standards

## Enforcement

**Build output parsing**: Use `plan-marshall:build-npm` for npm/npx output analysis — this skill does not provide its own parser.

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

## Related Skills

- `pm-dev-frontend:javascript` — JavaScript standards including JSDoc
- `pm-dev-frontend:lint-config` — ESLint, Prettier, Stylelint configuration
- `plan-marshall:build-npm` — npm/npx build execution with multi-parser output analysis

## Review Rules

The review rules of the javascript-cui domain — what a code review looks for in a change to a CUI JavaScript project's structure and build. The block follows the harvestable block contract — see [`review-rubric.md` § 10 "Harvestable review-rule blocks"](../../../plan-marshall/skills/phase-6-finalize/standards/review-rubric.md) for its rules, which are not restated here.

- A `package.json` without `"type": "module"` in a project whose sources use `import` / `export`, so Node and Jest load the files as CommonJS and fail on the module syntax.
- A required npm script (`lint`, `format`, `test`, `test:ci-strict`, `quality`) removed or renamed, so the Maven build step that runs it fails, or a check the build relies on no longer runs.
- A dependency change in `package.json` with no matching `package-lock.json` change, so `npm ci` in the build rejects the mismatch or installs versions other than the ones tested locally.
- A JavaScript source file placed outside the source directory of the project's type (standard Maven, Quarkus DevUI, NiFi extension, standalone), so it is linted and tested but never packaged into the built artifact.
- A Node.js version in `package.json` `engines` that differs from the version the frontend-maven-plugin installs, so the local build and the Maven build run on different Node versions.
