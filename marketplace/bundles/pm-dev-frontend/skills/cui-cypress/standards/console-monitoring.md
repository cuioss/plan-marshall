# Console Error Monitoring

Standards for monitoring and managing browser console output in Cypress E2E tests.

## Zero-Error Policy

**MANDATORY:** Cypress tests must actively monitor and validate browser console output to maintain application quality.

### Policy Requirements

**Tests Must:**
- Track all console errors and warnings
- Validate zero console errors at test completion
- Fail tests when unexpected errors occur
- Document and whitelist expected warnings

**Application Quality:**
- Console errors indicate real application problems
- Warnings may signal deprecated patterns or misuse
- Clean console output reflects code quality
- Proactive monitoring prevents production issues

## Console Monitoring Implementation

### Basic Error Tracking

Implement console monitoring in support file that runs before every test.

```javascript
// cypress/support/console-monitoring.js

/**
 * Initialize console error tracking before each window loads
 */
Cypress.on('window:before:load', (win) => {
  // Initialize error and warning arrays
  win.consoleErrors = [];
  win.consoleWarnings = [];

  // Store original console methods
  const originalError = win.console.error;
  const originalWarn = win.console.warn;

  // Override console.error to track errors
  win.console.error = (...args) => {
    // Call original method to preserve default behavior
    originalError.apply(win.console, args);

    // Track error message
    const errorMessage = args.join(' ');
    win.consoleErrors.push(errorMessage);
  };

  // Override console.warn to track warnings
  win.console.warn = (...args) => {
    // Call original method
    originalWarn.apply(win.console, args);

    // Track warning message
    const warningMessage = args.join(' ');
    win.consoleWarnings.push(warningMessage);
  };
});
```

### Import in Support File

```javascript
// cypress/support/e2e.js
import './console-monitoring';
import './commands';
```

## Allowed Warnings System

Implement centralized system for managing acceptable console warnings from third-party libraries.

### Allowed Warnings Configuration

```javascript
// cypress/support/console-monitoring.js

/**
 * Whitelist of acceptable console warnings from third-party libraries
 * Add warning patterns here with documentation explaining why they're allowed
 */
const allowedWarnings = [
  // Browser DevTools warnings (development only)
  'DevTools failed to load source map',

  // Legacy browser API deprecation warnings
  'Synchronous XMLHttpRequest on the main thread is deprecated',

  // Third-party library warnings (document library and version)
  'Some-library@1.2.3: Feature X is deprecated',

  // Known harmless warnings from dependencies
  '[SomeFramework] Non-critical configuration warning'
];

/**
 * Check if warning message matches allowed patterns
 * @param {string} message - Warning message to check
 * @returns {boolean} True if warning is allowed
 */
function isAllowedWarning(message) {
  return allowedWarnings.some(pattern => message.includes(pattern));
}
```

### Enhanced Monitoring with Filtering

```javascript
// cypress/support/console-monitoring.js

Cypress.on('window:before:load', (win) => {
  win.consoleErrors = [];
  win.consoleWarnings = [];
  win.unexpectedWarnings = [];

  const originalError = win.console.error;
  const originalWarn = win.console.warn;

  win.console.error = (...args) => {
    originalError.apply(win.console, args);
    const errorMessage = args.join(' ');
    win.consoleErrors.push(errorMessage);
  };

  win.console.warn = (...args) => {
    originalWarn.apply(win.console, args);
    const warningMessage = args.join(' ');

    // Track all warnings
    win.consoleWarnings.push(warningMessage);

    // Track unexpected warnings separately
    if (!isAllowedWarning(warningMessage)) {
      win.unexpectedWarnings.push(warningMessage);
    }
  };
});

/**
 * Allowed warning patterns
 */
const allowedWarnings = [
  'DevTools failed to load source map',
  'Synchronous XMLHttpRequest on the main thread is deprecated'
];

function isAllowedWarning(message) {
  return allowedWarnings.some(pattern => message.includes(pattern));
}
```

## Console Validation Commands

Create custom commands for console validation in tests.

### Validation Commands

```javascript
// cypress/support/commands.js

/**
 * Assert no console errors occurred during test
 * @param {Object} options - Validation options
 * @param {boolean} options.failOnWarnings - Also fail on unexpected warnings
 */
Cypress.Commands.add('assertNoConsoleErrors', (options = {}) => {
  const { failOnWarnings = false } = options;

  cy.window().then((win) => {
    // Check for console errors
    if (win.consoleErrors && win.consoleErrors.length > 0) {
      throw new Error(
        `Console errors detected:\n${win.consoleErrors.join('\n')}`
      );
    }

    // Optionally check for unexpected warnings
    if (failOnWarnings && win.unexpectedWarnings && win.unexpectedWarnings.length > 0) {
      throw new Error(
        `Unexpected console warnings detected:\n${win.unexpectedWarnings.join('\n')}`
      );
    }
  });
});

/**
 * Get current console errors and warnings
 * @returns {Cypress.Chainable<Object>} Console output object
 */
Cypress.Commands.add('getConsoleOutput', () => {
  return cy.window().then((win) => {
    return {
      errors: win.consoleErrors || [],
      warnings: win.consoleWarnings || [],
      unexpectedWarnings: win.unexpectedWarnings || []
    };
  });
});

/**
 * Clear console error and warning tracking
 */
Cypress.Commands.add('clearConsoleTracking', () => {
  cy.window().then((win) => {
    win.consoleErrors = [];
    win.consoleWarnings = [];
    win.unexpectedWarnings = [];
  });
});
```

## Usage Patterns

### Standard Test Pattern

```javascript
describe('Feature Tests', () => {
  it('R-FEAT-001: Should perform action without console errors', () => {
    // Arrange
    cy.navigateToPage('/feature', {
      expectedPageType: 'FEATURE_PAGE',
      waitForReady: true
    });

    // Act
    cy.get(TestConstants.SELECTORS.FEATURE.ACTION_BUTTON).click();

    // Assert functionality
    cy.get(TestConstants.SELECTORS.FEATURE.RESULT)
      .should('be.visible');

    // Assert no console errors
    cy.assertNoConsoleErrors();
  });
});
```

### Advanced Console Validation

```javascript
it('R-FEAT-002: Should load page with only expected warnings', () => {
  cy.navigateToPage('/complex-page', {
    expectedPageType: 'COMPLEX_PAGE',
    waitForReady: true
  });

  cy.getConsoleOutput().then((output) => {
    // Verify no errors
    expect(output.errors).to.have.length(0);

    // Verify no unexpected warnings
    expect(output.unexpectedWarnings).to.have.length(0);

    // Expected warnings are acceptable
    expect(output.warnings.length).to.be.greaterThan(0);
    output.warnings.forEach(warning => {
      cy.log(`Allowed warning: ${warning}`);
    });
  });
});
```

### Strict Validation Mode

```javascript
describe('Critical Path Tests', () => {
  it('R-CRIT-001: Should execute without any console output', () => {
    cy.navigateToPage('/critical-feature', {
      expectedPageType: 'CRITICAL_FEATURE',
      waitForReady: true
    });

    cy.get(TestConstants.SELECTORS.CRITICAL.ACTION).click();

    // Fail on both errors AND warnings
    cy.assertNoConsoleErrors({ failOnWarnings: true });

    // Additional verification
    cy.getConsoleOutput().then((output) => {
      expect(output.errors).to.have.length(0);
      expect(output.warnings).to.have.length(0);
    });
  });
});
```

## Allowed Warnings Management

### Adding New Allowed Warnings

When adding new allowed warnings, document rationale:

```javascript
const allowedWarnings = [
  // Browser DevTools - Development only, not present in production
  'DevTools failed to load source map',

  // Legacy API - Third-party library constraint
  // Library: old-library@2.1.0
  // Rationale: Migration planned for Q2 2024
  'Synchronous XMLHttpRequest on the main thread is deprecated',

  // Framework Warning - Known non-critical issue
  // Issue: https://github.com/framework/issues/1234
  // Rationale: Framework team confirmed harmless, fix in v3.0
  '[Framework] Configuration option X is deprecated',

  // Temporary Warning - To be removed when dependency-x upgraded to v5.0
  'dependency-x: Legacy mode enabled'
];
```

### Reviewing Allowed Warnings

**Regular Review Process:**
- Review allowed warnings quarterly
- Remove warnings after root cause fixed
- Update documentation with current status
- Track warnings to issues/tickets
- Verify warnings still occur in latest versions

### Conditional Allowed Warnings

For environment-specific warnings:

```javascript
/**
 * Get allowed warnings based on environment
 */
function getAllowedWarnings() {
  const baseWarnings = [
    'DevTools failed to load source map'
  ];

  const developmentWarnings = [
    '[HMR] Hot Module Replacement enabled'
  ];

  // Add development-only warnings in non-production
  if (Cypress.env('environment') !== 'production') {
    return [...baseWarnings, ...developmentWarnings];
  }

  return baseWarnings;
}

function isAllowedWarning(message) {
  const allowedWarnings = getAllowedWarnings();
  return allowedWarnings.some(pattern => message.includes(pattern));
}
```

## Global Console Validation

### Automatic Validation After Each Test

```javascript
// cypress/support/e2e.js

/**
 * Automatically validate console after each test
 */
afterEach(function() {
  // Skip validation if test already failed
  if (this.currentTest.state === 'failed') {
    return;
  }

  cy.window().then((win) => {
    if (win.consoleErrors && win.consoleErrors.length > 0) {
      const errorMessage = `Console errors detected:\n${win.consoleErrors.join('\n')}`;

      // Log errors for debugging
      cy.log('Console Errors:', win.consoleErrors);

      // Fail test
      throw new Error(errorMessage);
    }
  });
});
```

## Best Practices

### Documentation Standards

**Required Documentation:**
- Document all allowed warnings with rationale
- Link warnings to issues/tickets when applicable
- Note library versions for third-party warnings
- Include removal timeline for temporary warnings

**Example:**

```javascript
const allowedWarnings = [
  // Third-party: chart-library@2.1.0
  // Issue: JIRA-1234
  // Rationale: Library uses deprecated API, upgrade blocked by breaking changes
  // Timeline: Remove after upgrade to chart-library@3.0 (Q3 2024)
  'chart-library: Canvas API deprecated',
];
```

### Maintenance Guidelines

**Regular Maintenance:**
- Review console output in development regularly
- Update allowed warnings after dependency updates
- Remove warnings from whitelist once fixed
- Test console monitoring in CI/CD pipeline
- Verify monitoring works across browsers

**Warning Escalation:**
- Unexpected warnings should be investigated
- Recurring warnings indicate code quality issues
- New warnings from application code should be fixed
- Document decision if warning must be allowed

### Testing Console Monitoring

Test that console monitoring works correctly:

```javascript
// cypress/e2e/infrastructure/console-monitoring.cy.js

describe('Console Monitoring', () => {
  it('should detect console errors', () => {
    cy.visit('/test-page');

    // Trigger console error
    cy.window().then((win) => {
      win.console.error('Test error');
    });

    // Verify error was tracked
    cy.window().then((win) => {
      expect(win.consoleErrors).to.include('Test error');
    });
  });

  it('should allow whitelisted warnings', () => {
    cy.visit('/test-page');

    // Trigger allowed warning
    cy.window().then((win) => {
      win.console.warn('DevTools failed to load source map');
    });

    // Should be tracked but not cause failure
    cy.getConsoleOutput().then((output) => {
      expect(output.warnings.length).to.be.greaterThan(0);
      expect(output.unexpectedWarnings).to.have.length(0);
    });
  });
});
```

## Error Categories

### Application Errors (Must Fix)
- JavaScript runtime errors
- React/framework errors
- API call failures
- Resource loading failures

### Dependency Warnings (Document)
- Third-party library deprecation warnings
- Browser API deprecation warnings
- Development-only warnings

### False Positives (Whitelist)
- Browser extension warnings
- DevTools warnings
- Known harmless library warnings

## Integration with CI/CD

Ensure console monitoring runs in continuous integration:

```javascript
// cypress.config.js
export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      // Configure console monitoring for CI
      on('task', {
        logConsoleErrors(errors) {
          console.error('Console errors detected in CI:', errors);
          return null;
        }
      });
    }
  }
});
```

## Summary

**Key Requirements:**
- Implement console monitoring for all tests
- Maintain zero-error policy
- Document all allowed warnings
- Review and update whitelist regularly
- Validate console output in every test
- Fail tests on unexpected console output
