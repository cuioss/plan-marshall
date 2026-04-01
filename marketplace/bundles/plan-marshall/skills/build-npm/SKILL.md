---
name: build-npm
description: npm/npx build operations with execution, multi-parser architecture, and coverage analysis
user-invocable: false
---

# Build npm

npm/npx build execution with multi-parser output analysis and JavaScript coverage reporting.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not invoke npm/npx directly; all builds go through the script API
- Do not invent script arguments not listed in the operations table
- Do not bypass the multi-parser detection logic

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-npm:npm {command} {args}`
- Output format defaults to TOON; use `--format json` only when explicitly required
- Always analyze the result TOON: check `status` for success/error/timeout, review `errors` for failures
- npm vs npx routing is automatic; do not force one over the other

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `npm.py` | CLI | npm/npx operations dispatcher (includes coverage + warning config) |
| `js_coverage.py` | CLI | JavaScript coverage analysis |
| `_npm_execute.py` | Library | Execution config via factory pattern |
| `_npm_cmd_parse.py` | Library | Multi-parser dispatcher |
| `_npm_parse_typescript.py` | Library | TypeScript error parsing |
| `_npm_parse_jest.py` | Library | Jest/Vitest test output parsing |
| `_npm_parse_eslint.py` | Library | ESLint output parsing |
| `_npm_parse_tap.py` | Library | TAP format test output parsing |
| `_npm_parse_errors.py` | Library | Generic npm error parsing |

## Unified API

All build skills share the same subcommand structure. npm supports the common subcommands:

| Subcommand | Purpose |
|------------|---------|
| `run` | Execute build and auto-parse on failure (primary API) |
| `parse` | Parse npm/npx build output from log file |
| `coverage-report` | Parse JavaScript coverage report |
| `check-warnings` | Categorize build warnings against acceptable patterns |

**Not available**: `search-markers` (OpenRewrite is Java-specific, not applicable to npm projects).

### run (Primary API)

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm run \
    --command-args "<command>" \
    [--working-dir <path>] \
    [--env "NODE_ENV=production"] \
    [--timeout <seconds>] \
    [--project-dir <path>] \
    [--mode <mode>] \
    [--format <toon|json>]
```

**Parameters**:
- `--command-args` - Complete npm command arguments, e.g. `"run test"` or `"run test --workspace=pkg"` (required)
- `--working-dir` - Working directory for command execution
- `--env` - Environment variables (e.g. `"NODE_ENV=test CI=true"`)
- `--timeout` - Timeout in seconds (default: 300, adaptive via run-config, min floor: 60s)
- `--project-dir` - Project root directory (default: `.`)
- `--mode` - Output mode: actionable (default), structured, errors
- `--format` - Output format: toon (default), json

**Output Format (TOON)**:

Success:
```
status	success
exit_code	0
duration_seconds	12
log_file	.plan/temp/build-output/default/npm-2026-01-04-143022.log
command	npm run test
command_type	npm
```

Build Failed:
```
status	error
exit_code	1
duration_seconds	8
log_file	.plan/temp/build-output/default/npm-2026-01-04-143022.log
command	npm run test
command_type	npm
error	build_failed

errors[2]{file,line,message,category}:
src/utils/helper.js    42    Expected true, got false    test_failure
src/components/App.tsx  15   TS2339: Property 'x' missing    compilation_error

tests:
  passed: 40
  failed: 2
  skipped: 1
```

### parse

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm parse \
    --log <path> [--mode <mode>]
```

**Parameters**:
- `--log` - Path to npm build log file (required)
- `--mode` - Output mode: default, errors, structured (default)

### coverage-report

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm coverage-report \
    [--project-path <path>] \
    [--report-path <path>] \
    [--threshold <percent>]
```

**Parameters**:
- `--project-path` - Project directory (for auto-detection of report files)
- `--report-path` - Override coverage report path (default: auto-detect)
- `--threshold` - Coverage threshold percent (default: 80)

Supports Jest/Istanbul JSON (`coverage-summary.json`) and LCOV formats. Auto-detects format from file extension.

**Output Format (TOON)**:

```
status	success
passed	true
threshold	80
message	"Coverage meets threshold: 85.2% line, 78.3% branch"

overall:
  line	85.2
  branch	78.3
  function	81.5
  statement	87.1
```

### check-warnings

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm check-warnings \
    --warnings <json> [--acceptable-warnings <json>]
```

**Parameters**:
- `--warnings` - JSON array of warnings
- `--acceptable-warnings` - JSON object with acceptable patterns

## npm vs npx Detection

Commands are automatically routed to npm or npx:

```python
NPX_COMMANDS = ['playwright', 'eslint', 'prettier', 'stylelint', 'tsc', 'jest', 'vitest']
```

## Multi-Parser Architecture

```
npm build output → detect_tool_type(content, command)
    ├─→ "typescript" → parse_typescript()
    ├─→ "jest"       → parse_jest()
    ├─→ "eslint"     → parse_eslint()
    ├─→ "tap"        → parse_tap()
    ├─→ "npm_error"  → parse_npm_errors()
    └─→ "generic"    → Try each parser in sequence
```

## Error Categories

| Category | Description |
|----------|-------------|
| `compilation_error` | SyntaxError, TypeError, ReferenceError, TypeScript errors |
| `test_failure` | Jest/Vitest test failures, assertion errors |
| `lint_error` | ESLint, Prettier, StyleLint violations |
| `dependency_error` | Module not found, npm 404, ERESOLVE |
| `playwright_error` | Browser automation failures, timeouts |

## Module Discovery

npm module discovery reads `package.json` to detect workspaces and available scripts.

### Workspace Detection

For monorepo projects, the discovery scans `package.json` for a `workspaces` field. Each workspace gets its own module entry with scoped commands.

### Command Generation

Discovery generates canonical commands per module:

| Canonical | npm Command |
|-----------|-------------|
| `verify` | `run test` (or `run build && run test`) |
| `quality-gate` | `run lint` |
| `compile` | `run build` |
| `module-tests` | `run test` |
| `clean` | `run clean` (if script exists) |

Commands are only generated for scripts present in `package.json`.

## References

- `plan-marshall:extension-api` - Extension API contract
- `plan-marshall:extension-api/standards/build-execution.md` - Execution patterns and lifecycle
- `standards/npm-impl.md` - npm execution details
