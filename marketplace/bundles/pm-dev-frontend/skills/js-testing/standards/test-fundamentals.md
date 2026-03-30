# JavaScript Test Fundamentals

## Framework Selection

| Choose | When |
|--------|------|
| **Jest** | React Native (mandatory), legacy Webpack/Babel projects, CommonJS-heavy codebases, established Jest infrastructure |
| **Vitest** | Vite-based projects, new projects, TypeScript-first codebases, native ESM needed |

Vitest's API is 95% Jest-compatible. Migration is straightforward -- mainly config changes, not test rewrites.

## Project Setup

### Jest Configuration (package.json)

```json
{
  "jest": {
    "testEnvironment": "jest-environment-jsdom",
    "testMatch": ["**/src/test/js/**/*.test.js"],
    "resetMocks": true,
    "clearMocks": true,
    "restoreMocks": true,
    "coverageDirectory": "target/coverage",
    "coverageReporters": ["text", "html", "lcov"],
    "coverageThreshold": {
      "global": {
        "branches": 75,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    },
    "setupFiles": ["<rootDir>/src/test/js/jest.setup.js"],
    "setupFilesAfterEnv": ["<rootDir>/src/test/js/jest.setup-dom.js"]
  }
}
```

### Vitest Configuration (vitest.config.js)

```javascript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/test/js/**/*.test.js'],
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: 'target/coverage',
      thresholds: {
        branches: 75,
        functions: 80,
        lines: 80,
        statements: 80,
      },
    },
  },
});
```

### Setup Files

**Global setup** (runs before test framework loads):

```javascript
// jest.setup.js / vitest.setup.js
// Provide fetch mock (jsdom does not include fetch)
globalThis.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
  })
);
```

**DOM setup** (runs after framework, has access to matchers):

```javascript
// jest.setup-dom.js / vitest.setup-dom.js
import '@testing-library/jest-dom';

// Optional: global helper to wait for async component updates
globalThis.waitForComponentUpdate = async (component) => {
  if (component.updateComplete) {
    await component.updateComplete;
  }
  await new Promise((resolve) => setTimeout(resolve, 0));
};
```

## Test File Organization

### Location and Naming

Place tests in `src/test/js/` mirroring source structure:

```
src/
├── main/webapp/js/
│   ├── api.js
│   ├── utils.js
│   └── components/
│       └── token-verifier.js
└── test/js/
    ├── jest.setup.js
    ├── jest.setup-dom.js
    ├── mocks/              # Shared mock modules
    │   └── external-lib.js
    ├── test-helpers.js     # Shared test utilities
    ├── api.test.js
    ├── utils.test.js
    └── components/
        └── token-verifier.test.js
```

### Naming Convention

- Test files: `{module-name}.test.js`
- Mock files: `mocks/{module-name}.js`
- Helper files: `test-helpers.js` or `helpers/{concern}.js`

## Test Structure

### AAA Pattern (Arrange-Act-Assert)

Every test follows three phases, separated by blank lines for readability:

```javascript
test('formats currency with two decimal places', () => {
  // Arrange
  const amount = 1234.5;

  // Act
  const result = formatCurrency(amount, 'USD');

  // Assert
  expect(result).toBe('$1,234.50');
});
```

### Describe Blocks

Group related tests with `describe`. Use nested blocks for sub-behaviors:

```javascript
describe('validateUrl', () => {
  test('accepts valid HTTPS URLs', () => {
    expect(validateUrl('https://example.com')).toBe(true);
  });

  test('rejects URLs without protocol', () => {
    expect(validateUrl('example.com')).toBe(false);
  });

  describe('edge cases', () => {
    test('rejects empty string', () => {
      expect(validateUrl('')).toBe(false);
    });

    test('rejects null', () => {
      expect(validateUrl(null)).toBe(false);
    });
  });
});
```

### Naming Conventions

Test names should read as behavior descriptions. The reader should understand the test without reading the body:

```javascript
// Good -- describes behavior and expected outcome
test('returns 404 when user not found', async () => { ... });
test('disables submit button while form is validating', () => { ... });

// Bad -- vague, describes implementation
test('test1', () => { ... });
test('works', () => { ... });
test('calls the API', () => { ... });
```

### Single Responsibility

Each test verifies one behavior. Multiple `expect` calls are fine when they assert the same logical concept:

```javascript
// Good -- one logical assertion (form renders correctly)
test('renders login form with required fields', () => {
  init(container);
  expect(container.querySelector('#username')).not.toBeNull();
  expect(container.querySelector('#password')).not.toBeNull();
  expect(container.querySelector('[type="submit"]')).not.toBeNull();
});

// Bad -- tests two unrelated behaviors
test('renders form and validates input', () => {
  init(container);
  expect(container.querySelector('#username')).not.toBeNull();
  fireEvent.change(input, { target: { value: '' } });
  expect(container.querySelector('.error')).not.toBeNull(); // separate test
});
```

## Parameterized Tests

Use `test.each` for input/output variations. Keep it for straightforward mappings -- prefer individual tests for complex scenarios:

```javascript
test.each([
  ['hello@example.com', true],
  ['not-an-email', false],
  ['', false],
  ['user@domain.co.uk', true],
])('validateEmail(%s) returns %s', (input, expected) => {
  expect(validateEmail(input)).toBe(expected);
});
```

## Coverage

### Thresholds

Enforce minimum coverage at build time to prevent regressions. Reasonable defaults:

| Metric | Threshold |
|--------|-----------|
| Lines | 80% |
| Statements | 80% |
| Functions | 80% |
| Branches | 75% |

Coverage is guidance, not a goal. Focus on critical business logic rather than chasing 100%. A well-tested 80% codebase is more valuable than a superficially-tested 100% one.

### Coverage Reports

- **Text**: Console output during CI
- **HTML**: Visual analysis during development
- **LCOV**: Integration with SonarQube/Codecov
- **Cobertura**: CI dashboard integration

### What to Exclude

```json
"coveragePathIgnorePatterns": [
  "node_modules",
  "src/test/",
  "dist/",
  "generated/"
]
```

## NPM Scripts

```json
{
  "scripts": {
    "test": "NODE_ENV=test jest",
    "test:watch": "NODE_ENV=test jest --watch",
    "test:coverage": "NODE_ENV=test jest --coverage",
    "test:ci": "NODE_ENV=test jest --watchAll=false --passWithNoTests --coverage"
  }
}
```

## ESLint Integration

Use `eslint-plugin-jest` or `eslint-plugin-vitest` for test-specific rules:

```javascript
// In eslint.config.js -- test file overrides
{
  files: ['src/test/js/**/*.test.js'],
  plugins: { jest: jestPlugin },
  rules: {
    'jest/expect-expect': 'error',
    'jest/no-disabled-tests': 'warn',
    'jest/no-focused-tests': 'error',
    'jest/no-identical-title': 'error',
    'jest/valid-expect': 'error',
    'no-console': 'off',
    'max-len': 'off',
  },
}
```

Key rules:
- `no-focused-tests`: Prevents committed `.only()` calls
- `expect-expect`: Ensures every test has assertions
- `no-identical-title`: Unique test names within describe blocks

For Vitest projects, use `eslint-plugin-vitest` with equivalent rules.

## See Also

- [DOM and Component Testing](dom-component-testing.md) - DOM manipulation, web components, Testing Library
- [Mocking and Async Patterns](mocking-async.md) - Module mocking, fetch mocks, timers, test isolation
- `pm-dev-frontend:js-enforce-eslint` - ESLint test file overrides
