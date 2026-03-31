# Async Programming

Promises, async/await patterns, error handling, and concurrent operations for asynchronous JavaScript.

## Overview

Modern JavaScript uses Promises and async/await for asynchronous operations. This guide covers best practices for async programming, error handling strategies, and utilities for managing concurrent operations.

## Async/Await Patterns

### Basic Async Functions

Use async/await for clean, readable asynchronous code:

```javascript
// Async function with error bubbling
const fetchUserData = async (userId) => {
  const response = await fetch(`/api/users/${userId}`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return await response.json();
};

// Usage - let errors bubble up
try {
  const user = await fetchUserData(123);
  console.log(user);
} catch (error) {
  console.error('Failed to fetch user:', error);
}
```

### When to Catch Errors

Let errors bubble up by default. Only catch to add meaningful context or transform errors:

```javascript
// Preferred: Catch to add context
const fetchUserWithContext = async (userId) => {
  try {
    const response = await fetch(`/api/users/${userId}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    throw new Error(`Failed to fetch user ${userId}: ${error.message}`, {
      cause: error,
    });
  }
};
```

### Sequential Operations

Use await for operations that must run in sequence:

```javascript
const processUserWorkflow = async (userId) => {
  const user = await fetchUser(userId);
  const preferences = await fetchPreferences(user.id);
  return await applySettings(user, preferences);
};
```

### Concurrent Operations

Use Promise.all for independent operations that can run in parallel:

```javascript
// Concurrent with destructuring
const loadUserDashboard = async (userId) => {
  const [user, posts, notifications, settings] = await Promise.all([
    fetchUser(userId),
    fetchUserPosts(userId),
    fetchNotifications(userId),
    fetchSettings(userId),
  ]);

  return { user, posts, notifications, settings };
};
```

### Handling Partial Failures

Use Promise.allSettled for operations where some can fail:

```javascript
const fetchMultipleResourcesSafely = async (urls) => {
  const results = await Promise.allSettled(
    urls.map(async (url) => {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
  );

  const successful = results
    .filter(result => result.status === 'fulfilled')
    .map(result => result.value);

  const failed = results
    .filter(result => result.status === 'rejected')
    .map((result, index) => ({
      url: urls[index],
      error: result.reason
    }));

  if (failed.length > 0) {
    console.warn(`${failed.length} requests failed:`, failed);
  }

  return { successful, failed };
};
```

### Timeout with Promise.race

Use Promise.race for timeout or fastest response:

```javascript
// Generic timeout wrapper
const withTimeout = (promise, timeoutMs) => {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Operation timed out')), timeoutMs)
    ),
  ]);
};

// Usage
const data = await withTimeout(fetch('/api/data'), 5000);
```

## Error Handling

### Error Handling Strategies

Define custom error classes (e.g., `NetworkError`, `ValidationError`) with contextual fields (`url`, `status`, `field`) when you need to distinguish error types programmatically.

**Strategy 1: Let errors bubble up** (preferred):

```javascript
const validateAndSave = async (data) => {
  validateData(data); // Let ValidationError bubble up
  return await saveData(data); // Let NetworkError bubble up
};
```

**Strategy 2: Handle specific errors, rethrow others**:

```javascript
const saveWithRecovery = async (data) => {
  try {
    return await saveData(data);
  } catch (error) {
    if (error instanceof NetworkError && error.status >= 500) {
      console.warn(`Server error (${error.status}), retrying...`);
      await new Promise(resolve => setTimeout(resolve, 1000));
      return await saveData(data);
    }
    throw error; // Let other errors bubble up
  }
};
```

Use Strategy 1 by default. Use Strategy 2 when you need recovery logic or must add context before rethrowing.

## Promise Utilities

### Retry with Exponential Backoff

```javascript
const retryOperation = async (operation, maxRetries = 3, delay = 1000) => {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === maxRetries) throw error;
      await new Promise(resolve => setTimeout(resolve, delay));
      delay *= 2;
    }
  }
};
```

### Batch Processing with Concurrency Limit

```javascript
const parallelLimit = async (items, limit, asyncFn) => {
  const results = [];
  const executing = [];

  for (const item of items) {
    const promise = asyncFn(item).then(result => {
      executing.splice(executing.indexOf(promise), 1);
      return result;
    });
    results.push(promise);
    executing.push(promise);

    if (executing.length >= limit) await Promise.race(executing);
  }

  return Promise.all(results);
};
```

## Promise.withResolvers (ES2024)

Creates a deferred promise without the executor callback pattern:

```javascript
// Preferred: ES2024: Promise.withResolvers()
const { promise, resolve, reject } = Promise.withResolvers();

// Useful when resolve/reject must be called outside the executor
element.addEventListener('load', () => resolve(element));
element.addEventListener('error', () => reject(new Error('Load failed')));

const result = await promise;
```

## AbortController

Use `AbortController` to cancel fetch requests, clean up event listeners, and manage component lifecycles:

```javascript
// Cancel a fetch request
const controller = new AbortController();

const fetchData = async (url) => {
  const response = await fetch(url, { signal: controller.signal });
  return response.json();
};

// Cancel after timeout or user action
setTimeout(() => controller.abort(), 5000);
cancelButton.addEventListener('click', () => controller.abort());

// Handle cancellation
try {
  const data = await fetchData('/api/data');
} catch (error) {
  if (error.name === 'AbortError') {
    console.log('Request was cancelled');
  } else {
    throw error;
  }
}
```

### Component Cleanup Pattern

```javascript
class DataFetcher {
  #controller = null;

  async load(url) {
    // Cancel any in-flight request
    this.#controller?.abort();
    this.#controller = new AbortController();

    const response = await fetch(url, { signal: this.#controller.signal });
    return response.json();
  }

  destroy() {
    this.#controller?.abort();
  }
}
```

## Advanced Concepts

## Common Pitfalls

- **Unnecessary try-catch**: Don't catch just to rethrow — let errors bubble naturally
- **Missing await**: Forgetting `await` returns a Promise instead of the resolved value
- **Sequential when parallel is possible**: Use `Promise.all()` for independent operations instead of sequential `await`
- **Await in loops**: Use `Promise.all(items.map(...))` instead of `for...of` with `await` when items are independent

## See Also

- [JavaScript Fundamentals](javascript-fundamentals.md) - Core language features
- [Code Quality](code-quality.md) - Complexity and error handling
- [Modern Patterns](modern-patterns.md) - Advanced patterns
- `pm-dev-frontend:js-enforce-eslint` - ESLint async rules
