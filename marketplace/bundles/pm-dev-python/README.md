# pm-dev-python

Python domain extension providing development standards and build infrastructure integration for plan-marshall workflows.

## Purpose

- Python development standards and best practices
- Build execution via pyprojectx (`./pw` wrapper)
- Integration with ruff, mypy, and pytest
- Runtime discovery of available build commands

## Skills

| Skill | Purpose |
|-------|---------|
| `python-best-practices` | Core Python development patterns |
| `ext-triage-python` | Triage extension for Python findings during plan-finalize phase |
| `plan-marshall-plugin` | Build infrastructure integration |

## Build Commands

The extension discovers commands from `[tool.pyprojectx.aliases]` in `pyproject.toml`:

| Canonical | Tool |
|-----------|------|
| `compile` | mypy on production sources |
| `test-compile` | mypy on test sources |
| `module-tests` | pytest |
| `quality-gate` | ruff check |
| `verify` | Full verification (compile + quality-gate + module-tests) |
| `coverage` | pytest with coverage |
| `clean` | Remove build artifacts |

## Usage

Commands are executed via the extension-api:

```bash
# Resolve and execute verify command
python3 .plan/execute-script.py plan-marshall:build-python:python_build run \
    --command-args "verify"
```

## Integration

This extension is discovered by:
- `extension-api` - Build system detection
- `manage-architecture` - Module discovery
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
