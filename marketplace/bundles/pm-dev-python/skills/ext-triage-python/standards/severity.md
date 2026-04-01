# Python Severity Guidelines

Severity-to-action mapping for Python findings during triage.

## Ruff Findings

| Code Prefix | Category | Default Action |
|-------------|----------|----------------|
| E1xx-E5xx | PEP 8 style (pycodestyle) | Fix |
| E7xx | Statement errors | **Fix** (mandatory) |
| E9xx | Runtime errors | **Fix** (mandatory) |
| F | Pyflakes (unused imports, undefined names) | **Fix** (mandatory) |
| W | Warnings (whitespace, deprecated) | Fix or suppress with reason |
| C4 | Flake8-comprehensions | Fix (cleaner code) |
| C90 | McCabe complexity | Fix if over threshold, else accept |
| D | Pydocstyle (docstrings) | Fix for public API, accept for internals |
| I | Isort (import order) | Fix (auto-fixable) |
| N | PEP 8 naming | Fix for public API, accept for legacy |
| UP | Pyupgrade (modernization) | Fix (auto-fixable) |
| S | Bandit (security) | **Fix** for S1xx-S3xx, assess others |
| B | Bugbear (common bugs) | Fix |
| SIM | Simplify | Fix or accept based on readability |
| RUF | Ruff-specific | Fix |

## Mypy Findings

| Error Type | Default Action |
|------------|----------------|
| `error: Incompatible types` | **Fix** (type mismatch) |
| `error: Missing return statement` | **Fix** (logic error) |
| `error: Module has no attribute` | **Fix** (import error) |
| `error: Argument has incompatible type` | **Fix** (API misuse) |
| `note: Revealed type` | Informational, ignore |
| `error: Cannot find implementation` | Fix or stub |
| `error: Need type annotation` | Fix for public, suppress for dynamic patterns |

## Pytest Findings

| Finding Type | Default Action |
|--------------|----------------|
| Test failure (AssertionError) | **Fix** (broken behavior) |
| Test error (setup/teardown) | **Fix** (infrastructure issue) |
| Collection error | **Fix** (import or syntax error) |
| Slow test (>5s) | Investigate, optimize or mark as slow |
| Flaky test (intermittent) | **Fix** (non-determinism) |
| Coverage drop >2% | Fix (add missing tests) |
| Coverage drop <2% | Justify or fix |

## Decision Criteria

When deciding between fix and suppress:

1. **Is this a real bug or type safety issue?** Fix it.
2. **Is this auto-fixable by ruff?** Fix it (zero effort).
3. **Is this in generated or vendored code?** Suppress globally.
4. **Is this a style preference in legacy code?** Accept with migration plan.
5. **Is this a security finding (S-codes)?** Fix unless clearly false positive.
6. **Does fixing change behavior?** Verify with tests before fixing.
