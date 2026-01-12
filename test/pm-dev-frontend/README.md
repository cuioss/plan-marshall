# pm-dev-frontend Tests

Tests for pm-dev-frontend bundle (JavaScript/npm development).

## Structure

```
test/pm-dev-frontend/
├── build/                     # Build analysis test data
├── build-operations/          # npm build execution tests
├── coverage/                  # Coverage report test data
├── integration/               # Integration tests with real projects
├── jsdoc/                     # JSDoc validation test data
├── plan-marshall-plugin/      # Extension and discovery tests
├── test_js_coverage.py        # Coverage analysis tests
├── test_jsdoc.py              # JSDoc validation tests
└── test_npm_output.py         # npm output parsing tests
```

## Running Tests

```bash
python3 test/run-tests.py test/pm-dev-frontend/
```
