# Mocking and Async Testing Patterns

## Module Mocking

### Full Module Mock

Mock entire modules at the top of the test file. With `resetMocks: true`, implementations are cleared between tests:

```javascript
jest.mock('../../main/webapp/js/api.js');
jest.mock('../../main/webapp/js/utils.js');

// Re-apply implementations in beforeEach (needed when resetMocks: true)
beforeEach(() => {
  utils.sanitizeHtml.mockImplementation((s) => s || '');
  utils.t.mockImplementation((key) => key);
  utils.displayUiError.mockImplementation(() => {});
});
```

### Partial Module Mock

Mock specific exports while keeping others real:

```javascript
// Jest
jest.mock('./config', () => ({
  ...jest.requireActual('./config'),
  getApiUrl: jest.fn(() => 'https://test-api.example.com'),
}));

// Vitest
vi.mock('./config', async () => ({
  ...(await vi.importActual('./config')),
  getApiUrl: vi.fn(() => 'https://test-api.example.com'),
}));
```

### Global Module Mocks (moduleNameMapper)

For external libraries that every test needs mocked, use `moduleNameMapper` in config:

```json
{
  "moduleNameMapper": {
    "^nf.Common$": "<rootDir>/src/test/js/mocks/nf-common.js",
    "^lit$": "<rootDir>/src/test/js/mocks/lit.js",
    "^devui$": "<rootDir>/src/test/js/mocks/devui.js"
  }
}
```

The mock module exports the same interface as the real module with controlled behavior:

```javascript
// mocks/nf-common.js
module.exports = {
  formatValue: (v) => v,
  substringAfterLast: (str, sep) => {
    const idx = str.lastIndexOf(sep);
    return idx >= 0 ? str.substring(idx + sep.length) : str;
  },
};
```

## Fetch Mocking

### Setup File Approach

Provide a global fetch mock in the setup file (jsdom does not include fetch):

```javascript
// jest.setup.js
globalThis.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
  })
);
```

### Response Helpers

Create helpers for common response patterns:

```javascript
function mockJsonResponse(data, ok = true, status = 200) {
  globalThis.fetch.mockResolvedValueOnce({
    ok,
    status,
    statusText: ok ? 'OK' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
}

function mockErrorResponse(status, body = 'Error') {
  globalThis.fetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: 'Error',
    json: () => Promise.reject(new Error('not json')),
    text: () => Promise.resolve(body),
  });
}
```

### Asserting Fetch Calls

```javascript
test('sends POST with token in body', async () => {
  mockJsonResponse({ valid: true, decoded: {} });

  await verifyToken('eyJhbGci...');

  const [url, opts] = globalThis.fetch.mock.calls[0];
  expect(url).toBe('api/verify-token');
  expect(opts.method).toBe('POST');
  expect(JSON.parse(opts.body)).toEqual({ token: 'eyJhbGci...' });
});
```

## Mock Patterns

### Mock External Dependencies, Not Internal Logic

Mock boundaries (APIs, file system, third-party services). Internal logic should run as-is:

```javascript
// Good -- mocks external API boundary
jest.mock('./api');
api.fetchUser.mockResolvedValue({ name: 'Alice' });

// Bad -- mocks internal helper the function calls
jest.mock('./utils', () => ({ parseResponse: jest.fn() }));
```

When mocking setup becomes complicated, the code under test likely needs refactoring.

### Spy Without Replacing

Use `spyOn` to observe calls without replacing behavior:

```javascript
test('logs error on validation failure', async () => {
  const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

  await validate(null);

  expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('validation failed'));
  errorSpy.mockRestore();
});
```

### Mock Reset with DevUI Pattern

For complex mock objects (like JSON-RPC interfaces), provide a reset helper:

```javascript
// mocks/devui.js
const mockJsonRPC = {
  validateToken: jest.fn(),
  getConfig: jest.fn(),
};

export function resetDevUIMocks() {
  Object.values(mockJsonRPC).forEach((fn) => fn.mockReset());
}

export const devui = { jsonRPC: { Service: mockJsonRPC } };
```

```javascript
// In tests
beforeEach(() => {
  resetDevUIMocks();
});
```

## Async Testing

### async/await (Preferred)

The most readable approach for promise-based code:

```javascript
test('fetches and displays user data', async () => {
  api.fetchUser.mockResolvedValue({ name: 'Alice', role: 'admin' });

  await init(container);

  expect(container.querySelector('.user-name').textContent).toBe('Alice');
});
```

### Error Testing with .rejects

Prefer `.rejects.toThrow()` over try/catch for cleaner error assertions:

```javascript
test('rejects with network error', async () => {
  api.fetchUser.mockRejectedValue(new Error('Network error'));

  await expect(fetchUserData('123')).rejects.toThrow('Network error');
});
```

When using try/catch (sometimes needed for complex error inspection), always pair with `expect.assertions`:

```javascript
test('throws with error details', async () => {
  expect.assertions(2);
  try {
    await riskyOperation();
  } catch (error) {
    expect(error.code).toBe('TIMEOUT');
    expect(error.retryable).toBe(true);
  }
});
```

### Waiting for DOM Updates

After triggering async operations, the DOM may not update immediately. Use a microtask yield:

```javascript
const tick = (ms = 0) => new Promise((resolve) => setTimeout(resolve, ms));

test('shows validation result after async check', async () => {
  api.verifyToken.mockResolvedValue({ valid: true });

  init(container);
  container.querySelector('#token-input').value = 'test.jwt.token';
  container.querySelector('.verify-button').click();
  await tick(10);

  expect(container.querySelector('.status.valid')).not.toBeNull();
});
```

For Testing Library, prefer `waitFor` or `findBy*` queries instead of manual ticks:

```javascript
import { waitFor } from '@testing-library/dom';

test('shows result after validation', async () => {
  api.verifyToken.mockResolvedValue({ valid: true });
  triggerValidation();

  await waitFor(() => {
    expect(screen.getByText('Token is valid')).toBeInTheDocument();
  });
});
```

### Waiting for Lit Component Updates

```javascript
test('updates display after property change', async () => {
  component._token = 'new-token';
  await waitForComponentUpdate(component);

  expect(component).toHaveRenderedContent('new-token');
});
```

## Timer Control

### Fake Timers

Use fake timers when testing time-dependent behavior (debounce, polling, auto-dismiss):

```javascript
test('auto-removes success message after timeout', () => {
  jest.useFakeTimers();

  displayUiSuccess(container, 'Saved');
  expect(container.querySelector('.success-message')).not.toBeNull();

  jest.advanceTimersByTime(5000);
  expect(container.querySelector('.success-message')).toBeNull();

  jest.useRealTimers();
});
```

### Async Timer APIs

When fake timers interact with promises, use the async variant to avoid deadlocks:

```javascript
test('retries failed request after delay', async () => {
  jest.useFakeTimers();
  api.fetch.mockRejectedValueOnce(new Error('timeout')).mockResolvedValueOnce({ ok: true });

  const promise = fetchWithRetry();

  // Async variant flushes microtasks between timer advances
  await jest.advanceTimersByTimeAsync(3000);
  const result = await promise;

  expect(result).toEqual({ ok: true });
  jest.useRealTimers();
});
```

Always restore real timers in `afterEach` to prevent leaking into other tests:

```javascript
afterEach(() => {
  jest.useRealTimers();
});
```

## Test Isolation

### State Reset Between Tests

Each test must be independent. Use setup/teardown hooks to prevent shared state:

```javascript
describe('app initialization', () => {
  const originalNf = globalThis.nf;

  beforeEach(() => {
    history.replaceState({}, '', '/app/');
  });

  afterEach(() => {
    document.body.innerHTML = '';
    if (originalNf !== undefined) globalThis.nf = originalNf;
    else delete globalThis.nf;
    jest.resetModules();
  });
});
```

### Module Reset

When testing modules with side effects (top-level initialization), reset the module registry:

```javascript
afterEach(() => {
  jest.resetModules();
});

test('initializes with custom config', async () => {
  process.env.API_URL = 'https://custom-api.example.com';
  const { init } = await import('./app.js');
  // Module re-executes with new environment
});
```

### Mock Cleanup Hierarchy

| Method | Clears calls | Clears implementation | Restores original |
|--------|:---:|:---:|:---:|
| `mockClear()` | yes | no | no |
| `mockReset()` | yes | yes | no |
| `mockRestore()` | yes | yes | yes |

With `restoreMocks: true` in config, all mocks are fully restored after each test automatically.

## Sample Test Data

Define test constants at the top of the file for reuse across tests:

```javascript
const SAMPLE_TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMSJ9.signature';

const SAMPLE_CONFIG = {
  component: 'RestApiGatewayProcessor',
  port: 9443,
  routes: [
    { name: 'users', path: '/api/users', methods: ['GET', 'POST'] },
    { name: 'health', path: '/api/health', methods: ['GET'] },
  ],
};

const SAMPLE_VALIDATION_RESULT = {
  valid: true,
  decoded: {
    header: { alg: 'RS256', typ: 'JWT' },
    payload: { sub: 'user1', iss: 'test-issuer', exp: Math.floor(Date.now() / 1000) + 3600 },
  },
};
```
