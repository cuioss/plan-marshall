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

**Default timeouts:**
- Standard builds: 120 seconds (2 minutes)
- E2E/Playwright tests: 180 seconds (3 minutes)
- Lint/format: 60 seconds (1 minute)

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
python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm execute \
    --command "run test" \
    --working-dir frontend/
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

## Script Reference

### Primary API: npm_cmd_run.py

**Notation**: `pm-dev-frontend:plan-marshall-plugin:npm`

| Subcommand | Description |
|------------|-------------|
| `run` | Execute build and auto-parse on failure (primary API) |

**Parameters:**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--targets` | Yes | - | Build targets to execute (e.g., "run test") |
| `--workspace` | No | - | Workspace name for monorepo projects |
| `--working-dir` | No | . | Working directory for command execution |
| `--timeout` | No | 120 | Build timeout in seconds |
| `--mode` | No | actionable | Output mode: actionable, structured, errors |
| `--format` | No | toon | Output format: toon or json |

**Example:**
```bash
python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm run \
    --targets "run test" --timeout 180
```

### Internal Functions

The `npm.py` script exposes these internal functions for use by `extension.py`:

| Function | Description |
|----------|-------------|
| `execute_direct()` | Execute npm/npx command with adaptive timeout |
| `detect_command_type()` | Detect npm vs npx based on command |
| `get_bash_timeout()` | Calculate outer timeout with buffer |

---

## Issue Routing

| Issue Type | Target Command |
|------------|----------------|
| compilation_error | `/js-implement-code` |
| test_failure | `/js-implement-tests` |
| lint_error | `/js-enforce-eslint` |
| dependency_error | Manual fix |
| playwright_error | `/js-implement-tests` |
