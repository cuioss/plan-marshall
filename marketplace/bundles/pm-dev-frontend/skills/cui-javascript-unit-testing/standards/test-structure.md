# Test Structure

Test file organization, naming conventions, setup files, and directory structure for Jest testing.

## Overview

Proper test organization ensures tests are easy to find, maintain, and execute. This guide defines standard directory structures, file naming conventions, and setup patterns for Jest tests.

## Directory Structure

### Standard Layout

```
src/test/js/
├── components/          # Component tests
│   ├── qwc-jwt-config.test.js
│   ├── qwc-jwt-debugger.test.js
│   └── user-profile.test.js
├── mocks/              # Test mocks
│   ├── devui.js
│   ├── lit.js
│   ├── lit-decorators.js
│   ├── lit-directives.js
│   └── style-mock.js
├── setup/              # Test setup files
│   ├── jest.setup.js
│   └── jest.setup-dom.js
├── utils/              # Test utilities
│   ├── test-helpers.js
│   └── wait-for-update.js
└── integration/        # Integration tests
    └── api-integration.test.js
```

### Directory Purpose

**components/** - Unit tests for individual components
- One test file per component
- Tests component behavior in isolation
- Uses mocked dependencies

**mocks/** - Mock implementations for dependencies
- Framework mocks (Lit, DevUI)
- External dependency mocks
- Shared across all tests

**setup/** - Global test configuration
- Run before/after test environment setup
- Configure global test behavior
- Add custom matchers

**utils/** - Test helper functions
- Shared test utilities
- Wait functions
- Helper functions for common test operations

**integration/** - Integration tests
- Multi-component interactions
- API integration tests
- End-to-end flows (distinct from Cypress E2E)

## File Naming Conventions

### Test Files

**Component tests**: `component-name.test.js`
```
qwc-jwt-config.test.js
user-profile-card.test.js
navigation-menu.test.js
```

**Integration tests**: `feature-name.test.js`
```
authentication-flow.test.js
data-sync.test.js
user-workflow.test.js
```

**Utility tests**: `utility-name.test.js`
```
validation-utils.test.js
format-helpers.test.js
```

### Mock Files

**Mock files**: Match module name
```
lit.js           // Mocks 'lit' module
devui.js         // Mocks 'devui' module
lit-directives.js // Mocks 'lit/directives/*'
```

### Why `.test.js` Suffix?

- Jest testMatch pattern: `**/*.test.js`
- Clear distinction from source files
- IDEs recognize as test files
- Consistent with JavaScript ecosystem

## Setup Files

### jest.setup.js

Global test configuration that runs BEFORE test environment:

```javascript
// src/test/js/setup/jest.setup.js

// Suppress console warnings in tests
global.console = {
  ...console,
  warn: jest.fn(),
  error: jest.fn(),
};

// Global mocks for browser APIs
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Set default test timeout
jest.setTimeout(10000);
```

### jest.setup-dom.js

DOM-specific configuration that runs AFTER test environment:

```javascript
// src/test/js/setup/jest.setup-dom.js

import '@testing-library/jest-dom';

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock window.fetch
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock customElements if needed
if (!global.customElements) {
  global.customElements = {
    define: jest.fn(),
    get: jest.fn(),
    whenDefined: jest.fn(() => Promise.resolve()),
  };
}
```

## Test File Structure

### Standard Test Template

```javascript
// Import dependencies
import { html, fixture, expect } from '@open-wc/testing';
import './component-name.js';

// Describe block for component
describe('ComponentName', () => {
  let element;

  // Setup before each test
  beforeEach(async () => {
    element = await fixture(html`<component-name></component-name>`);
  });

  // Cleanup after each test
  afterEach(() => {
    element?.remove();
  });

  // Group related tests
  describe('Rendering', () => {
    it('should render with default properties', () => {
      expect(element).to.exist;
      expect(element.shadowRoot).to.exist;
    });
  });

  describe('Properties', () => {
    it('should have default values', () => {
      expect(element.propertyName).to.equal(defaultValue);
    });
  });

  describe('Methods', () => {
    it('should execute correctly', async () => {
      const result = await element.methodName();
      expect(result).to.equal(expected);
    });
  });

  describe('Events', () => {
    it('should dispatch custom events', async () => {
      let eventFired = false;
      element.addEventListener('custom-event', () => {
        eventFired = true;
      });

      await element.triggerEvent();
      expect(eventFired).to.be.true;
    });
  });
});
```

### Organizational Patterns

**Group by functionality**:
```javascript
describe('ComponentName', () => {
  describe('Rendering', () => { /* ... */ });
  describe('Properties', () => { /* ... */ });
  describe('Methods', () => { /* ... */ });
  describe('Events', () => { /* ... */ });
  describe('Accessibility', () => { /* ... */ });
});
```

**Group by feature**:
```javascript
describe('UserAuthentication', () => {
  describe('Login', () => { /* ... */ });
  describe('Logout', () => { /* ... */ });
  describe('Session Management', () => { /* ... */ });
  describe('Error Handling', () => { /* ... */ });
});
```

## Test Utilities

### Common Helper Functions

Create reusable test utilities:

```javascript
// src/test/js/utils/test-helpers.js

/**
 * Wait for component to complete update
 */
export const waitForComponentUpdate = async (component) => {
  await component.updateComplete;
  await new Promise(resolve => setTimeout(resolve, 0));
};

/**
 * Create mock event
 */
export const createMockEvent = (type, detail = {}) => {
  return new CustomEvent(type, {
    detail,
    bubbles: true,
    composed: true,
  });
};

/**
 * Query shadow root
 */
export const queryShadow = (element, selector) => {
  return element.shadowRoot?.querySelector(selector);
};

/**
 * Query all in shadow root
 */
export const queryAllShadow = (element, selector) => {
  return element.shadowRoot?.querySelectorAll(selector);
};
```

### Usage in Tests

```javascript
import { waitForComponentUpdate, queryShadow } from '../utils/test-helpers.js';

it('should update display', async () => {
  element.value = 'new value';
  await waitForComponentUpdate(element);

  const display = queryShadow(element, '.display');
  expect(display.textContent).to.equal('new value');
});
```

## Best Practices

### File Organization

1. **One component, one test file** - Keep tests focused
2. **Co-locate related tests** - Group by feature or domain
3. **Separate mocks from tests** - Reuse mocks across tests
4. **Centralize setup** - Use setup files for common configuration

### Test Isolation

1. **Clean up after each test** - Remove DOM elements, reset mocks
2. **Avoid shared state** - Each test should be independent
3. **Use beforeEach/afterEach** - Consistent setup and teardown
4. **Reset mocks** - Clear mock history between tests

### Performance

1. **Keep setup minimal** - Only create what's needed
2. **Reuse fixtures** - Don't recreate identical test data
3. **Mock heavy dependencies** - Avoid real network calls
4. **Use fake timers** - Control time-dependent tests

### Naming

1. **Descriptive test names** - Explain what's being tested
2. **Use "should" pattern** - "should render correctly"
3. **Group logically** - Use describe blocks effectively
4. **Consistent conventions** - Follow same patterns across tests

## Common Patterns

### beforeEach/afterEach

```javascript
describe('Component', () => {
  let element;
  let container;

  beforeEach(async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    element = await fixture(html`<my-component></my-component>`);
  });

  afterEach(() => {
    element?.remove();
    container?.remove();
  });

  // Tests...
});
```

### Shared Test Data

```javascript
describe('DataProcessor', () => {
  const testData = {
    users: [
      { id: 1, name: 'Alice' },
      { id: 2, name: 'Bob' },
    ],
    config: { timeout: 5000 },
  };

  it('should process users', () => {
    const result = processUsers(testData.users);
    expect(result).toHaveLength(2);
  });

  it('should apply config', () => {
    const processor = new DataProcessor(testData.config);
    expect(processor.timeout).toBe(5000);
  });
});
```

### Async Setup

```javascript
describe('AsyncComponent', () => {
  let element;
  let data;

  beforeEach(async () => {
    // Load test data
    data = await loadTestData();

    // Create component with data
    element = await fixture(html`
      <async-component .data=${data}></async-component>
    `);

    // Wait for initial render
    await element.updateComplete;
  });

  // Tests...
});
```

## See Also

- [Jest Configuration](jest-configuration.md) - Jest setup and config
- [Testing Patterns](testing-patterns.md) - Component testing patterns
- [Coverage Standards](coverage-standards.md) - Coverage requirements
