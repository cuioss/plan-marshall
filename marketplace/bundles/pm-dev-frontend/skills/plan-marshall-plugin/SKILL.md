---
name: plan-marshall-plugin
description: JavaScript domain extension with npm build operations and workflow integration
allowed-tools: [Read, Bash]
---

# Plan Marshall Plugin - JavaScript Domain

Domain extension providing JavaScript development capabilities to plan-marshall workflows, including npm/npx build execution with output parsing.

## Purpose

- Domain identity and workflow extensions (outline, triage)
- npm/npx build execution with parsed output
- Module detection for npm workspaces
- Profile-based skill organization

## Extension API

Configuration in `extension.py` implements the Extension API contract:

| Function | Purpose |
|----------|---------|
| `get_skill_domains()` | Domain metadata with profiles |
| `provides_triage()` | Returns `pm-dev-frontend:ext-triage-js` |
| `discover_modules(project_root)` | Discover npm modules with metadata, commands |

---

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `extension.py` | Extension | ExtensionBase implementation |
| `npm.py` | CLI + Library | npm/npx operations, `execute_direct()` |
| `_npm_parse_typescript.py` | Library | TypeScript error parsing |
| `_npm_parse_jest.py` | Library | Jest/Vitest test output parsing |
| `_npm_parse_eslint.py` | Library | ESLint output parsing |
| `_npm_parse_tap.py` | Library | TAP format test output parsing |
| `_npm_parse_errors.py` | Library | Generic npm error parsing |

---

## npm vs npx Detection

Commands are automatically routed to npm or npx:

```python
# npx commands (standalone tools)
NPX_COMMANDS = ['playwright', 'eslint', 'prettier', 'stylelint', 'tsc', 'jest', 'vitest']

# detect_command_type(args) returns:
#   "npx" for commands starting with NPX_COMMANDS
#   "npm" for all others
```

---

## Multi-Parser Architecture

Unlike Maven/Gradle, npm is a script runner that executes arbitrary tools. Each tool has its own output format:

```
npm build output
    │
    ▼
detect_tool_type(content, command)
    │
    ├─→ "typescript" → parse_typescript()
    ├─→ "jest"       → parse_jest()
    ├─→ "eslint"     → parse_eslint()
    ├─→ "tap"        → parse_tap()
    ├─→ "npm_error"  → parse_npm_errors()
    └─→ "generic"    → Try each parser in sequence
```

All parsers return unified `(issues, test_summary, build_status)` tuples.

---

## Timeout Learning

Command durations are recorded for adaptive timeouts:

```python
# Before execution
timeout = timeout_get("npm:test", default=120, project_dir=".")

# After execution
timeout_set("npm:test", duration=5, project_dir=".")
```

Default timeouts by command type:
- Build/test: 120 seconds
- E2E/Playwright: 180 seconds
- Lint/format: 60 seconds

---

## Build Operations

Scripts for npm/npx build execution.

### npm run (Primary API)

Unified command that executes build and returns parsed output on failure.

```bash
python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm run \
    --targets "<command>" \
    [--workspace <name>] \
    [--working-dir <path>] \
    [--env "NODE_ENV=production"] \
    [--timeout <ms>] \
    [--mode <mode>]
```

**Parameters**:
- `--targets` - npm/npx command to execute (required)
- `--workspace` - Workspace name for monorepo projects
- `--working-dir` - Working directory for command execution
- `--env` - Environment variables (e.g., 'NODE_ENV=test CI=true')
- `--timeout` - Timeout in milliseconds (default: 120000)
- `--mode` - Output mode: actionable (default), structured, errors

**Output Format (TOON)**:

Success:
```
status	success
exit_code	0
duration_seconds	5
log_file	.plan/temp/build-output/default/npm-2026-01-06-143022.log
command	npm run build
```

Build Failed:
```
status	error
exit_code	1
duration_seconds	3
log_file	.plan/temp/build-output/default/npm-2026-01-06-143022.log
command	npm run build
error	build_failed

errors[2]{file,line,message,category}:
src/index.js	42	SyntaxError: Unexpected token	compilation_error
src/utils.js	15	TypeError: Cannot read property	compilation_error
```

### Low-level Operations

| Command | Purpose |
|---------|---------|
| `npm execute` | Execute build, return log file reference |
| `npm parse` | Parse build output from log file |

---

## Output Modes

- **actionable** (default) - Errors + warnings NOT in acceptable_warnings
- **structured** - All errors + all warnings
- **errors** - Only errors, compact format

## Error Categories

| Category | Description |
|----------|-------------|
| `compilation_error` | SyntaxError, TypeError, ReferenceError, TypeScript errors |
| `test_failure` | Jest/Vitest test failures, assertion errors |
| `lint_error` | ESLint, Prettier, StyleLint violations |
| `dependency_error` | Module not found, npm 404, ERESOLVE |
| `playwright_error` | Browser automation failures, timeouts |

## Error Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| `build_failed` | Non-zero exit code | Errors included in response |
| `timeout` | Exceeded timeout | Increase timeout, check log_file |
| `execution_failed` | Process couldn't start | Check npm/node installed |
| `log_file_creation_failed` | Can't create log | Check permissions |

---

## Warning Handling

Manage warnings via run-config:

```bash
# Add accepted warning
python3 .plan/execute-script.py plan-marshall:run-config:run_config warning add \
    --category transitive_dependency \
    --pattern "peer dep warning ..." \
    --build-system npm

# List accepted warnings
python3 .plan/execute-script.py plan-marshall:run-config:run_config warning list
```

---

## Integration

This extension is discovered by:
- `extension-api` - Build system detection and command generation
- `skill-domains` - Domain configuration
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution-flow.md` - Complete execution lifecycle
- `standards/npm-impl.md` - npm execution details
