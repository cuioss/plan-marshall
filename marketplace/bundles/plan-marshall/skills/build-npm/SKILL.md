---
name: build-npm
description: npm/npx build operations with execution, multi-parser architecture, and coverage analysis
user-invocable: false
---

# Build npm

npm/npx build execution with multi-parser output analysis and JavaScript coverage reporting.

## Enforcement

See `plan-marshall:extension-api/standards/build-api-reference.md` § Enforcement for shared rules.

**Tool-specific constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-npm:npm {command} {args}`
- npm vs npx routing is automatic; do not force one over the other

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `npm.py` | CLI | npm/npx operations dispatcher (includes coverage + warning config) |
| `js_coverage.py` | CLI | Deep per-file coverage analysis (see section below) |
| `_npm_execute.py` | Library | Execution config via factory pattern |
| `_npm_cmd_parse.py` | Library | Multi-parser dispatcher |
| `_npm_cmd_discover.py` | Library | Module discovery via package.json workspaces |
| `_npm_parse_typescript.py` | Library | TypeScript error parsing |
| `_npm_parse_jest.py` | Library | Jest/Vitest test output parsing |
| `_npm_parse_eslint.py` | Library | ESLint output parsing |
| `_npm_parse_tap.py` | Library | TAP format test output parsing |
| `_npm_parse_errors.py` | Library | Generic npm error parsing |

Shared infrastructure from `extension-api`: `_build_execute_factory.py`, `_build_shared.py`, `_build_parse.py`, `_build_coverage_report.py`, `_build_check_warnings.py`.

## Subcommands

npm supports the shared subcommands documented in `build-api-reference.md`:
**run**, **parse**, **coverage-report**, **check-warnings**, **discover**.

Not available: `search-markers` (OpenRewrite is Java-specific).

### npm-Specific Notes

**run**: Additional parameters beyond the shared API:
- `--working-dir` — Working directory for command execution (for nested frontend projects in monorepos)
- `--env` — Environment variables (e.g., `"NODE_ENV=test CI=true"`)

The result TOON includes a `command_type` field (`npm` or `npx`) indicating which executable was used.

**coverage-report**: Auto-detects reports in these locations:
- `coverage/coverage-summary.json` (Jest/Istanbul JSON)
- `coverage/lcov.info` (LCOV format)
- `dist/coverage/coverage-summary.json`

The `overall` section includes `function` and `statement` metrics (instead of JaCoCo's `instruction` and `method`).

**discover**: Detects workspaces from:
1. `package.json` `workspaces` field (npm/yarn — array or object format)
2. `pnpm-workspace.yaml` `packages` field (pnpm)

Commands are conditional on scripts present in `package.json` (e.g., `compile` only generated if `build` or `typecheck` script exists).

### js_coverage.py — Deep Coverage Analysis

A standalone CLI tool for per-file coverage analysis, separate from the `coverage-report` subcommand:

- `coverage-report`: Summary-level threshold check (shared infrastructure, all build systems)
- `js_coverage.py analyze`: Deep per-file breakdown with CRITICAL/WARNING/OK classification

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:js_coverage analyze \
    --report <path> --format json|lcov --threshold <percent>
```

Use `js_coverage.py` when you need to identify specific files with low coverage, not just an overall pass/fail.

## npm vs npx Detection

Commands are routed based on a built-in `NPX_COMMANDS` list in `_npm_execute.py`. Direct tool invocations (prettier, eslint, jest, webpack, tsc, etc.) use `npx`; script invocations (`run test`, `run build`) use `npm`. Adding new CLI tools to the list requires a code change.

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

Detection uses content patterns (e.g., `error TS` for TypeScript, `FAIL` + `Tests:` for Jest). When multiple tools produce output in a single log, the single-dispatch routing may miss secondary tool output — for combined logs, `generic` mode tries all parsers in sequence.

## Error Categories

See `build-api-reference.md` § npm categories for the full table.

### Issue Routing

npm errors route to `pm-dev-frontend` bundle skills:

| Category | Target Skill |
|----------|-------------|
| `compilation_error` | `pm-dev-frontend:javascript` |
| `test_failure` | `pm-dev-frontend:jest-testing` |
| `lint_error` | `pm-dev-frontend:lint-config` |

## Module Discovery

Reads `package.json` to detect workspaces and available scripts.

### Command Generation

| Canonical | npm Command | Condition |
|-----------|-------------|-----------|
| `install` | `install` | Always |
| `verify` | `run build && run test` (or `run test`) | `build`/`test` scripts |
| `quality-gate` | `run lint` (or `run check`) | `lint`/`check` script |
| `compile` | `run build` (or `run typecheck`/`run type-check`) | `build`/`typecheck` script |
| `module-tests` | `run test` | `test` script |
| `coverage` | `run test:coverage` (or `run coverage`) | `test:coverage`/`coverage` script |
| `clean` | `run clean` | `clean` script |

Commands are only generated for scripts present in `package.json`.

## References

- `plan-marshall:extension-api/standards/build-api-reference.md` — Shared subcommand documentation
- `plan-marshall:extension-api/standards/build-execution.md` — Execution contract and lifecycle
- `standards/npm-impl.md` — npm-specific execution details
