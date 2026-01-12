# Jest Configuration

Complete Jest setup including environment configuration, module mapping, transforms, and integration with build systems.

## Overview

Jest is the primary testing framework for JavaScript projects in CUI. This guide covers all configuration aspects needed for testing modern JavaScript applications, including ES modules, web components, and DOM testing.

## Required Dependencies

Add these dev dependencies to package.json:

```json
{
  "devDependencies": {
    "jest": "^29.0.0",
    "jest-environment-jsdom": "^29.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@open-wc/testing": "^4.0.0",
    "babel-jest": "^29.0.0",
    "@babel/core": "^7.22.0",
    "@babel/preset-env": "^7.22.0"
  }
}
```

## Core Jest Configuration

### Complete Configuration

Add this Jest configuration to package.json:

```json
{
  "jest": {
    "testEnvironment": "jest-environment-jsdom",
    "testMatch": [
      "**/src/test/js/**/*.test.js"
    ],
    "moduleNameMapper": {
      "^lit$": "<rootDir>/src/test/js/mocks/lit.js",
      "^devui$": "<rootDir>/src/test/js/mocks/devui.js",
      "^lit/directives/unsafe-html.js$": "<rootDir>/src/test/js/mocks/lit-directives.js"
    },
    "transform": {
      "^.+\\.js$": "babel-jest"
    },
    "transformIgnorePatterns": [
      "node_modules/(?!(lit|@lit)/)"
    ],
    "setupFiles": [
      "<rootDir>/src/test/js/setup/jest.setup.js"
    ],
    "setupFilesAfterEnv": [
      "<rootDir>/src/test/js/setup/jest.setup-dom.js"
    ],
    "collectCoverageFrom": [
      "src/main/resources/dev-ui/**/*.js",
      "!src/main/resources/dev-ui/**/*.min.js"
    ],
    "coveragePathIgnorePatterns": [
      "node_modules",
      "src/test"
    ],
    "coverageThreshold": {
      "global": {
        // See coverage-standards.md for threshold values (80% for all metrics)
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    },
    "coverageReporters": [
      "text",
      "lcov",
      "html",
      "cobertura"
    ],
    "coverageDirectory": "target/coverage"
  }
}
```

### Configuration Breakdown

**testEnvironment**: `jest-environment-jsdom`
- Provides browser-like environment for DOM testing
- Required for testing web components and DOM manipulation
- Includes window, document, and other browser globals

**testMatch**: Pattern for finding test files
- `**/src/test/js/**/*.test.js` finds all test files in test directory
- Matches files ending with `.test.js`
- Recursive search through all subdirectories

**coverageDirectory**: `target/coverage`
- Aligns with Maven build structure
- Coverage reports stored with other build artifacts
- Easy to find and integrate with CI/CD

## Module Name Mapping

Map module imports to mocked implementations:

```json
{
  "moduleNameMapper": {
    "^lit$": "<rootDir>/src/test/js/mocks/lit.js",
    "^devui$": "<rootDir>/src/test/js/mocks/devui.js",
    "^lit/directives/unsafe-html.js$": "<rootDir>/src/test/js/mocks/lit-directives.js"
  }
}
```

### Why Module Mapping?

**Isolate dependencies**: Test components without full framework overhead

**Control behavior**: Mock implementations provide predictable test behavior

**Speed**: Mocked modules load faster than real implementations

**Simplicity**: Avoid complex framework initialization in tests

### Common Mappings

```json
{
  "moduleNameMapper": {
    // Lit framework
    "^lit$": "<rootDir>/src/test/js/mocks/lit.js",
    "^lit/decorators.js$": "<rootDir>/src/test/js/mocks/lit-decorators.js",
    "^lit/directives/(.*)$": "<rootDir>/src/test/js/mocks/lit-directives.js",

    // DevUI integration
    "^devui$": "<rootDir>/src/test/js/mocks/devui.js",

    // Style imports (if needed)
    "\\.(css|less|scss|sass)$": "<rootDir>/src/test/js/mocks/style-mock.js"
  }
}
```

## Transform Configuration

Configure Babel to transform ES modules for Jest:

```json
{
  "transform": {
    "^.+\\.js$": "babel-jest"
  },
  "transformIgnorePatterns": [
    "node_modules/(?!(lit|@lit)/)"
  ]
}
```

### Transform Patterns

**babel-jest**: Transforms ES modules to CommonJS for Jest

**transformIgnorePatterns**: Don't transform node_modules EXCEPT lit packages

### Babel Configuration

Create `.babelrc` or `babel.config.js`:

```javascript
// babel.config.js
module.exports = {
  presets: [
    ['@babel/preset-env', {
      targets: {
        node: 'current',
      },
    }],
  ],
};
```

### Why Transform Lit?

Lit uses ES modules that Jest can't handle natively. Transforming Lit packages allows Jest to process them correctly.

## Setup Files

Configure global test environment with setup files.

### setupFiles

Runs BEFORE test environment is set up. Use for:
- Global variables
- Node.js environment configuration
- Polyfills that don't need DOM

```json
{
  "setupFiles": [
    "<rootDir>/src/test/js/setup/jest.setup.js"
  ]
}
```

### setupFilesAfterEnv

Runs AFTER test environment is set up. Use for:
- DOM-specific configuration
- Testing library extensions
- Custom matchers

```json
{
  "setupFilesAfterEnv": [
    "<rootDir>/src/test/js/setup/jest.setup-dom.js"
  ]
}
```

## npm Scripts

Add these scripts to package.json:

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:verbose": "jest --verbose",
    "test:debug": "node --inspect-brk node_modules/.bin/jest --runInBand"
  }
}
```

### Script Usage

```bash
# Run all tests
npm test

# Watch mode for development
npm run test:watch

# Generate coverage report
npm run test:coverage

# Verbose output
npm run test:verbose

# Debug tests in Chrome DevTools
npm run test:debug
```

## Environment-Specific Configuration

### Development vs CI

Use environment variables to adjust configuration:

```javascript
// jest.config.js
const isCI = process.env.CI === 'true';

module.exports = {
  testEnvironment: 'jest-environment-jsdom',

  // CI: run all tests, local: watch mode
  watchAll: !isCI,

  // CI: generate all reports, local: text only
  coverageReporters: isCI
    ? ['text', 'lcov', 'html', 'cobertura']
    : ['text'],

  // CI: fail on coverage threshold, local: warn
  // See coverage-standards.md for threshold definitions and rationale
  coverageThreshold: {
    global: {
      branches: 80,  // See coverage-standards.md
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

## Integration with Maven

Configure frontend-maven-plugin to run Jest:

```xml
<execution>
  <id>npm-test</id>
  <goals>
    <goal>npm</goal>
  </goals>
  <phase>test</phase>
  <configuration>
    <arguments>test</arguments>
  </configuration>
</execution>
```

### Maven + Jest Integration

Tests run during Maven test phase automatically:

```bash
mvn test
```

Coverage reports appear in `target/coverage/` directory.

## Troubleshooting

### Common Issues

**Error: Cannot find module 'lit'**
- Check moduleNameMapper configuration
- Verify mock file exists at specified path
- Ensure path uses `<rootDir>` prefix

**Error: SyntaxError: Unexpected token 'export'**
- Add package to transformIgnorePatterns exception
- Verify babel-jest is configured
- Check .babelrc exists and is valid

**Tests timeout**
- Increase timeout: `jest.setTimeout(10000)` in setup
- Check for unresolved promises
- Verify async operations complete

**Coverage shows 0%**
- Check collectCoverageFrom patterns match source files
- Verify source files are not in coveragePathIgnorePatterns
- For mocked components, collect coverage from test files

## See Also

- [Test Structure](test-structure.md) - Test file organization
- [Testing Patterns](testing-patterns.md) - Component testing and mocking
- [Coverage Standards](coverage-standards.md) - Coverage requirements