# Coverage Standards

Test coverage thresholds, reporting formats, collection strategies, and quality gates for Jest testing.

## Overview

Code coverage measures how much of your code is executed during tests. This guide defines minimum coverage requirements, reporting standards, and strategies for collecting accurate coverage data.

## Minimum Coverage Thresholds

### Required Thresholds

All projects must meet these minimum coverage requirements:

- **Branches**: 80% minimum
- **Functions**: 80% minimum
- **Lines**: 80% minimum
- **Statements**: 80% minimum

### Jest Configuration

```json
{
  "jest": {
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

### Why 80%?

**Practical balance**:
- High enough to ensure quality
- Achievable without excessive effort
- Industry standard for enterprise software
- Leaves room for exceptional cases

**Not 100% because**:
- Some code is difficult to test (error handling)
- Diminishing returns above 80-90%
- Time better spent on test quality than coverage quantity

### Per-File Thresholds

Optionally enforce thresholds per file:

```json
{
  "coverageThreshold": {
    "global": {
      "branches": 80,
      "functions": 80,
      "lines": 80,
      "statements": 80
    },
    "./src/components/critical-component.js": {
      "branches": 95,
      "functions": 95,
      "lines": 95,
      "statements": 95
    }
  }
}
```

## Coverage Collection

### Source File Coverage

For testing actual source files:

```json
{
  "collectCoverageFrom": [
    "src/main/resources/dev-ui/**/*.js",
    "!src/main/resources/dev-ui/**/*.min.js",
    "!src/main/resources/dev-ui/**/*.bundle.js"
  ],
  "coveragePathIgnorePatterns": [
    "node_modules",
    "src/test",
    "/mocks/",
    "/setup/"
  ]
}
```

### Test File Coverage (When Using Mocks)

When components are fully mocked during testing, collect coverage from test files:

```json
{
  "collectCoverageFrom": [
    "src/test/js/**/*.js",
    "!src/test/js/**/*.test.js",
    "!src/test/js/mocks/**/*.js",
    "!src/test/js/setup/**/*.js"
  ]
}
```

**Why test file coverage?**
- Mocked components show 0% coverage
- Test files contain actual component logic when mocking
- Ensures tests themselves are well-covered

### Collection Patterns

**Include**:
- Source JavaScript files
- Component implementations
- Utility modules
- Business logic

**Exclude**:
- Test files (*.test.js)
- Mock implementations
- Setup/configuration files
- Third-party libraries
- Minified files
- Build artifacts

## Coverage Reporting

### Report Formats

Generate multiple formats for different audiences:

```json
{
  "coverageReporters": [
    "text",      // Console output for developers
    "lcov",      // SonarQube integration
    "html",      // Human-readable browser reports
    "cobertura"  // CI/CD integration (Jenkins, GitLab)
  ]
}
```

### Format Details

**text** - Console output:
```
----------|---------|----------|---------|---------|
File      | % Stmts | % Branch | % Funcs | % Lines |
----------|---------|----------|---------|---------|
component |   85.71 |    75.00 |   83.33 |   85.71 |
utils     |   91.67 |    87.50 |   90.00 |   91.67 |
----------|---------|----------|---------|---------|
All files |   88.24 |    81.25 |   86.67 |   88.24 |
----------|---------|----------|---------|---------|
```

**lcov** - Machine-readable for tools:
- SonarQube ingests lcov.info
- CI/CD systems parse for trends
- Code quality dashboards

**html** - Interactive browser report:
- Visual coverage by file
- Line-by-line coverage display
- Clickable to see uncovered lines
- Great for developers

**cobertura** - XML format:
- Jenkins integration
- GitLab merge request widgets
- CI/CD pipeline reports

### Coverage Directory

Store reports in Maven-compatible location:

```json
{
  "coverageDirectory": "target/coverage"
}
```

**Benefits**:
- Aligns with Maven build structure
- Easy to find with other artifacts
- Git-ignored by default
- CI/CD systems know where to look

## Running Coverage

### npm Scripts

```json
{
  "scripts": {
    "test": "jest",
    "test:coverage": "jest --coverage",
    "test:coverage:watch": "jest --coverage --watch",
    "test:ci": "jest --ci --coverage --watchAll=false"
  }
}
```

### Command Line

```bash
# Generate coverage report
npm run test:coverage

# Coverage with watch mode
npm run test:coverage:watch

# CI mode (no watch, with coverage)
npm run test:ci

# Coverage for specific file
npm test -- path/to/file.test.js --coverage

# Update snapshots with coverage
npm test -- --updateSnapshot --coverage
```

### View HTML Report

```bash
# Generate and open report
npm run test:coverage
open target/coverage/index.html

# Or on Linux
npm run test:coverage
xdg-open target/coverage/index.html
```

## Coverage Analysis

### Understanding Metrics

**Statements**: Individual executable statements
```javascript
const x = 5;        // Statement
console.log(x);     // Statement
```

**Branches**: Each branch of conditional logic
```javascript
if (condition) {    // Branch 1
  doThis();
} else {            // Branch 2
  doThat();
}
```

**Functions**: Function declarations and invocations
```javascript
function myFunc() { // Function
  // ...
}
myFunc();          // Invocation
```

**Lines**: Physical lines of code
```javascript
const result = calculate(  // Line 1
  param1,                  // Line 2
  param2                   // Line 3
);                         // Line 4
```

### Interpreting Results

**100%** - Every line/branch/function tested
- Ideal but not always practical
- May indicate over-testing

**80-95%** - Good coverage
- Acceptable for most code
- Some edge cases may be untested

**60-80%** - Moderate coverage
- Main paths covered
- Missing edge cases and error handling

**Below 60%** - Poor coverage
- Significant gaps in testing
- High risk of undetected bugs

### Finding Uncovered Code

View HTML report to see:
- Red/green highlighting per line
- Uncovered branches highlighted
- Functions never called
- Files with low coverage

## CI/CD Integration

### Maven Integration

Configure frontend-maven-plugin:

```xml
<execution>
  <id>npm-test</id>
  <goals>
    <goal>npm</goal>
  </goals>
  <phase>test</phase>
  <configuration>
    <arguments>run test:ci</arguments>
  </configuration>
</execution>
```

### SonarQube Integration

Configure coverage path in pom.xml:

```xml
<properties>
  <sonar.javascript.lcov.reportPaths>
    target/coverage/lcov.info
  </sonar.javascript.lcov.reportPaths>
  <sonar.coverage.exclusions>
    **/*.test.js,
    **/test/**/*,
    **/mocks/**/*,
    **/setup/**/*
  </sonar.coverage.exclusions>
</properties>
```

### GitHub Actions Example

```yaml
name: Test Coverage

on: [push, pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Run tests with coverage
        run: npm run test:coverage

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./target/coverage/lcov.info

      - name: Check coverage thresholds
        run: |
          if [ -f target/coverage/coverage-summary.json ]; then
            echo "Coverage report generated successfully"
          fi
```

## Improving Coverage

### Strategies

1. **Test happy paths first** - Main user flows
2. **Add edge case tests** - Boundary conditions
3. **Test error handling** - Exceptions, failures
4. **Cover all branches** - If/else, switch cases
5. **Test async operations** - Promises, callbacks
6. **Mock external dependencies** - APIs, databases

### Targeting Gaps

```bash
# Generate coverage report
npm run test:coverage

# Open HTML report
open target/coverage/index.html

# Find files with low coverage
# Look for red/yellow indicators
# Write tests for uncovered lines
```

### Coverage-Driven Testing

```javascript
// 1. Run coverage, see utils.js has low coverage
npm run test:coverage

// 2. Open HTML report, see validateEmail uncovered

// 3. Write test for uncovered function
it('should validate email addresses', () => {
  expect(validateEmail('test@example.com')).toBe(true);
  expect(validateEmail('invalid')).toBe(false);
  expect(validateEmail('')).toBe(false);
  expect(validateEmail(null)).toBe(false);
});

// 4. Run coverage again, verify improvement
```

## Quality Gates

### Enforcing Standards

**Local development**:
```bash
# Runs tests with coverage, fails if below threshold
npm run test:coverage
```

**CI/CD pipeline**:
```bash
# Strict mode with explicit thresholds
npm run test:ci-strict
```

**Pre-commit hook**:
```json
{
  "husky": {
    "hooks": {
      "pre-commit": "npm run test:coverage"
    }
  }
}
```

### Handling Failures

When coverage falls below threshold:

```
FAIL  Coverage for lines (78%) does not meet global threshold (80%)
FAIL  Coverage for functions (76%) does not meet global threshold (80%)
```

**Fix by**:
1. Adding tests for uncovered lines
2. Adding tests for uncovered functions
3. Removing dead code
4. Justifying exclusions

### Exclusions

Exclude code from coverage when justified:

```javascript
// istanbul ignore next
function debugHelper() {
  // Debug code not tested
}

// istanbul ignore else
if (condition) {
  // Main path tested
} else {
  // Defensive code, hard to test
}
```

**Use sparingly** - Only for:
- Debug/development code
- Defensive programming
- Platform-specific code
- Truly unreachable code

## Common Issues

### 0% Coverage

**Problem**: Coverage shows 0% despite tests passing

**Causes**:
- collectCoverageFrom patterns don't match source files
- Source files are in coveragePathIgnorePatterns
- Using mocks instead of real components

**Solution**:
```json
{
  "collectCoverageFrom": [
    "src/main/**/*.js",  // Check this matches your source
    "!src/main/**/*.test.js"
  ],
  "coveragePathIgnorePatterns": [
    "node_modules"  // Remove src/main if present
  ]
}
```

### Fluctuating Coverage

**Problem**: Coverage percentage changes unexpectedly

**Causes**:
- New code added without tests
- Tests removed or commented out
- collectCoverageFrom patterns changed

**Solution**:
- Monitor coverage in CI/CD
- Require tests with new code
- Set branch protection rules

### Slow Coverage Generation

**Problem**: Tests with coverage run much slower

**Solutions**:
- Reduce coverageReporters in development (text only)
- Use --coverage=false for quick iterations
- Run full coverage only in CI/CD

## See Also

- [Jest Configuration](jest-configuration.md) - Configure coverage collection
- [Test Structure](test-structure.md) - Organize tests for coverage
- [Testing Patterns](testing-patterns.md) - Write effective tests
