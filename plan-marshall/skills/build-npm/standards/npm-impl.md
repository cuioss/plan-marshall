# npm Implementation Standards

npm-specific standards for build execution and output parsing. For shared standards (timeouts, warnings, log files), see `extension-api/standards/build-systems-common.md`. For npm/npx detection rules and multi-parser architecture, see SKILL.md and `build-api-reference.md`.

---

## Build Command Construction

### Base Command

npm commands are routed automatically between `npm` and `npx` based on the command type. Direct tool invocations (eslint, tsc, jest, etc.) use `npx`; package script invocations use `npm`.

### Common Commands

| Command | Purpose |
|---------|---------|
| `run test` | Run package.json test script |
| `run build` | Production build |
| `run lint` | Run configured linters |
| `run test:ci` | CI/CD test script |
| `npx eslint src/` | Direct ESLint invocation |
| `npx tsc --noEmit` | Type-check without emit |
| `npx playwright test` | E2E test execution |

---

## Module Targeting

### Working Directory

For projects with nested frontend directories:

```bash
python3 .plan/execute-script.py plan-marshall:build-npm:npm run \
    --command-args "run test" \
    --working-dir frontend/
```

### Workspace Targeting

For monorepo workspace builds:

```bash
npm run test --workspace=packages/core
npm run build --workspace=packages/ui
```

---

## Quality Configuration

npm projects typically configure quality via package.json scripts:

```json
{
  "scripts": {
    "lint": "eslint src/",
    "typecheck": "tsc --noEmit",
    "test": "jest",
    "test:ci": "jest --ci --coverage",
    "verify": "npm run lint && npm run typecheck && npm run test"
  }
}
```

---

## CI/CD Standards

```bash
export CI=true
export NODE_ENV=test
```

npm runs non-interactively when `CI=true` is set.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ERESOLVE dependency conflicts | Check peer dependency versions in package.json |
| E404 package not found | Verify package name and registry configuration |
| Build timeout | Increase `--timeout` or check for hanging processes |
| Workspace not found | Verify `workspaces` field in root package.json |
| TypeScript compilation slow | Use `--incremental` or project references |

### Diagnostic Commands

```bash
npm --version
npm ls
npm ls --all
npm outdated
npm audit
npx tsc --version
```

See SKILL.md for coverage report paths. See `build-api-reference.md` for shared build documentation.

**Notation**: `plan-marshall:build-npm:npm`
