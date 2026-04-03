# npm Implementation Standards

npm-specific standards for build execution and output parsing. For shared standards (timeouts, warnings, log files), see `extension-api/standards/build-systems-common.md`. For npm/npx detection rules and multi-parser architecture, see SKILL.md and `build-api-reference.md`.

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
