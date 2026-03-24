---
name: build-npm
description: npm/npx build operations with execution, multi-parser architecture, and coverage analysis
user-invocable: false
---

# Build npm

## Enforcement

- Run scripts EXACTLY as documented using `python3 .plan/execute-script.py plan-marshall:build-npm:npm ...`
- Never invoke `npm` or `npx` directly outside of script internals
- All script output follows TOON format contract

---

npm/npx build execution with multi-parser output analysis and JavaScript coverage reporting.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not invoke npm/npx directly; all builds go through the script API
- Do not invent script arguments not listed in the operations table
- Do not bypass the multi-parser detection logic

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-npm:npm {command} {args}`
- npm vs npx routing is automatic; do not force one over the other

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `npm.py` | CLI + Library | npm/npx operations, `execute_direct()` |
| `js-coverage.py` | CLI | JavaScript coverage analysis |
| `_npm_parse_typescript.py` | Library | TypeScript error parsing |
| `_npm_parse_jest.py` | Library | Jest/Vitest test output parsing |
| `_npm_parse_eslint.py` | Library | ESLint output parsing |
| `_npm_parse_tap.py` | Library | TAP format test output parsing |
| `_npm_parse_errors.py` | Library | Generic npm error parsing |

## npm run (Primary API)

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm run \
    --targets "<command>" \
    [--workspace <name>] \
    [--working-dir <path>] \
    [--env "NODE_ENV=production"] \
    [--timeout <ms>] \
    [--mode <mode>]
```

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

## References

- `plan-marshall:extension-api` - Extension API contract
- `standards/npm-impl.md` - npm execution details
