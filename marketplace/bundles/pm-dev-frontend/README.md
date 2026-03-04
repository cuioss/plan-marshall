# CUI Frontend Expert

Frontend development standards and tools for CUI projects - modern JavaScript, CSS, and web development.

## Purpose

This bundle provides comprehensive frontend development expertise through domain knowledge skills with integrated automation workflows and build system integration.

## Components Included

### Skills (8 skills)

1. **cui-javascript** - Core JavaScript development standards
   - ES modules and modern patterns
   - Async programming and code quality
   - Best practices for CUI projects

2. **cui-javascript-project** - Project structure and build standards
   - Directory layouts, package.json configuration
   - Dependency management, Maven integration
   - `npm-output.py` build output parser

3. **cui-css** - CSS development standards
   - Responsive design patterns
   - Quality tooling and linting

4. **cui-cypress** - E2E testing with Cypress
   - Test organization and best practices
   - Build integration patterns

5. **js-fix-jsdoc** - JSDoc documentation standards
   - Documentation patterns for functions, classes, modules
   - `jsdoc.py` analyzer script

6. **js-enforce-eslint** - ESLint, Prettier, Stylelint configuration
   - Flat config setup and rule management
   - Build integration standards

7. **ext-triage-js** - Extension point for JavaScript finding triage

8. **plan-marshall-plugin** - Core infrastructure (npm build system, 6 parsers)

> **Planning Integration**: Frontend domain skills are loaded by plan-marshall task executors during plan execution via `task.skills` array.

## Architecture

```
pm-dev-frontend/
└── skills/
    ├── cui-javascript/          # Core JS standards
    ├── cui-javascript-project/  # Project structure + dependencies
    ├── cui-css/                 # CSS standards
    ├── cui-cypress/             # E2E testing
    ├── js-fix-jsdoc/            # JSDoc + violations workflow
    │   └── scripts/
    │       └── jsdoc.py
    ├── js-enforce-eslint/       # ESLint enforcement
    ├── ext-triage-js/           # Triage extension point
    └── plan-marshall-plugin/    # npm build system integration
        └── scripts/
            ├── npm.py
            └── npm-output.py
```

## Bundle Statistics

- **Skills**: 8 (domain knowledge with integrated workflows)
- **Scripts**: 3+ (Python automation)

## Dependencies

### External Dependencies

- Python 3 for automation scripts
- Node.js and npm for JavaScript builds

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-frontend/
