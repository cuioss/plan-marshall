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
| `cui-python` | Core Python development patterns |
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
python3 .plan/execute-script.py pm-dev-python:plan-marshall-plugin:python_build run \
    --commandArgs "verify"
```

## Integration

This extension is discovered by:
- `extension-api` - Build system detection
- `analyze-project-architecture` - Module discovery
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution-flow.md` - Execution lifecycle
