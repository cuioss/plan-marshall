# pm-dev-python

Python domain extension providing development standards for plan-marshall workflows.

## Purpose

- Python 3.10+ development standards and best practices
- Pytest testing patterns with isolation, fixtures, and coverage
- Integration with ruff, mypy, and pytest toolchains
- Triage extension for Python findings during plan-finalize phase

## Skills (6 skills)

| Skill | Purpose |
|-------|---------|
| `python-core` | Core Python patterns — types, data structures, error handling, naming, imports |
| `pytest-testing` | Pytest standards — fixtures, isolation, mocking, assertions, coverage |
| `python-security` | Python security — injection sinks (subprocess, eval/exec, deserialization, SQL), path-traversal, untrusted-input handling |
| `arch-gate-python` | Python architectural-fitness gate — import-linter structural-boundary check emitting arch-constraint findings |
| `ext-triage-python` | Triage extension for Python findings during plan-finalize phase |
| `plan-marshall-plugin` | Python domain registration (extension implementor discovered via the Extension API, registered in plugin.json) |

## Architecture

```
pm-dev-python/
└── skills/
    ├── python-core/             # Core Python standards (reference)
    │   └── standards/
    │       └── python-core.md
    ├── pytest-testing/          # Pytest testing standards (reference)
    │   └── standards/
    │       └── testing-pytest.md
    ├── python-security/         # Python security standards (reference)
    ├── arch-gate-python/        # Python architectural-fitness gate
    ├── ext-triage-python/       # Triage extension point
    │   └── standards/
    │       ├── severity.md
    │       └── suppression.md
    └── plan-marshall-plugin/    # Domain extension (registered)
        ├── SKILL.md
        └── extension.py
```

## Build Operations

Build operations (pyprojectx execution, parsing, discovery) are provided by `plan-marshall:build-pyproject`, not this bundle. See `plan-marshall:extension-api/standards/build-execution.md` for execution patterns.

## Integration

This extension is discovered by:
- `extension-api` - Domain registration and build system detection
- `manage-architecture` - Module discovery
- `marshall-steward` - Project setup wizard

## Dependencies

No external dependencies. Pure reference material.

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-python/
