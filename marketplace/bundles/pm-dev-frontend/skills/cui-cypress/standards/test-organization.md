# Test Organization and Structure

Standards for organizing Cypress test files, directories, and reusable test components.

## Directory Structure

Organize Cypress tests in a clear, logical hierarchy that mirrors application structure and test types.

### Standard Layout

```
cypress/
├── e2e/                    # E2E test specifications
│   ├── auth/               # Authentication tests
│   │   ├── login-flow.cy.js
│   │   ├── logout-flow.cy.js
│   │   └── password-reset.cy.js
│   ├── dashboard/          # Dashboard feature tests
│   │   ├── user-management.cy.js
│   │   └── data-visualization.cy.js
│   └── admin/              # Admin functionality tests
│       ├── system-configuration.cy.js
│       └── user-permissions.cy.js
├── support/                # Support files and utilities
│   ├── e2e.js              # Global configuration and imports
│   ├── commands.js         # Custom commands
│   ├── console-monitoring.js  # Console error tracking
│   └── constants/          # Test constants
│       └── test-constants.js
├── fixtures/               # Test data files
│   ├── users.json
│   └── test-data.json
└── plugins/                # Cypress plugins (if needed)
```

### Organization Principles

**Feature-Based Structure:**
- Group tests by application feature or module
- Mirror application architecture when logical
- Keep related tests together

**Separation of Concerns:**
- Test specifications in `e2e/`
- Reusable utilities in `support/`
- Static test data in `fixtures/`
- Configuration in `plugins/`

## File Naming Conventions

### Test Files

**Pattern:** `{feature-area}/{descriptive-name}.cy.js`

**Examples:**
- `auth/login-flow.cy.js` - User authentication flow
- `dashboard/user-management.cy.js` - User management features
- `admin/system-configuration.cy.js` - System configuration screens

**Guidelines:**
- Use kebab-case for file names
- Include `.cy.` before extension to identify test files
- Choose descriptive names reflecting test purpose
- Group related tests in subdirectories

### Support Files

**Pattern:** `{purpose}.js` or `{category}/{purpose}.js`

**Examples:**
- `commands.js` - Custom Cypress commands
- `console-monitoring.js` - Console error monitoring
- `constants/test-constants.js` - Test constants
- `helpers/authentication.js` - Authentication helpers

## Constants Organization

Organize test constants using DSL-style patterns for maintainability and reusability.

### Centralized Test Constants

```javascript
// cypress/support/constants/test-constants.js

/**
 * Centralized test constants following DSL-style pattern
 */
export const TestConstants = {
  /**
   * Test data selectors organized by feature area
   */
  SELECTORS: {
    LOGIN: {
      USERNAME_INPUT: '[data-testid="username-input"]',
      PASSWORD_INPUT: '[data-testid="password-input"]',
      SUBMIT_BUTTON: '[data-testid="login-submit"]',
      ERROR_MESSAGE: '[data-testid="login-error"]'
    },
    NAVIGATION: {
      MENU_TOGGLE: '[data-testid="menu-toggle"]',
      USER_MENU: '[data-testid="user-menu"]',
      LOGOUT_BUTTON: '[data-testid="logout-button"]'
    },
    DASHBOARD: {
      USER_TABLE: '[data-testid="user-table"]',
      ADD_USER_BUTTON: '[data-testid="add-user"]',
      SEARCH_INPUT: '[data-testid="user-search"]'
    }
  },

  /**
   * Timeout values for different operation types
   */
  TIMEOUTS: {
    DEFAULT: 10000,
    API_CALL: 30000,
    PAGE_LOAD: 15000,
    AUTHENTICATION: 45000,
    ELEMENT_INTERACTION: 15000
  },

  /**
   * Test data values
   */
  TEST_DATA: {
    VALID_USER: {
      username: 'validuser',
      password: 'ValidPassword123!'
    },
    INVALID_USER: {
      username: 'invaliduser',
      password: 'WrongPassword'
    }
  },

  /**
   * API endpoints for testing
   */
  API: {
    LOGIN: '/api/auth/login',
    LOGOUT: '/api/auth/logout',
    USERS: '/api/users'
  },

  /**
   * Page types for navigation verification
   */
  PAGE_TYPES: {
    LOGIN: 'LOGIN',
    MAIN_CANVAS: 'MAIN_CANVAS',
    DASHBOARD: 'DASHBOARD',
    ADMIN: 'ADMIN'
  }
};
```

### Constants Usage

```javascript
// e2e/auth/login-flow.cy.js
import { TestConstants } from '../../support/constants/test-constants';

describe('Login Flow', () => {
  it('should authenticate valid user', () => {
    cy.get(TestConstants.SELECTORS.LOGIN.USERNAME_INPUT)
      .type(TestConstants.TEST_DATA.VALID_USER.username);

    cy.get(TestConstants.SELECTORS.LOGIN.PASSWORD_INPUT)
      .type(TestConstants.TEST_DATA.VALID_USER.password);

    cy.get(TestConstants.SELECTORS.LOGIN.SUBMIT_BUTTON).click();
  });
});
```

### Constants Organization Principles

**Hierarchical Structure:**
- Group constants by feature area
- Use nested objects for related values
- Maintain clear naming hierarchy

**Naming Conventions:**
- UPPER_CASE for constant names
- PascalCase for nested object groups
- Descriptive names reflecting purpose

**Maintainability:**
- Single source of truth for selectors
- Easy to update across all tests
- Type-safe with JSDoc annotations

## Custom Commands

Define reusable Cypress commands for common operations.

### Command Definition Structure

```javascript
// cypress/support/commands.js

// For complete login command implementation with modern cy.session() caching,
// see testing-patterns.md "Use cy.session()" section

/**
 * Clear current session and ensure clean state
 * @returns {Cypress.Chainable} Cypress command chain
 */
Cypress.Commands.add('clearSession', () => {
  cy.clearCookies();
  cy.clearLocalStorage();
  cy.window().then((win) => {
    win.sessionStorage.clear();
  });
});

/**
 * Navigate to page with verification
 * @param {string} path - URL path to navigate to
 * @param {Object} options - Navigation options
 * @param {string} options.expectedPageType - Expected page type after navigation
 * @param {boolean} options.waitForReady - Whether to wait for page ready state
 * @param {number} options.timeout - Custom timeout in milliseconds
 * @returns {Cypress.Chainable} Cypress command chain
 */
Cypress.Commands.add('navigateToPage', (path, options = {}) => {
  const {
    expectedPageType,
    waitForReady = true,
    timeout = TestConstants.TIMEOUTS.PAGE_LOAD
  } = options;

  cy.visit(path, { timeout });

  if (waitForReady) {
    cy.waitForPageReady({ timeout });
  }

  if (expectedPageType) {
    cy.verifyPageType(expectedPageType);
  }
});

/**
 * Wait for page to reach ready state
 * @param {Object} options - Wait options
 * @param {number} options.timeout - Custom timeout
 * @returns {Cypress.Chainable} Cypress command chain
 */
Cypress.Commands.add('waitForPageReady', (options = {}) => {
  const { timeout = TestConstants.TIMEOUTS.PAGE_LOAD } = options;

  cy.window({ timeout }).should((win) => {
    expect(win.document.readyState).to.equal('complete');
  });
});

/**
 * Verify current page type matches expected
 * @param {string} expectedType - Expected page type constant
 * @returns {Cypress.Chainable} Cypress command chain
 */
Cypress.Commands.add('verifyPageType', (expectedType) => {
  cy.getPageContext({ timeout: TestConstants.TIMEOUTS.PAGE_LOAD })
    .then((context) => {
      expect(context.pageType).to.equal(expectedType);
    });
});

/**
 * Get current page context including type and state
 * @param {Object} options - Options
 * @param {number} options.timeout - Custom timeout
 * @returns {Object} Page context
 */
Cypress.Commands.add('getPageContext', (options = {}) => {
  const { timeout = TestConstants.TIMEOUTS.DEFAULT } = options;

  return cy.window({ timeout }).then((win) => {
    return win.pageContext || {
      pageType: 'UNKNOWN',
      isReady: false
    };
  });
});

/**
 * Get current session context
 * @returns {Object} Session context with authentication state
 */
Cypress.Commands.add('getSessionContext', () => {
  return cy.window().then((win) => {
    return win.sessionContext || {
      isLoggedIn: false,
      pageType: 'UNKNOWN',
      user: null
    };
  });
});

/**
 * Retrieve and restore session from storage
 * Restores authentication state and session data from localStorage/sessionStorage
 * @param {string} sessionId - Session identifier to retrieve
 * @returns {Cypress.Chainable} Cypress command chain
 */
Cypress.Commands.add('retrieveSession', (sessionId) => {
  cy.window().then((win) => {
    const sessionData = win.localStorage.getItem(`session_${sessionId}`);
    if (sessionData) {
      const session = JSON.parse(sessionData);
      win.sessionContext = session;
      return session;
    }
    throw new Error(`Session ${sessionId} not found`);
  });
});

/**
 * Logout current user and clear session
 * Clears authentication state, session data, and returns to login page
 * @returns {Cypress.Chainable} Cypress command chain
 */
Cypress.Commands.add('logout', () => {
  cy.window().then((win) => {
    win.sessionContext = {
      isLoggedIn: false,
      pageType: 'UNKNOWN',
      user: null
    };
    win.localStorage.clear();
    win.sessionStorage.clear();
  });
  cy.visit('/login');
});
```

### Command Organization

**Categories:**
- **Authentication Commands:** Login, logout, session management
- **Navigation Commands:** Page navigation, routing verification
- **Data Commands:** API interactions, fixture loading
- **Verification Commands:** State checks, assertion helpers

**Best Practices:**
- One command per logical operation
- Comprehensive JSDoc documentation
- Chainable return types
- Descriptive command names

## Test File Structure

### Standard Test Template

```javascript
// Import dependencies
import { TestConstants } from '../../support/constants/test-constants';

// Test suite description
describe('Feature Area - Specific Functionality', () => {
  // Setup before each test
  beforeEach(() => {
    cy.clearSession();
    cy.visit('/feature-path');
  });

  // Cleanup after each test (if needed)
  afterEach(() => {
    // Cleanup operations
  });

  // Individual test case
  it('R-FEAT-001: Should perform expected behavior', () => {
    // Arrange - Setup test conditions
    cy.login('testuser', 'testpassword');

    // Act - Perform test actions
    cy.get(TestConstants.SELECTORS.DASHBOARD.ADD_USER_BUTTON).click();

    // Assert - Verify outcomes
    cy.get(TestConstants.SELECTORS.DASHBOARD.USER_TABLE)
      .should('be.visible');
  });
});
```

### Test Naming Convention

**Pattern:** `R-{FEATURE}-{NUMBER}: Should {expected behavior}`

**Examples:**
- `R-AUTH-001: Should reject invalid credentials`
- `R-DASH-015: Should display user list after login`
- `R-ADMIN-003: Should update system configuration`

**Components:**
- **Requirement ID:** `R-{FEATURE}-{NUMBER}` for traceability
- **Behavior Description:** Clear, action-based statement
- Active voice, starting with "Should"

## Fixtures Organization

### Fixture Files

Store test data in JSON fixtures:

```javascript
// cypress/fixtures/users.json
{
  "validUser": {
    "username": "testuser",
    "password": "TestPassword123!",
    "email": "test@example.com"
  },
  "adminUser": {
    "username": "admin",
    "password": "AdminPassword123!",
    "email": "admin@example.com"
  },
  "invalidUser": {
    "username": "invalid",
    "password": "wrong"
  }
}
```

### Fixture Usage

```javascript
describe('User Management', () => {
  let users;

  before(() => {
    cy.fixture('users').then((data) => {
      users = data;
    });
  });

  it('should login with valid credentials', () => {
    cy.login(users.validUser.username, users.validUser.password);
  });
});
```

## Best Practices

**Maintainability:**
- Keep test files focused on single feature area
- Extract repeated logic to custom commands
- Use constants for all selectors and test data

**Clarity:**
- Descriptive file and test names
- Clear directory organization
- Comprehensive JSDoc documentation

**Reusability:**
- Centralized constants
- Reusable custom commands
- Shared fixtures for common data

**Scalability:**
- Logical grouping by feature
- Consistent naming conventions
- Easy to locate and update tests
