# npm Implementation Standards

Standards for executing npm/npx builds in JavaScript projects.

---

## Command Construction

### npm vs npx Detection

Commands are automatically routed to either `npm` or `npx` based on the command:

**npx commands** (tools that should use npx):
- `playwright` - Playwright test runner
- `eslint` - ESLint linter
- `prettier` - Prettier formatter
- `stylelint` - StyleLint CSS linter
- `tsc` - TypeScript compiler
- `jest` - Jest test runner (when invoked directly)
- `vitest` - Vitest test runner (when invoked directly)

**npm commands** (npm scripts):
- `run <script>` - Execute package.json script
- `test` - Run test script
- `install` - Install dependencies
- `build` - Build production bundle

**Examples:**
```bash
# These use npx automatically
playwright test
eslint src/
prettier --check src/

# These use npm
run test
run build
test
install
```

### Workspace Targeting

For monorepo projects with npm workspaces:

**Detection:**
1. Read root `package.json`
2. Check for `workspaces` array
3. Validate workspace name exists

**Usage:**
```bash
# Single workspace build
npm run test --workspace=e-2-e-playwright

# Multiple workspaces
npm run test --workspace=pkg1 --workspace=pkg2
```

---

## Build Execution

### Log File Management

**Log file pattern:**
```
.plan/temp/build-output/{scope}/npm-{timestamp}.log
```

- `{scope}`: "default" (root build) or workspace name
- `{timestamp}`: `YYYY-MM-DD-HHMMSS` format

**Examples:**
- `.plan/temp/build-output/default/npm-2026-01-06-143022.log` - root build
- `.plan/temp/build-output/my-workspace/npm-2026-01-06-143030.log` - workspace build

**Output capture:**
All output goes to log file, not memory (R1 compliance).

### Timeout Management

**Timeout units:** All timeouts use **seconds** (not milliseconds).

**Default timeout:** 300 seconds (5 minutes), same as all other build skills. Adaptive timeout learning adjusts based on actual build duration.

**Timeout behavior:**
- Commands exceeding timeout return exit code 124
- Log file contains partial output up to timeout
- Build marked as FAILURE

### Exit Code Interpretation

**Exit codes:**
- `0` - Success
- `1` - General failure (test failures, lint errors, compilation errors)
- `124` - Timeout
- Other non-zero - Command-specific errors

---

## Output Parsing

### Error Categorization

**compilation_error:**
- `SyntaxError:`
- `TypeError:`
- `ReferenceError:`
- `error TS\d+:` (TypeScript)

**test_failure:**
- `✘` or `✖` (Jest/Vitest markers)
- `FAIL` messages
- `Expected.*to.*but.*received`
- `\d+ tests? failed`

**lint_error:**
- `eslint` messages
- `stylelint` messages
- `prettier` check failures
- ESLint format: `line:col error message rule-name`

**dependency_error:**
- `Cannot find module`
- `Module not found`
- `npm ERR! 404`
- `ERESOLVE` conflicts

**playwright_error:**
- `playwright` errors
- `page.goto: Timeout`
- `locator.click: Timeout`
- `selector.*not found`

### File Location Extraction

**Supported patterns:**

1. **TypeScript/ESLint style:**
   ```
   src/components/Button.js:15:3
   ```

2. **Webpack style:**
   ```
   @ ./src/components/Button.js 15:3
   ```

3. **Jest style:**
   ```
   at Object.<anonymous> (src/utils/helper.js:42:10)
   ```

4. **Playwright style:**
   ```
   tests/login.spec.js:15:5
   ```

---

## Working Directory

### Default Behavior

Commands execute from project root by default.

### Custom Working Directory

For projects with nested frontend directories:

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm execute \
    --command "run test" \
    --working-dir frontend/
```

---

## Acceptable Warnings

### Configuration

Acceptable warning patterns are stored in `run-configuration.json` under the `npm` section:

```json
{
    "npm": {
        "acceptable_warnings": [
            "ExperimentalWarning",
            "^.*peer dependency.*$"
        ]
    }
}
```

Patterns support substring matching and regex (patterns starting with `^`).

### Access

```
Skill: plan-marshall:manage-run-config
Workflow: Read Configuration
Field: npm.acceptable_warnings
```

---

## Best Practices

### Build Command Selection

**Test execution:**
- Use `run test` for package.json test script
- Use `run test:ci` for CI/CD environments
- Use `run test:coverage` for coverage generation

**Linting:**
- Use `run lint` for configured linters
- Use `npx eslint src/` for direct ESLint
- Use `run format:check` for Prettier validation

**Building:**
- Use `run build` for production builds
- Use `run dev` for development builds

### Environment Configuration

**Test environment:**
```bash
NODE_ENV=test CI=true npm run test
```

**Production build:**
```bash
NODE_ENV=production npm run build
```

**E2E tests:**
```bash
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e
```

---

## Module Discovery

npm module discovery reads `package.json` to detect workspaces and available scripts.

### Workspace Detection

For monorepo projects, the discovery scans `package.json` for a `workspaces` field:

```json
{
  "workspaces": ["packages/*", "apps/*"]
}
```

Each workspace gets its own module entry with scoped commands.

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

---

## Script Reference

**Notation**: `plan-marshall:build-npm:npm`

| Subcommand | Description |
|------------|-------------|
| `run` | Execute build and auto-parse on failure (primary API) |
| `parse` | Parse npm/npx build output and categorize issues |
| `coverage-report` | Parse JavaScript coverage report |
| `check-warnings` | Categorize build warnings against acceptable patterns |

### run Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--command-args` | Yes | - | Complete npm command arguments (e.g., "run test" or "run test --workspace=pkg") |
| `--working-dir` | No | - | Working directory for command execution |
| `--env` | No | - | Environment variables (e.g., "NODE_ENV=test CI=true") |
| `--timeout` | No | 300 | Build timeout in seconds |
| `--project-dir` | No | . | Project root directory |
| `--mode` | No | actionable | Output mode: actionable, structured, errors |
| `--format` | No | toon | Output format: toon or json |

**Example:**
```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm run \
    --command-args "run test" --timeout 180
```

---

## Issue Routing

| Issue Type | Target Command |
|------------|----------------|
| compilation_error | Fix via task executor |
| test_failure | Fix via task executor |
| lint_error | `/lint-config` |
| dependency_error | Manual fix |
| playwright_error | Fix via task executor |

---

## Coverage Report Paths

The coverage report parser searches these paths in order:

| Path | Format |
|------|--------|
| `coverage/coverage-summary.json` | Jest/Istanbul JSON |
| `coverage/lcov.info` | LCOV |
| `dist/coverage/coverage-summary.json` | Alternative JSON location |

Generate with: `npx jest --coverage` or `npx vitest run --coverage`
