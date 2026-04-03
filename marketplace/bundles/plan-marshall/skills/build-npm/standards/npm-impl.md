# npm Implementation Standards

npm-specific standards for build execution and output parsing. For shared standards (timeouts, warnings, log files), see `extension-api/standards/build-systems-common.md`.

---

## Command Construction

### npm vs npx Detection

Commands are automatically routed to either `npm` or `npx` based on the command:

**npx commands** (tools that should use npx):
- Linters/formatters: `playwright`, `eslint`, `prettier`, `stylelint`
- TypeScript tools: `tsc`, `tsx`, `ts-node`
- Test runners: `jest`, `vitest`, `mocha`
- Bundlers: `webpack`, `rollup`, `esbuild`, `vite`
- Transpiler: `babel`

**npm commands** (npm scripts):
- `run <script>`, `test`, `install`, `build`

**Examples:**
```bash
# These use npx automatically
playwright test
eslint src/
prettier --check src/

# These use npm
run test
run build
```

### Workspace Targeting

For monorepo projects with npm workspaces:

```bash
# Single workspace build
npm run test --workspace=e-2-e-playwright

# Multiple workspaces
npm run test --workspace=pkg1 --workspace=pkg2
```

---

## Output Parsing

### Multi-Parser Architecture

npm output is detected and routed to tool-specific parsers via the shared `ParserRegistry`:

```
npm build output → detect_tool_type(content, command)
    ├─→ "typescript" → parse_typescript()
    ├─→ "jest"       → parse_jest()
    ├─→ "eslint"     → parse_eslint()
    ├─→ "tap"        → parse_tap()
    └─→ "npm_error"  → parse_npm_errors()
```

### File Location Extraction

**Supported patterns:**

1. **TypeScript/ESLint style:** `src/components/Button.js:15:3`
2. **Webpack style:** `@ ./src/components/Button.js 15:3`
3. **Jest style:** `at Object.<anonymous> (src/utils/helper.js:42:10)`
4. **Playwright style:** `tests/login.spec.js:15:5`

---

## Working Directory

### Custom Working Directory

For projects with nested frontend directories:

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm run \
    --command-args "run test" \
    --working-dir frontend/
```

---

## Best Practices

### Build Command Selection

**Test execution:**
- Use `run test` for package.json test script
- Use `run test:ci` for CI/CD environments

**Linting:**
- Use `run lint` for configured linters
- Use `npx eslint src/` for direct ESLint

**Building:**
- Use `run build` for production builds

### Environment Configuration

```bash
NODE_ENV=test CI=true npm run test           # Test environment
NODE_ENV=production npm run build            # Production build
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e  # E2E tests
```

---

## CI/CD Standards

### Environment Variables

```bash
export CI=true
export NODE_ENV=test
```

### Non-Interactive Mode

npm runs non-interactively when `CI=true` is set. This disables prompts and progress bars.

---

## Issue Routing

Routes to skills in the `pm-dev-frontend` bundle:

| Issue Type | Target Skill |
|------------|-------------|
| `compilation_error` | `pm-dev-frontend:javascript` |
| `test_failure` | `pm-dev-frontend:jest-testing` |
| `lint_error` | `pm-dev-frontend:lint-config` |
| `npm_dependency` | Manual package.json fix |
| `npm_error` | Manual npm configuration fix |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ERESOLVE dependency conflicts | Check peer dependency versions in package.json |
| E404 package not found | Verify package name and registry configuration |
| Build timeout | Increase `--timeout` or check for hanging processes |
| Workspace not found | Verify `workspaces` field in root package.json |
| TypeScript compilation slow | Use `--incremental` or project references |

---

## Coverage Report Paths

| Path | Format |
|------|--------|
| `coverage/coverage-summary.json` | Jest/Istanbul JSON |
| `coverage/lcov.info` | LCOV |
| `dist/coverage/coverage-summary.json` | Alternative JSON location |

Generate with: `npx jest --coverage` or `npx vitest run --coverage`

**Notation**: `plan-marshall:build-npm:npm`
