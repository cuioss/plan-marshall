# DOM and Component Testing

## Container-Based Testing Pattern

The standard pattern for testing JavaScript components that render into the DOM:

```javascript
describe('token-verifier', () => {
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    container.id = 'token-verification';
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('renders verification form', () => {
    init(container);
    expect(container.querySelector('#field-token-input')).not.toBeNull();
    expect(container.querySelector('.verify-token-button')).not.toBeNull();
  });
});
```

The `beforeEach`/`afterEach` cycle ensures each test starts with a fresh DOM -- no leaked state between tests.

## DOM Query Assertions

### querySelector Pattern

For vanilla JS components, use standard DOM queries:

```javascript
test('renders route selector with correct options', () => {
  init(container);
  const selector = container.querySelector('.route-selector');

  expect(selector).not.toBeNull();
  expect(selector.options.length).toBe(2);
  expect(selector.options[0].textContent).toContain('users');
  expect(selector.options[0].value).toBe('/api/users');
});
```

### Testing Library Queries

When @testing-library/jest-dom is available, prefer role-based queries. They verify accessibility while testing behavior:

```javascript
import { screen } from '@testing-library/dom';

test('renders submit button', () => {
  init(container);
  const button = screen.getByRole('button', { name: /submit/i });
  expect(button).toBeEnabled();
});
```

**Query priority** (prefer higher):
1. `getByRole` -- accessible role + name (best, doubles as accessibility check)
2. `getByText` -- visible text content
3. `getByTestId` -- data-testid attribute (last resort)

**Query variants**:
- `getBy*` -- element must exist, throws if missing
- `queryBy*` -- returns null if missing (use for asserting non-existence)
- `findBy*` -- waits for element to appear (async)

## Event Simulation

### Click Events

```javascript
test('toggles panel visibility on button click', () => {
  init(container);
  const button = container.querySelector('.toggle-button');
  const panel = container.querySelector('.panel');

  button.click();
  expect(panel.hidden).toBe(false);

  button.click();
  expect(panel.hidden).toBe(true);
});
```

### Keyboard Events

```javascript
test('closes dialog on Escape key', async () => {
  const promise = showConfirmationDialog({ message: 'Confirm?' });

  const dialog = document.querySelector('.confirmation-dialog');
  dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));

  const result = await promise;
  expect(result).toBe(false);
});
```

### Input Events

```javascript
test('validates input on change', () => {
  init(container);
  const input = container.querySelector('#email-input');

  input.value = 'invalid';
  input.dispatchEvent(new Event('input', { bubbles: true }));

  expect(container.querySelector('.error-message')).not.toBeNull();
});
```

## ARIA and Accessibility Testing

Test that components set correct ARIA attributes for screen readers and keyboard navigation:

```javascript
test('sets correct ARIA attributes on disclosure button', () => {
  init(container);
  const button = container.querySelector('.context-help-toggle');

  expect(button.getAttribute('aria-expanded')).toBe('false');
  expect(button.getAttribute('aria-controls')).toBe('help-panel');
  expect(button.type).toBe('button');
});

test('updates aria-expanded on toggle', () => {
  init(container);
  const button = container.querySelector('.context-help-toggle');

  button.click();
  expect(button.getAttribute('aria-expanded')).toBe('true');
});
```

## Web Component Testing (Lit / Custom Elements)

### Shadow DOM Mocking in jsdom

jsdom has limited Shadow DOM support. The common pattern mocks `shadowRoot` with a regular div:

```javascript
function setupComponent() {
  const component = new MyComponent();
  component.shadowRoot = document.createElement('div');
  return component;
}

function setupQuerySelectorMock(component, elements) {
  component.shadowRoot.querySelector = jest.fn((selector) => {
    switch (selector) {
      case '#token-input': return elements.tokenInput;
      case '.validate-button': return elements.validateButton;
      default: return null;
    }
  });
}
```

### Lit Component Testing

For Lit components, use `@open-wc/testing` which provides test fixtures and helpers:

```javascript
import { fixture, html, expect } from '@open-wc/testing';
import '../src/my-component.js';

test('renders with default values', async () => {
  const el = await fixture(html`<my-component></my-component>`);
  expect(el.shadowRoot.querySelector('h1')).to.exist;
});

test('reflects attribute changes', async () => {
  const el = await fixture(html`<my-component name="World"></my-component>`);
  expect(el.shadowRoot.textContent).to.include('World');
});
```

For jsdom-only environments where `@open-wc/testing` is unavailable, mock Lit's template tags:

```javascript
// mocks/lit.js (mapped via moduleNameMapper)
export function html(strings, ...values) {
  return strings.reduce((acc, str, i) => acc + str + (values[i] ?? ''), '');
}

export function css(strings, ...values) {
  return strings.reduce((acc, str, i) => acc + str + (values[i] ?? ''), '');
}
```

### Custom Matchers for Web Components

```javascript
// jest.setup-dom.js
expect.extend({
  toHaveRenderedContent(component, content) {
    const rendered = component._lastRenderedResult || '';
    const pass = rendered.includes(content);
    return {
      pass,
      message: () =>
        `expected component ${pass ? 'not ' : ''}to have rendered content "${content}"`,
    };
  },

  toHaveShadowClass(component, className) {
    const el = component.shadowRoot?.querySelector(`.${className}`);
    return {
      pass: el !== null,
      message: () =>
        `expected shadow DOM ${el ? 'not ' : ''}to contain element with class "${className}"`,
    };
  },
});
```

### Lifecycle Testing

```javascript
describe('component lifecycle', () => {
  test('initializes with default properties', () => {
    const component = setupComponent();
    expect(component._token).toBe('');
    expect(component._validationResult).toBeNull();
  });

  test('cleans up intervals on disconnect', () => {
    const component = setupComponent();
    component.connectedCallback();

    const clearSpy = jest.spyOn(window, 'clearInterval');
    component.disconnectedCallback();

    expect(clearSpy).toHaveBeenCalled();
  });
});
```

### Browser-Based Testing (When jsdom Is Insufficient)

For full Shadow DOM fidelity, use Web Test Runner with a browser provider. This is recommended by the Lit team for production web component testing. Use jsdom for unit tests where Shadow DOM behavior is not critical.

## Test Helper Patterns

### DOM Factory Helpers

Create helpers that produce realistic DOM structures for tests:

```javascript
// test-helpers.js
export function mockCreateFormField({ label, type = 'text', id }) {
  const wrapper = document.createElement('div');
  wrapper.className = 'form-field';

  const labelEl = document.createElement('label');
  labelEl.textContent = label;
  labelEl.setAttribute('for', id);

  const input = document.createElement(type === 'textarea' ? 'textarea' : 'input');
  input.id = id;
  if (type !== 'textarea') input.type = type;

  wrapper.append(labelEl, input);
  return wrapper;
}
```

### Full DOM Templates

For complex components, define HTML templates as constants:

```javascript
const FULL_DOM = `
  <div id="app-container">
    <main class="tabs-container hidden">
      <div class="tabs" role="tablist">
        <button role="tab" aria-selected="true">Tab 1</button>
        <button role="tab" aria-selected="false">Tab 2</button>
      </div>
      <div role="tabpanel" id="panel-1">Content 1</div>
      <div role="tabpanel" id="panel-2" hidden>Content 2</div>
    </main>
  </div>`;

beforeEach(() => {
  document.body.innerHTML = FULL_DOM;
});
```

### Mock Scenario Objects

Pre-define mock data scenarios for consistency across tests:

```javascript
export const mockScenarios = {
  runtimeActive: () => ({
    status: 'active',
    issuers: [{ name: 'keycloak', url: 'https://keycloak:8443/realms/master' }],
  }),
  runtimeWithIssues: () => ({
    status: 'degraded',
    errors: ['Certificate expired for issuer: keycloak'],
  }),
  networkError: () => {
    throw new Error('Network error');
  },
};
```

## See Also

- [Test Fundamentals](test-fundamentals.md) - Framework setup, AAA pattern, coverage configuration
- [Mocking and Async Patterns](mocking-async.md) - Module mocking, fetch mocks, timers
