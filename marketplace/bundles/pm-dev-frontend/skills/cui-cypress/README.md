# Cypress E2E Testing Standards

Comprehensive standards for Cypress End-to-End testing in CUI projects, providing framework-specific adaptations and best practices for reliable browser-based test automation.

## Standards Included

### Framework Configuration
**cypress-configuration.md**
- ESLint configuration adapted for Cypress
- Adjusted complexity thresholds for E2E scenarios
- Plugin setup and global configuration
- Framework-specific rule adaptations

### Test Organization
**test-organization.md**
- Directory structure and file naming conventions
- Custom command patterns and reusable utilities
- DSL-style constants for selectors and test data
- Test file structure and organization principles

### Testing Patterns
**testing-patterns.md**
- Core testing principles (no branching logic, explicit assertions)
- Session management and test isolation strategies
- Navigation patterns and page type verification
- Error handling and timeout configuration
- Modern Cypress patterns and anti-patterns

### Console Monitoring
**console-monitoring.md**
- Zero-error policy enforcement
- Allowed warnings system for third-party libraries
- Console error tracking implementation
- Integration with test lifecycle

### Build Integration
**build-integration.md**
- NPM scripts for Cypress execution
- Maven integration patterns
- CI/CD pipeline configuration
- Dependency management and versioning

## Quick Start

1. **Activate the skill:**
   ```
   Skill: cui-cypress
   ```

2. **Review configuration standards:**
   - Start with `cypress-configuration.md` for ESLint setup
   - Apply framework-specific adaptations

3. **Organize tests:**
   - Follow `test-organization.md` structure
   - Create custom commands for reusable logic
   - Define constants using DSL pattern

4. **Apply best practices:**
   - Enforce no-branching-logic rule
   - Implement console monitoring
   - Use session management helpers
   - Follow navigation patterns

## Key Principles

### Mandatory Requirements
- **No branching logic in tests** - Use explicit assertions only
- **Navigation helpers** - Never use direct `cy.visit()` or URL checks
- **Session verification** - Always verify context after authentication
- **Console monitoring** - Detect and validate all console output

### Prohibited Patterns
- Fixed timeout waits (`cy.wait(1000)`)
- Element existence checks in test logic
- Manual session manipulation
- Direct URL inspection or manipulation

## Integration

This skill extends:
- JavaScript development standards
- ESLint configuration standards
- Unit testing patterns
- Project structure standards

## Usage Examples

### Creating a New Test
```javascript
// e2e/auth/login-flow.cy.js
import { TestConstants } from '../../support/constants/test-constants';

describe('Authentication Flow', () => {
  beforeEach(() => {
    cy.clearSession();
  });

  it('R-AUTH-001: Should successfully authenticate valid user', () => {
    cy.navigateToPage('/login', {
      expectedPageType: 'LOGIN',
      waitForReady: true
    });

    cy.login('validUser', 'validPassword');

    cy.getSessionContext().then((context) => {
      expect(context.isLoggedIn).to.be.true;
      expect(context.pageType).to.equal('MAIN_CANVAS');
    });
  });
});
```

### Defining Custom Commands
```javascript
// support/commands.js
/**
 * Navigate to a page and verify page type
 * @param {string} path - URL path to navigate to
 * @param {Object} options - Navigation options
 * @param {string} options.expectedPageType - Expected page type after navigation
 * @param {boolean} options.waitForReady - Whether to wait for page ready state
 */
Cypress.Commands.add('navigateToPage', (path, options = {}) => {
  const { expectedPageType, waitForReady = true } = options;

  cy.visit(path);

  if (waitForReady) {
    cy.waitForPageReady();
  }

  if (expectedPageType) {
    cy.verifyPageType(expectedPageType);
  }
});
```

## Related Documentation

- [Cypress Official Documentation](https://docs.cypress.io/)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
- CUI JavaScript Development Standards
- CUI ESLint Configuration Standards
