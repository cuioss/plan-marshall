---
name: build-npm
description: npm/npx build operations — TypeScript, Jest, ESLint, TAP parsing with workspace discovery, per-file JS coverage analysis, and automatic npm/npx routing
user-invocable: false
implements: plan-marshall:extension-api/standards/ext-point-build
---

# Build npm

npm/npx build execution with multi-parser output analysis and JavaScript coverage reporting.

## Enforcement

See `build-api-reference.md` § Enforcement for shared rules.
All commands use `python3 .plan/execute-script.py plan-marshall:build-npm:npm {command} {args}`.
npm vs npx routing is automatic; do not force one over the other.

## Scripts

| Script | Purpose |
|--------|---------|
| `npm.py` | CLI dispatcher |
| `js_coverage.py` | Deep per-file coverage analysis (standalone CLI) |
| `_npm_execute.py` | Execution config with npm/npx auto-detection (uses shared `default_command_key_fn`) |
| `_npm_cmd_parse.py` | Single-match parser registry dispatcher |
| `_npm_cmd_discover.py` | Module discovery via package.json workspaces |
| `_npm_parse_typescript.py` | TypeScript error parsing |
| `_npm_parse_jest.py` | Jest/Vitest test output parsing |
| `_npm_parse_eslint.py` | ESLint output parsing |
| `_npm_parse_tap.py` | TAP format test output parsing |
| `_npm_parse_errors.py` | Generic npm error parsing |

## Subcommands

Supports: **run**, **parse**, **coverage-report**, **check-warnings**, **discover**.
See `build-api-reference.md` for the full subcommand API and availability matrix.

### npm-Specific Behavior

- **run**: Additional `--working-dir` (monorepo nested frontends) and `--env` (e.g., `"NODE_ENV=test CI=true"`) parameters. Result includes `command_type` field (`npm`/`npx`)
- **coverage-report**: Searches `coverage/coverage-summary.json` (Jest/Istanbul), `coverage/lcov.info` (LCOV), `dist/coverage/coverage-summary.json`. Reports `function`/`statement` metrics instead of JaCoCo's `instruction`/`method`
- **discover**: Detects workspaces from `package.json` `workspaces` field (npm/yarn) and `pnpm-workspace.yaml` `packages` field (pnpm). Commands are conditional on available scripts

### js_coverage.py — Deep Coverage Analysis

Per-file coverage breakdown with CRITICAL/WARNING/OK classification, separate from the summary-level `coverage-report` subcommand:

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:js_coverage analyze \
    --report <path> --format json|lcov --threshold <percent>
```

## Parser Architecture

Uses a single-match parser registry: log content is analyzed to detect the tool type (TypeScript, Jest, ESLint, TAP, or npm errors), then routed to the matching parser. This differs from Python's multi-parser combination which runs all matching parsers.

## Module Discovery

Reads `package.json` to detect workspaces and available scripts.

## References

- `build-api-reference.md` — Shared subcommand API, error categories, issue routing, wrapper detection
- `build-execution.md` — Execution contract and lifecycle
- `standards/npm-impl.md` — npm-specific execution details
