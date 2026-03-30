# pm-dev-frontend

Frontend development standards and tools - modern JavaScript, CSS, and web development.

## Purpose

This bundle provides general frontend development expertise through domain knowledge skills with integrated automation workflows and build system integration.

## Components Included

### Skills (5 skills)

1. **javascript** - Core JavaScript development standards
   - ES modules, modern patterns, async programming, code quality
   - JSDoc documentation standards and patterns
   - `jsdoc.py` analyzer script for violation detection

2. **css** - CSS development standards
   - Responsive design patterns
   - Quality tooling and linting

3. **js-enforce-eslint** - ESLint, Prettier, Stylelint configuration
   - Flat config setup and rule management
   - Build integration standards

4. **ext-triage-js** - Extension point for JavaScript finding triage

5. **plan-marshall-plugin** - JavaScript domain registration (internal extension, not registered in plugin.json)

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
    ├── js-enforce-eslint/       # ESLint, Prettier, Stylelint
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
