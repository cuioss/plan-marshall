# cui-javascript-unit-testing

Jest unit testing standards for CUI JavaScript projects.

## Description

This skill provides comprehensive Jest unit testing standards covering configuration, test structure, component testing patterns, mocking strategies, and coverage requirements. It ensures consistent, high-quality unit testing across JavaScript projects with focus on 80% coverage thresholds, proper mocking, and test isolation.

## What's Included

- **Jest Configuration** - Complete Jest setup including jsdom environment, module mapping, transforms
- **Test Structure** - File organization, naming conventions, setup files, directory standards
- **Testing Patterns** - Component testing, mocking strategies, assertions, AAA pattern
- **Coverage Standards** - 80% thresholds, reporting formats, collection strategies

## Key Standards

### Jest Setup
- **Test Environment**: jsdom for DOM testing
- **Test Match**: `**/src/test/js/**/*.test.js`
- **Transform**: babel-jest for ES modules
- **Module Mapping**: Mocks for Lit, DevUI, directives

### Coverage Requirements
- **80% minimum** for all metrics (branches, functions, lines, statements)
- **Multiple formats**: text, lcov, html, cobertura
- **Coverage directory**: target/coverage
- **Collection strategies**: Different patterns for mocked vs actual source files

### Test Organization
- **components/** - Component tests
- **mocks/** - Framework and dependency mocks
- **setup/** - Global test configuration
- **utils/** - Test utilities

### Mocking
- Lit framework mock (html, css, LitElement)
- DevUI mock (jsonRPC, router)
- External dependencies
- Global browser APIs (ResizeObserver, matchMedia)

## Usage Examples

### When to Activate

Activate this skill when:
- Writing new Jest unit tests
- Configuring Jest for a project
- Implementing component tests
- Creating mocks for dependencies
- Analyzing test coverage
- Setting up test infrastructure

### Example Workflow

1. Setting up new project testing:
   - Reference jest-configuration.md for package.json setup
   - Follow test-structure.md for directory organization
   - Use testing-patterns.md for component test structure
   - Verify coverage-standards.md requirements

2. Writing component tests:
   - Consult testing-patterns.md for Lit component structure
   - Check mocking strategies for external dependencies
   - Apply AAA pattern from testing-patterns.md
   - Ensure coverage meets 80% threshold

3. Troubleshooting tests:
   - Review jest-configuration.md for config issues
   - Check test-structure.md for setup file patterns
   - Verify mocks in testing-patterns.md

## Quick Reference

### Jest Configuration
```json
{
  "jest": {
    "testEnvironment": "jest-environment-jsdom",
    "testMatch": ["**/src/test/js/**/*.test.js"],
    "coverageThreshold": {
      "global": {
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    }
  }
}
```

### Test Structure
```javascript
describe('ComponentName', () => {
  let element;

  beforeEach(async () => {
    // Arrange
    element = await fixture(html`<component-name></component-name>`);
  });

  it('should render with default properties', () => {
    // Act & Assert
    expect(element).to.exist;
    expect(element.shadowRoot).to.exist;
  });
});
```

### Coverage Reports
```bash
# Run tests with coverage
npm test -- --coverage

# View HTML report
open target/coverage/index.html
```

## Related Skills

- **cui-javascript** - Core JavaScript patterns and code quality
- **cui-css** - CSS development standards
- E2E testing standards (future skill)

## Standards Documents

- `jest-configuration.md` - Jest setup and configuration
- `test-structure.md` - Test file organization
- `testing-patterns.md` - Component testing and mocking
- `coverage-standards.md` - Coverage requirements and reporting
