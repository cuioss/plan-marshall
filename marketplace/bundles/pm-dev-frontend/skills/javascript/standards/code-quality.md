# Code Quality

For general code quality principles (SRP, CQS, complexity thresholds, refactoring triggers), see `plan-marshall:dev-general-code-quality`. This document covers JavaScript-specific complexity limits, ESLint mappings, and JS refactoring patterns.

## JavaScript Complexity Limits

Beyond the general thresholds in `plan-marshall:dev-general-code-quality`, JavaScript enforces:

- **Statement Count**: Maximum 20 statements per function
- **Parameter Count**: Maximum 5 parameters per function (ESLint `max-params`)

## JavaScript Refactoring Patterns

### Strategy 1: Extract Methods

Break down large functions into focused, single-purpose functions. Move state checks, rendering logic, or data transformations into named helper methods.

```javascript
// ❌ Monolithic function with 20+ statements
_doRender() {
  if (this._loading) return html`<div class="loading">Loading...</div>`;
  if (this._error) return html`<div class="error">${this._error}</div>`;
  // ... many more lines of rendering logic
}

// ✅ Decomposed into helpers
_doRender() {
  return this._renderLoadingOrError() ?? this._renderConfiguration();
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

Replace multiple parameters with a single options object when a function exceeds the 5-parameter limit.

```javascript
// ❌ Too many parameters
function createUser(name, email, role, department, manager, startDate) { ... }

// ✅ Configuration object with destructuring
function createUser({ name, email, role, department, manager, startDate }) {
  return { id: generateId(), name, email, role, department, manager, startDate };
}
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

## See Also

- `plan-marshall:dev-general-code-quality` - General code quality principles (SRP, CQS, complexity, error handling)
- [JavaScript Fundamentals](javascript-fundamentals.md) - Core language patterns
- [Modern Patterns](modern-patterns.md) - Advanced JavaScript patterns
- [Async Programming](async-programming.md) - Asynchronous code quality and error handling patterns
- `pm-dev-frontend:js-enforce-eslint` - Linting and quality tools
