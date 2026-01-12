# Testing Patterns

Component testing patterns, mocking strategies, assertions, and the AAA pattern for Jest unit tests.

## Overview

Effective testing requires consistent patterns for structuring tests, mocking dependencies, and making assertions. This guide covers proven patterns for testing JavaScript components with Jest.

## AAA Pattern (Arrange-Act-Assert)

### Pattern Structure

Every test should follow this three-phase pattern:

```javascript
it('should update display when value changes', async () => {
  // Arrange - Set up test conditions
  const element = await fixture(html`<my-component></my-component>`);
  const newValue = 'test value';

  // Act - Perform the action being tested
  element.value = newValue;
  await element.updateComplete;

  // Assert - Verify the expected outcome
  expect(element.shadowRoot.textContent).toContain(newValue);
});
```

### Why AAA?

- **Clarity**: Each phase has clear purpose
- **Readability**: Tests are easy to understand
- **Maintainability**: Easy to modify individual phases
- **Consistency**: Standard structure across all tests

### AAA Examples

**Simple test**:
```javascript
it('should calculate sum correctly', () => {
  // Arrange
  const a = 5;
  const b = 3;

  // Act
  const result = sum(a, b);

  // Assert
  expect(result).toBe(8);
});
```

**Async test**:
```javascript
it('should fetch and display user data', async () => {
  // Arrange
  const userId = '123';
  const mockUser = { id: '123', name: 'Alice' };
  fetch.mockResolvedValueOnce({
    ok: true,
    json: async () => mockUser,
  });

  // Act
  const element = await fixture(html`<user-display .userId=${userId}></user-display>`);
  await element.updateComplete;

  // Assert
  expect(element.shadowRoot.textContent).toContain('Alice');
});
```

## Component Testing

### Lit Component Test Structure

Standard pattern for testing Lit web components:

```javascript
import { html, fixture, expect } from '@open-wc/testing';
import './my-component.js';

describe('MyComponent', () => {
  let element;

  beforeEach(async () => {
    element = await fixture(html`<my-component></my-component>`);
  });

  afterEach(() => {
    element?.remove();
  });

  describe('Rendering', () => {
    it('should render with default properties', () => {
      expect(element).to.exist;
      expect(element.shadowRoot).to.exist;
    });

    it('should have correct tag name', () => {
      expect(element.tagName.toLowerCase()).to.equal('my-component');
    });

    it('should render initial content', () => {
      const content = element.shadowRoot.querySelector('.content');
      expect(content).to.exist;
    });
  });

  describe('Properties', () => {
    it('should have default property values', () => {
      expect(element.title).to.equal('');
      expect(element.isActive).to.be.false;
    });

    it('should update properties reactively', async () => {
      element.title = 'New Title';
      await element.updateComplete;

      const header = element.shadowRoot.querySelector('.header');
      expect(header.textContent).to.equal('New Title');
    });

    it('should reflect attributes', async () => {
      element.setAttribute('title', 'Test');
      await element.updateComplete;

      expect(element.title).to.equal('Test');
    });
  });

  describe('Methods', () => {
    it('should execute method correctly', async () => {
      const result = await element.doSomething();
      expect(result).to.equal(expectedValue);
    });

    it('should update state when method called', async () => {
      await element.toggleActive();
      expect(element.isActive).to.be.true;
    });
  });

  describe('Events', () => {
    it('should dispatch custom events', async () => {
      let eventData = null;

      element.addEventListener('custom-event', (e) => {
        eventData = e.detail;
      });

      await element.triggerEvent();

      expect(eventData).to.not.be.null;
      expect(eventData.value).to.equal('expected');
    });

    it('should handle user interactions', async () => {
      const button = element.shadowRoot.querySelector('button');
      button.click();
      await element.updateComplete;

      expect(element.clickCount).to.equal(1);
    });
  });

  describe('Accessibility', () => {
    it('should be accessible', async () => {
      await expect(element).to.be.accessible();
    });

    it('should have proper ARIA attributes', () => {
      const button = element.shadowRoot.querySelector('button');
      expect(button).to.have.attribute('aria-label');
    });
  });
});
```

## Mocking Strategies

### Lit Framework Mock

Mock the entire Lit framework for isolated testing:

```javascript
// src/test/js/mocks/lit.js

export const html = (strings, ...values) => {
  return { strings, values, _$litType$: 1 };
};

export const css = (strings, ...values) => {
  return { strings, values, _$litType$: 2 };
};

export class LitElement {
  static properties = {};
  static styles = [];

  constructor() {
    this.updateComplete = Promise.resolve();
    this.shadowRoot = null;
  }

  connectedCallback() {
    if (!this.shadowRoot) {
      this.shadowRoot = document.createElement('div');
    }
    this.requestUpdate();
  }

  disconnectedCallback() {
    // Cleanup
  }

  render() {
    return html``;
  }

  requestUpdate() {
    // Trigger render
    const rendered = this.render();
    // Process rendered template
    return this.updateComplete;
  }

  updated(changedProperties) {
    // Override in tests if needed
  }
}
```

### DevUI Mock

Mock DevUI integration for component testing:

```javascript
// src/test/js/mocks/devui.js

export const devui = {
  jsonRPC: {
    call: jest.fn((method, params) => {
      // Return mock data based on method
      return Promise.resolve({ success: true });
    }),
  },

  router: {
    navigate: jest.fn((path) => {
      // Mock navigation
      console.log(`Navigate to: ${path}`);
    }),

    getCurrentPath: jest.fn(() => '/current/path'),
  },

  state: {
    get: jest.fn((key) => null),
    set: jest.fn((key, value) => {}),
  },
};
```

### Function Mocking

Mock individual functions with Jest:

```javascript
// Mock module function
jest.mock('../utils/api-client', () => ({
  fetchData: jest.fn(),
  postData: jest.fn(),
}));

// Import mocked module
import { fetchData, postData } from '../utils/api-client';

it('should call API correctly', async () => {
  // Setup mock return value
  fetchData.mockResolvedValue({ data: 'test' });

  // Use in test
  const result = await fetchData('/endpoint');

  // Verify mock was called
  expect(fetchData).toHaveBeenCalledWith('/endpoint');
  expect(result.data).toBe('test');
});
```

### Spy on Methods

Spy on existing methods:

```javascript
it('should call internal method', async () => {
  // Spy on method
  const spy = jest.spyOn(element, 'internalMethod');

  // Trigger action
  await element.publicMethod();

  // Verify spy was called
  expect(spy).toHaveBeenCalled();
  expect(spy).toHaveBeenCalledWith(expectedArg);

  // Restore original
  spy.mockRestore();
});
```

### Mock timers

Control time-dependent code:

```javascript
describe('Timer functionality', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should debounce calls', () => {
    const callback = jest.fn();
    const debounced = debounce(callback, 1000);

    debounced();
    debounced();
    debounced();

    expect(callback).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1000);

    expect(callback).toHaveBeenCalledTimes(1);
  });
});
```

## Assertions

### Basic Assertions

Jest provides comprehensive matchers:

```javascript
// Equality
expect(value).toBe(5);                    // Strict equality (===)
expect(value).toEqual({ a: 1 });          // Deep equality
expect(value).not.toBe(null);             // Negation

// Truthiness
expect(value).toBeTruthy();               // Boolean true
expect(value).toBeFalsy();                // Boolean false
expect(value).toBeNull();                 // Strictly null
expect(value).toBeUndefined();            // Strictly undefined
expect(value).toBeDefined();              // Not undefined

// Numbers
expect(value).toBeGreaterThan(3);
expect(value).toBeGreaterThanOrEqual(3.5);
expect(value).toBeLessThan(5);
expect(value).toBeCloseTo(0.3);           // Floating point

// Strings
expect(string).toMatch(/pattern/);
expect(string).toContain('substring');

// Arrays
expect(array).toContain(item);
expect(array).toHaveLength(3);

// Objects
expect(object).toHaveProperty('key');
expect(object).toHaveProperty('nested.key', 'value');
```

### DOM Assertions

Using @testing-library/jest-dom:

```javascript
// Element existence
expect(element).toBeInTheDocument();
expect(element).toBeVisible();
expect(element).toBeEmpty();

// Element content
expect(element).toHaveTextContent('text');
expect(element).toHaveValue('value');

// Element attributes
expect(element).toHaveAttribute('attr', 'value');
expect(element).toHaveClass('className');

// Element state
expect(button).toBeDisabled();
expect(button).toBeEnabled();
expect(checkbox).toBeChecked();
expect(input).toHaveFocus();

// Accessibility
expect(element).toHaveAccessibleName('Button');
expect(element).toHaveAccessibleDescription('Description');
```

### Async Assertions

Handle asynchronous operations:

```javascript
// Async/await
it('should resolve promise', async () => {
  await expect(promise).resolves.toBe(value);
  await expect(promise).rejects.toThrow(Error);
});

// Wait for element
it('should display loading state', async () => {
  element.fetchData();

  // Wait for element to appear
  await waitFor(() => {
    expect(element.shadowRoot.querySelector('.loading')).toBeInTheDocument();
  });
});
```

### Custom Matchers

Create custom matchers for domain-specific assertions:

```javascript
expect.extend({
  toBeValidUser(received) {
    const pass = received &&
                 received.id &&
                 received.name &&
                 received.email.includes('@');

    return {
      pass,
      message: () => pass
        ? `expected ${received} not to be a valid user`
        : `expected ${received} to be a valid user`,
    };
  },
});

// Usage
expect(user).toBeValidUser();
```

## Error Testing

### Testing Error Conditions

```javascript
it('should throw error for invalid input', () => {
  expect(() => {
    processData(null);
  }).toThrow('Invalid input');

  expect(() => {
    processData(null);
  }).toThrow(ValidationError);
});

it('should handle errors gracefully', async () => {
  const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

  await element.methodThatMightFail();

  expect(consoleSpy).toHaveBeenCalledWith(
    expect.stringContaining('error')
  );

  consoleSpy.mockRestore();
});
```

### Error Boundary Testing

```javascript
it('should catch and display errors', async () => {
  // Cause error
  element.data = null;
  await element.updateComplete;

  // Verify error handling
  const errorMessage = element.shadowRoot.querySelector('.error');
  expect(errorMessage).toBeInTheDocument();
  expect(errorMessage.textContent).toContain('Failed to load');
});
```

## Integration Testing Patterns

### Multi-Component Tests

```javascript
describe('User workflow', () => {
  let container;
  let userList;
  let userDetail;

  beforeEach(async () => {
    container = await fixture(html`
      <div>
        <user-list></user-list>
        <user-detail></user-detail>
      </div>
    `);

    userList = container.querySelector('user-list');
    userDetail = container.querySelector('user-detail');
  });

  it('should update detail when user selected', async () => {
    // Select user in list
    const firstUser = userList.shadowRoot.querySelector('.user-item');
    firstUser.click();
    await userList.updateComplete;

    // Verify detail updated
    await userDetail.updateComplete;
    expect(userDetail.userId).to.equal(firstUser.dataset.id);
  });
});
```

## Best Practices

### Test Independence

1. **No shared state** between tests
2. **Clean up after each test** - remove elements, reset mocks
3. **Use beforeEach/afterEach** consistently
4. **Each test can run alone** or with others

### Clear Test Names

```javascript
// ✅ Good - explains what and why
it('should disable submit button when form is invalid', () => {});
it('should show error message when API call fails', () => {});
it('should navigate to home page after successful login', () => {});

// ❌ Bad - vague or technical
it('should work', () => {});
it('test button', () => {});
it('returns true', () => {});
```

### Focus on Behavior

Test what the component does, not how it does it:

```javascript
// ✅ Good - tests behavior
it('should display user name after loading', async () => {
  await element.loadUser('123');
  expect(element.shadowRoot.textContent).toContain('Alice');
});

// ❌ Bad - tests implementation
it('should set _userName property', () => {
  element._userName = 'Alice';
  expect(element._userName).toBe('Alice');
});
```

## See Also

- [Jest Configuration](jest-configuration.md) - Jest setup
- [Test Structure](test-structure.md) - File organization
- [Coverage Standards](coverage-standards.md) - Coverage requirements
