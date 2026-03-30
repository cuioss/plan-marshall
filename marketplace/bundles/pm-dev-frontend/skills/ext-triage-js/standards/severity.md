# JavaScript Severity Guidelines

Decision criteria for handling JavaScript findings based on severity, type, and context.

## ESLint Severity Mapping

| ESLint Level | Action | Notes |
|--------------|--------|-------|
| **error** | Fix (mandatory) | Blocks build/CI |
| **warn** | Fix preferred | Suppress with justification if legacy |
| **off** | N/A | Rule is disabled |

## Decision by Finding Type

### Security Issues

| Rule Category | Action | Notes |
|---------------|--------|-------|
| `no-eval`, `no-implied-eval` | **Fix immediately** | Security vulnerability |
| `no-new-Function` | **Fix immediately** | Code injection risk |
| XSS-related (jsx-a11y) | **Fix** | Security best practice |

### Code Quality

| Rule Category | Action | Context |
|---------------|--------|---------|
| `no-unused-vars` | Fix | Remove or use |
| `no-console` | Fix in production | Allow in development/debug |
| Complexity rules | Fix if > threshold | Refactor complex code |
| Naming conventions | Fix | Consistency matters |

### Formatting (Prettier/ESLint)

| Issue Type | Action | Notes |
|------------|--------|-------|
| Prettier violations | Auto-fix | Run `prettier --write` |
| ESLint auto-fixable | Auto-fix | Run `eslint --fix` |
| Style preferences | Accept or configure | Configure in `eslint.config.js` |

## Context Modifiers

### New Code vs Legacy Code

| Context | Guidance |
|---------|----------|
| **New JavaScript** | Full ESLint compliance, no suppressions |
| **Legacy JavaScript** | Fix errors, suppress warnings with justification |

### Test Code vs Production Code

| Context | Guidance |
|---------|----------|
| **Production code** | Standard rules, strict linting |
| **Test code** | More lenient for mocking, setup |
| **E2E tests** | Focus on functionality |

### Generated Code

| Situation | Action |
|-----------|--------|
| API clients (OpenAPI, GraphQL) | Exclude from linting |
| Build output (`dist/`) | Exclude entirely |
| Icon/asset imports | Configure specific rules |

## Acceptable to Accept

### Always Acceptable

| Finding Type | Reason |
|--------------|--------|
| Generated code (`**/generated/**`) | Regenerated, not maintained |
| Build output (`**/dist/**`) | Not source code |
| `node_modules/` | Third-party code |
| Vendored code | External responsibility |

### Conditionally Acceptable

| Finding Type | Condition |
|--------------|-----------|
| Legacy JS files | Tracked plan to address |
| Loose patterns in tests | Test mocks require flexibility |

### Never Acceptable

| Finding Type | Reason |
|--------------|--------|
| Security rules (eval, XSS) | Unacceptable risk |
| `error` level ESLint in CI | Blocks deployment |

## Framework-Specific Guidelines

### React

| Issue Type | Action |
|------------|--------|
| `react-hooks/exhaustive-deps` | Fix (usually) or document exception |
| Accessibility (jsx-a11y) | Fix for compliance |

### Node.js

| Issue Type | Action |
|------------|--------|
| Callback error handling | Fix - handle errors properly |
| Async/await patterns | Follow conventions |

## Quick Decision Flowchart

```
Is it ESLint error level?
  → Yes → FIX (blocks CI)

Is it a security rule?
  → Yes → FIX (no exceptions)

Is it auto-fixable?
  → Yes → RUN AUTO-FIX

Is it in generated code?
  → Yes → EXCLUDE from linting

Is it in test code?
  → Yes, mock-related → SUPPRESS with explanation
  → Yes, other → FIX

Is it low-effort fix?
  → Yes → FIX

Else → ACCEPT and document
```

## Iteration Limits

During finalize phase:

| Iteration | Focus |
|-----------|-------|
| 1 | Fix all errors, run auto-fix |
| 2 | Fix warnings |
| 3 | Review remaining, suppress with justification |
| MAX (5) | Accept remaining, document for future |

## Auto-Fix Commands

```bash
# Fix all auto-fixable ESLint issues
npx eslint --fix .

# Fix all Prettier issues
npx prettier --write .

# Fix both
npm run lint:fix  # If configured
```

## Related Standards

- [suppression.md](suppression.md) - How to suppress findings
- [pm-dev-frontend:javascript](../../javascript/SKILL.md) - JavaScript coding standards
