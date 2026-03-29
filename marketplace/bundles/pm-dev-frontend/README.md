# pm-dev-frontend

Frontend development standards and tools - modern JavaScript, CSS, and web development.

## Purpose

This bundle provides general frontend development expertise through domain knowledge skills with integrated automation workflows and build system integration.

## Components Included

### Skills (6 skills)

1. **javascript** - Core JavaScript development standards
   - ES modules and modern patterns
   - Async programming and code quality

2. **css** - CSS development standards
   - Responsive design patterns
   - Quality tooling and linting

3. **js-fix-jsdoc** - JSDoc documentation standards
   - Documentation patterns for functions, classes, modules
   - `jsdoc.py` analyzer script

4. **js-enforce-eslint** - ESLint, Prettier, Stylelint configuration
   - Flat config setup and rule management
   - Build integration standards

5. **ext-triage-js** - Extension point for JavaScript finding triage

6. **plan-marshall-plugin** - JavaScript domain registration

> **Companion bundle**: `pm-dev-frontend-cui` provides additional standards (Maven integration, Quarkus DevUI, NiFi).

> **Planning Integration**: Frontend domain skills are loaded by plan-marshall task executors during plan execution via `task.skills` array.

## Architecture

```
pm-dev-frontend/
└── skills/
    ├── javascript/              # Core JS standards
    ├── css/                     # CSS standards
    ├── js-fix-jsdoc/            # JSDoc + violations workflow
    │   └── scripts/
    │       └── jsdoc.py
    ├── js-enforce-eslint/       # ESLint enforcement
    ├── ext-triage-js/           # Triage extension point
    └── plan-marshall-plugin/    # JavaScript domain registration
```

## Dependencies

### External Dependencies

- Python 3 for automation scripts
- Node.js and npm for JavaScript builds

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-frontend/
