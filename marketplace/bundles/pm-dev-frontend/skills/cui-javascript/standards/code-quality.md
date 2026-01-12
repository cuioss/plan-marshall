# Code Quality

Code complexity limits, refactoring strategies, and maintainability best practices.

## Overview

Code quality is maintained through strict complexity limits and systematic refactoring strategies. This guide defines measurable quality standards and provides practical refactoring patterns for exceeding complexity thresholds.

## Complexity Limits

All functions must adhere to these complexity limits to ensure maintainability:

### Hard Limits

- **Cyclomatic Complexity**: Maximum 15 branches per function
- **Statement Count**: Maximum 20 statements per function
- **Parameter Count**: Maximum 5 parameters per function
- **Nesting Depth**: Maximum 3 levels of conditional/loop nesting

### Why These Limits?

- **Testability**: Complex functions require exponentially more test cases
- **Maintainability**: High complexity makes code harder to understand and modify
- **Bug Prevention**: Complexity correlates strongly with defect density
- **Code Review**: Simple functions are easier to review thoroughly

## Measuring Complexity

### Cyclomatic Complexity

Counts the number of independent paths through code:

```javascript
// Complexity = 1 (straight through)
function simple(x) {
  return x * 2;
}

// Complexity = 2 (one branch)
function conditional(x) {
  if (x > 0) {
    return x;
  }
  return -x;
}

// Complexity = 4 (three branches)
function complex(x) {
  if (x > 0) {
    return x;
  } else if (x < 0) {
    return -x;
  } else {
    return 0;
  }
}
```

### Statement Count

Counts executable statements in a function:

```javascript
// 5 statements
function calculate(a, b) {
  const sum = a + b;           // 1
  const product = a * b;       // 2
  const average = sum / 2;     // 3
  console.log(average);        // 4
  return { sum, product };     // 5
}
```

## Refactoring Strategies

### Strategy 1: Extract Methods

Break down large functions into focused, single-purpose functions.

#### Before

```javascript
// ❌ Complex monolithic function (20+ statements)
_doRender() {
  if (this._loading && !this._configuration) {
    return html`<div class="loading">Loading...</div>`;
  }
  if (this._error) {
    return html`<div class="error">${this._error}</div>`;
  }
  if (!this._configuration) {
    return html`<div class="loading">No data available</div>`;
  }

  const config = this._configuration;
  return html`
    <div class="container">
      <section class="general">
        <h2>General</h2>
        ${this._renderGeneralFields(config)}
      </section>
      <section class="parser">
        <h2>Parser</h2>
        ${this._renderParserFields(config)}
      </section>
      <section class="health">
        <h2>Health</h2>
        ${this._renderHealthStatus(config)}
      </section>
    </div>
  `;
}
```

#### After

```javascript
// ✅ Refactored with helper methods
_doRender() {
  const loadingOrErrorContent = this._renderLoadingOrError();
  if (loadingOrErrorContent) {
    return loadingOrErrorContent;
  }

  if (!this._configuration) {
    return html`<div class="loading">No data available</div>`;
  }

  return this._renderConfiguration();
}

_renderLoadingOrError() {
  if (this._loading && !this._configuration) {
    return html`<div class="loading">Loading...</div>`;
  }
  if (this._error) {
    return html`<div class="error">${this._error}</div>`;
  }
  return null;
}

_renderConfiguration() {
  const config = this._configuration;
  return html`
    <div class="container">
      ${this._renderGeneralSection(config)}
      ${this._renderParserSection(config)}
      ${this._renderHealthSection(config)}
    </div>
  `;
}
```

### Strategy 2: Early Returns

Reduce nesting with guard clauses and early returns.

#### Before

```javascript
// ❌ Deep nesting (complexity: 8)
function processData(data) {
  if (data) {
    if (data.isValid) {
      if (data.hasPermission) {
        if (data.items.length > 0) {
          return data.items.map(item => processItem(item));
        } else {
          return [];
        }
      } else {
        throw new Error('No permission');
      }
    } else {
      throw new Error('Invalid data');
    }
  } else {
    throw new Error('No data provided');
  }
}
```

#### After

```javascript
// ✅ Early returns with guard clauses (complexity: 4)
function processData(data) {
  if (!data) {
    throw new Error('No data provided');
  }
  if (!data.isValid) {
    throw new Error('Invalid data');
  }
  if (!data.hasPermission) {
    throw new Error('No permission');
  }
  if (data.items.length === 0) {
    return [];
  }

  return data.items.map(item => processItem(item));
}
```

### Strategy 3: Extract Boolean Logic

Simplify complex conditionals by extracting boolean expressions into well-named functions.

#### Before

```javascript
// ❌ Complex inline conditional
if (user && user.isActive && user.permissions.includes('admin') &&
    user.lastLogin && (Date.now() - user.lastLogin) < 86400000) {
  // Handle active admin
}
```

#### After

```javascript
// ✅ Extracted boolean methods
function isActiveAdmin(user) {
  return user &&
         user.isActive &&
         user.permissions.includes('admin') &&
         hasRecentLogin(user);
}

function hasRecentLogin(user) {
  if (!user.lastLogin) return false;
  const oneDayMs = 86400000;
  return (Date.now() - user.lastLogin) < oneDayMs;
}

if (isActiveAdmin(user)) {
  // Handle active admin
}
```

### Strategy 4: Extract Configuration Objects

Replace multiple parameters with configuration objects.

#### Before

```javascript
// ❌ Too many parameters (6 parameters)
function createUser(name, email, role, department, manager, startDate) {
  return {
    id: generateId(),
    name,
    email,
    role,
    department,
    manager,
    startDate,
  };
}
```

#### After

```javascript
// ✅ Configuration object (1 parameter)
function createUser(config) {
  const { name, email, role, department, manager, startDate } = config;
  return {
    id: generateId(),
    name,
    email,
    role,
    department,
    manager,
    startDate,
  };
}

// Usage
const user = createUser({
  name: 'John Doe',
  email: 'john@example.com',
  role: 'developer',
  department: 'Engineering',
  manager: 'Jane Smith',
  startDate: new Date(),
});
```

### Strategy 5: Extract Test Helpers

Move test helper functions outside describe blocks to reduce callback complexity.

#### Before

```javascript
// ❌ All functions inside describe block (too many statements)
describe('ComponentName', () => {
  let component;
  let container;

  // 10+ helper functions defined here
  function setupComponent() { /* ... */ }
  function createMockElements() { /* ... */ }
  function setupQuerySelector() { /* ... */ }
  // ... 7 more functions

  beforeEach(async () => {
    // 20+ statements for setup
    resetDevUIMocks();
    container = document.createElement('div');
    document.body.append(container);
    component = new Component();
    // ... 16 more statements
  });
});
```

#### After

```javascript
// ✅ Helper functions extracted to module level
// Test helper functions
function setupTestEnvironment() {
  resetDevUIMocks();
  const container = document.createElement('div');
  document.body.append(container);
  return container;
}

function setupComponent() {
  const component = new Component();
  component.shadowRoot = document.createElement('div');
  return component;
}

function createMockElements() {
  return {
    input: createInput(),
    button: createButton(),
    output: createOutput(),
  };
}

async function performInitialRender(container, component) {
  container.append(component);
  component.render();
  await waitForComponentUpdate(component);
}

describe('ComponentName', () => {
  let component;
  let container;

  beforeEach(async () => {
    container = setupTestEnvironment();
    component = setupComponent();
    const elements = createMockElements();
    setupQuerySelectorMock(component, elements);
    await performInitialRender(container, component);
  });

  // Tests...
});
```

## Common Refactoring Patterns

### Replace Switch with Object Lookup

```javascript
// ❌ Switch statement
function getStatusMessage(status) {
  switch (status) {
    case 'pending':
      return 'Processing...';
    case 'success':
      return 'Completed successfully';
    case 'error':
      return 'Failed to process';
    case 'cancelled':
      return 'Operation cancelled';
    default:
      return 'Unknown status';
  }
}

// ✅ Object lookup
const STATUS_MESSAGES = {
  pending: 'Processing...',
  success: 'Completed successfully',
  error: 'Failed to process',
  cancelled: 'Operation cancelled',
};

function getStatusMessage(status) {
  return STATUS_MESSAGES[status] || 'Unknown status';
}
```

### Replace Nested Ternaries with If-Else

```javascript
// ❌ Nested ternary
const message = user
  ? user.isActive
    ? user.isPremium
      ? 'Premium active user'
      : 'Active user'
    : 'Inactive user'
  : 'No user';

// ✅ Clear if-else
function getUserMessage(user) {
  if (!user) return 'No user';
  if (!user.isActive) return 'Inactive user';
  if (user.isPremium) return 'Premium active user';
  return 'Active user';
}

const message = getUserMessage(user);
```

### Split Large Functions into Pipelines

```javascript
// ❌ Large processing function
function processUserData(rawData) {
  // 20+ statements of validation, transformation, enrichment
  const validated = validateData(rawData);
  const normalized = normalizeData(validated);
  const enriched = enrichData(normalized);
  const formatted = formatData(enriched);
  return formatted;
}

// ✅ Pipeline of focused functions
const processUserData = (rawData) => {
  return [
    validateData,
    normalizeData,
    enrichData,
    formatData,
  ].reduce((data, fn) => fn(data), rawData);
};
```

## Code Organization

### Single Responsibility Principle

Each function should do one thing well:

```javascript
// ❌ Function doing too much
function saveUser(user) {
  validateUser(user);
  const normalized = normalizeUser(user);
  const saved = database.save(normalized);
  sendWelcomeEmail(saved);
  logUserCreation(saved);
  updateAnalytics(saved);
  return saved;
}

// ✅ Separate concerns
function saveUser(user) {
  validateUser(user);
  const normalized = normalizeUser(user);
  return database.save(normalized);
}

function onUserCreated(user) {
  sendWelcomeEmail(user);
  logUserCreation(user);
  updateAnalytics(user);
}
```

### DRY (Don't Repeat Yourself)

Extract duplicate code into reusable functions:

```javascript
// ❌ Duplicate validation logic
function createUser(data) {
  if (!data.email || !data.email.includes('@')) {
    throw new Error('Invalid email');
  }
  // ... create user
}

function updateUser(id, data) {
  if (!data.email || !data.email.includes('@')) {
    throw new Error('Invalid email');
  }
  // ... update user
}

// ✅ Extracted validation
function validateEmail(email) {
  if (!email || !email.includes('@')) {
    throw new Error('Invalid email');
  }
}

function createUser(data) {
  validateEmail(data.email);
  // ... create user
}

function updateUser(id, data) {
  validateEmail(data.email);
  // ... update user
}
```

## Naming Conventions

### Clear, Descriptive Names

```javascript
// ❌ Unclear names
function proc(d) {
  const r = d.map(x => x * 2);
  return r;
}

// ✅ Clear names
function processNumbers(numbers) {
  const doubled = numbers.map(num => num * 2);
  return doubled;
}
```

### Boolean Functions

```javascript
// ✅ Prefix with is, has, can, should
function isValid(data) { }
function hasPermission(user) { }
function canEdit(user, document) { }
function shouldRefresh(state) { }
```

### Function Naming

```javascript
// ✅ Verbs for actions
function calculateTotal() { }
function fetchUserData() { }
function validateInput() { }
function transformData() { }
```

## Documentation

### When to Comment

```javascript
// ✅ Explain WHY, not WHAT
// Retry with exponential backoff to handle temporary network issues
await retryOperation(fetchData, 3, 1000);

// ✅ Document complex algorithms
// Use binary search for O(log n) performance on sorted array
const index = binarySearch(sortedArray, target);

// ✅ Note non-obvious behavior
// Must clone to avoid mutating original (used by other components)
const cloned = { ...original };
```

### When NOT to Comment

```javascript
// ❌ Don't state the obvious
// Increment counter by 1
counter++;

// ❌ Don't explain bad code - refactor instead
// Complex logic to calculate price - needs refactoring
function calculatePrice() {
  // ... overly complex code
}
```

## Testing Quality

### Test Coverage

- All public functions must have tests
- Critical paths need edge case testing
- Complex logic needs thorough coverage

### Test Organization

```javascript
// ✅ Organize tests logically
describe('UserService', () => {
  describe('createUser', () => {
    it('should create user with valid data', () => { });
    it('should throw error for invalid email', () => { });
    it('should generate unique ID', () => { });
  });

  describe('updateUser', () => {
    it('should update existing user', () => { });
    it('should throw error for non-existent user', () => { });
  });
});
```

## See Also

- [JavaScript Fundamentals](javascript-fundamentals.md) - Core language patterns
- [Modern Patterns](modern-patterns.md) - Advanced JavaScript patterns
- [Async Programming](async-programming.md) - Asynchronous code quality
- [Tooling Guide](tooling-guide.md) - Linting and quality tools
