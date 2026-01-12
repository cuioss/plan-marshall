# Cypress Framework Configuration

Framework-specific configuration and adaptations for Cypress E2E testing within CUI projects.

## ESLint Configuration for Cypress

Cypress tests require adapted ESLint rules to accommodate the unique patterns and complexity of E2E testing scenarios.

### Complete Configuration Example

```javascript
// eslint.config.js - Cypress-specific configuration
import cypress from 'eslint-plugin-cypress';
import jsdoc from 'eslint-plugin-jsdoc';
import sonarjs from 'eslint-plugin-sonarjs';
import security from 'eslint-plugin-security';
import unicorn from 'eslint-plugin-unicorn';
import globals from 'globals';

export default [
  {
    files: ["cypress/**/*.js"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        cy: "readonly",
        Cypress: "readonly"
      }
    },
    plugins: {
      cypress,
      jsdoc,
      sonarjs,
      security,
      unicorn
    },
    rules: {
      // Cypress-specific rules
      "cypress/no-unnecessary-waiting": "warn",
      "cypress/unsafe-to-chain-command": "off",
      "cypress/no-assigning-return-values": "error",

      // Adapted complexity rules (see below)
      "max-lines-per-function": ["error", {
        "max": 200,
        "skipBlankLines": true,
        "skipComments": true
      }],
      "complexity": ["error", { "max": 25 }],

      // JSDoc requirements
      "jsdoc/require-description": "error",
      "jsdoc/require-param-description": "error",
      "jsdoc/require-returns-description": "error"
    }
  }
];
```

### Key Configuration Elements

**Global Variables:**
- `cy` - Cypress command object
- `Cypress` - Cypress utility object
- Standard browser and Node.js globals

**Required Plugins:**
- `eslint-plugin-cypress` - Cypress-specific linting rules
- `eslint-plugin-jsdoc` - Documentation enforcement
- `eslint-plugin-sonarjs` - Code quality checks
- `eslint-plugin-security` - Security vulnerability detection
- `eslint-plugin-unicorn` - Additional code quality rules

## Complexity Adaptations

E2E tests involve complex user interaction flows that naturally result in longer functions and higher cyclomatic complexity compared to unit tests or application code.

### Function Length Limits

**Standard JavaScript:** 50 lines maximum
**Cypress E2E Tests:** 200 lines maximum

```javascript
"max-lines-per-function": ["error", {
  "max": 200,           // Increased from 50 for test scenarios
  "skipBlankLines": true,
  "skipComments": true
}]
```

**Rationale:**
- E2E tests model complete user journeys
- Multiple page interactions in single test flow
- Setup and teardown operations are integrated
- Explicit assertion chains are verbose but necessary

### Cyclomatic Complexity

**Standard JavaScript:** 10 maximum
**Cypress E2E Tests:** 25 maximum

```javascript
"complexity": ["error", {
  "max": 25  // Increased from 10 for complex test scenarios
}]
```

**Rationale:**
- E2E tests validate multiple conditional branches
- User flows contain decision points
- Error state handling requires branching
- Form validation scenarios involve multiple paths

**Important:** While complexity thresholds are raised, tests must still avoid branching logic within test assertions (see testing-patterns.md).

## Plugin Rules Configuration

### Cypress Plugin Rules

**Enabled Rules:**
- `cypress/no-unnecessary-waiting` (warn) - Detects unnecessary `cy.wait()` calls
- `cypress/no-assigning-return-values` (error) - Prevents incorrect return value usage

**Disabled Rules:**
- `cypress/unsafe-to-chain-command` - Allows certain command chaining patterns

### Security and Quality Plugins

**SonarJS Rules:**
Apply cognitive complexity limits appropriate for test scenarios while maintaining code clarity.

**Security Plugin:**
Detect security vulnerabilities even in test code (e.g., hardcoded credentials, insecure random values).

**Unicorn Plugin:**
Enforce modern JavaScript patterns and conventions.

## JSDoc Requirements

All custom commands and helper functions must include comprehensive JSDoc documentation.

**Required Tags:**
- `@param` with type and description for all parameters
- `@returns` with type and description for return values
- Description of command purpose and behavior

**Example:**

For complete login command implementation with modern `cy.session()` caching and validation, see [testing-patterns.md](testing-patterns.md#use-cysession).

## Dependencies

### Required Packages

```json
{
  "devDependencies": {
    "cypress": "^13.0.0",
    "eslint": "^8.0.0",
    "eslint-plugin-cypress": "^3.0.0",
    "eslint-plugin-jsdoc": "^48.0.0",
    "eslint-plugin-sonarjs": "^0.23.0",
    "eslint-plugin-security": "^2.1.0",
    "eslint-plugin-unicorn": "^51.0.0"
  }
}
```

### Version Considerations

**Cypress:**
- Use latest stable version (13.x or higher)
- Monitor breaking changes in major version updates
- Test compatibility with CI/CD environments

**ESLint Plugins:**
- Keep plugins updated for latest rule improvements
- Review changelogs for deprecated rules
- Validate plugin compatibility with ESLint version

## Global Configuration

### Cypress Configuration File

```javascript
// cypress.config.js
import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:8080',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    supportFile: 'cypress/support/e2e.js',
    video: true,
    screenshotOnRunFailure: true,
    viewportWidth: 1280,
    viewportHeight: 720,
    defaultCommandTimeout: 10000,
    pageLoadTimeout: 30000,
    requestTimeout: 15000,
    responseTimeout: 15000
  }
});
```

### Environment Variables

Store environment-specific configuration:

```javascript
// cypress.env.json (gitignored)
{
  "apiUrl": "http://localhost:8080/api",
  "username": "testuser",
  "password": "testpassword"
}
```

**Security Note:** Never commit credentials to version control. Use CI/CD environment variables for sensitive values.

## Best Practices

**Configuration Organization:**
- Separate Cypress rules from application code rules
- Use file pattern matching for targeted configuration
- Document deviations from standard rules

**Maintenance:**
- Review and update plugin versions regularly
- Validate rule effectiveness during code reviews
- Adjust complexity thresholds if consistently hit limits

**Team Alignment:**
- Ensure all team members use same ESLint configuration
- Document rationale for adapted thresholds
- Share ESLint configuration via version control
