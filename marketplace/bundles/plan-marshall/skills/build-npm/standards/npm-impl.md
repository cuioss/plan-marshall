# npm Implementation Standards

npm-specific standards for build execution and output parsing. For shared standards (timeouts, warnings, log files), see `extension-api/standards/build-systems-common.md`. For npm/npx detection rules and multi-parser architecture, see SKILL.md and `build-api-reference.md`.

---

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `npm` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

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
