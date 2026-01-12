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

**Preferred**: Let errors bubble up naturally:

```javascript
// ✅ Let errors bubble up to caller
const fetchAndProcessData = async (url) => {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  return processData(data);
};
```

**Alternative**: Catch only to add meaningful context or transform errors:

```javascript
// ✅ Catch to add context
const fetchUserWithContext = async (userId) => {
  try {
    const response = await fetch(`/api/users/${userId}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    // Add meaningful context
    throw new Error(`Failed to fetch user ${userId}: ${error.message}`, {
      cause: error,
      userId,
    });
  }
};
```

### Sequential Operations

Use await for operations that must run in sequence:

```javascript
// Sequential processing
const processUserWorkflow = async (userId) => {
  const user = await fetchUser(userId);
  const preferences = await fetchPreferences(user.id);
  const settings = await applySettings(user, preferences);
  return settings;
};

// Processing array items sequentially
const processItemsSequentially = async (items) => {
  const results = [];

  for (const item of items) {
    const result = await processItem(item);
    results.push(result);
  }

  return results;
};
```

### Concurrent Operations

Use Promise.all for independent operations that can run in parallel:

```javascript
// Concurrent operations with Promise.all
const fetchMultipleResources = async (urls) => {
  const responses = await Promise.all(
    urls.map(url => fetch(url))
  );

  // Check all responses succeeded
  responses.forEach(response => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  });

  const data = await Promise.all(
    responses.map(response => response.json())
  );

  return data;
};

// Concurrent with different operations
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
// Handle partial failures gracefully
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

### Race Conditions

Use Promise.race for timeout or fastest response:

```javascript
// Race between operation and timeout
const fetchWithTimeout = async (url, timeoutMs = 5000) => {
  const fetchPromise = fetch(url);

  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Request timeout')), timeoutMs);
  });

  const response = await Promise.race([fetchPromise, timeoutPromise]);
  return response.json();
};

// Race between multiple endpoints
const fetchFromFastestEndpoint = async (urls) => {
  const fetchPromises = urls.map(url =>
    fetch(url).then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
  );

  return await Promise.race(fetchPromises);
};
```

## Error Handling

### Custom Error Classes

Define specific error types for different error conditions:

```javascript
// Custom error classes
class ValidationError extends Error {
  constructor(field, value, message) {
    super(message);
    this.name = 'ValidationError';
    this.field = field;
    this.value = value;
  }
}

class NetworkError extends Error {
  constructor(url, status, message) {
    super(message);
    this.name = 'NetworkError';
    this.url = url;
    this.status = status;
  }
}

class AuthenticationError extends Error {
  constructor(message, credentials) {
    super(message);
    this.name = 'AuthenticationError';
    this.credentials = credentials;
  }
}

// Usage
const validateAndFetchUser = async (userId) => {
  if (!userId || userId <= 0) {
    throw new ValidationError('userId', userId, 'User ID must be a positive number');
  }

  const response = await fetch(`/api/users/${userId}`);

  if (response.status === 401) {
    throw new AuthenticationError('User not authenticated');
  }

  if (!response.ok) {
    throw new NetworkError(
      `/api/users/${userId}`,
      response.status,
      `Failed to fetch user: ${response.statusText}`
    );
  }

  return response.json();
};
```

### Error Handling Strategies

**Strategy 1**: Let errors bubble up (preferred):

```javascript
// ✅ Let errors bubble up to caller
const validateAndSave = async (data) => {
  validateData(data); // Let ValidationError bubble up
  return await saveData(data); // Let NetworkError bubble up
};
```

**Strategy 2**: Handle specific errors, rethrow others:

```javascript
// ✅ Handle specific errors meaningfully
const validateAndSaveWithRecovery = async (data) => {
  try {
    validateData(data);
    return await saveData(data);
  } catch (error) {
    if (error instanceof ValidationError) {
      // Transform validation errors into user-friendly format
      throw new Error(`Invalid ${error.field}: ${error.message}`, {
        cause: error,
        code: 'VALIDATION_FAILED'
      });
    }

    if (error instanceof NetworkError && error.status >= 500) {
      // Retry server errors
      console.warn(`Server error (${error.status}), retrying...`);
      await new Promise(resolve => setTimeout(resolve, 1000));
      return await saveData(data);
    }

    // Let other errors bubble up
    throw error;
  }
};
```

**Strategy 3**: Result pattern (avoid throwing):

```javascript
// Return result object instead of throwing
const validateAndSaveResult = async (data) => {
  try {
    validateData(data);
    const result = await saveData(data);
    return { success: true, data: result };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      type: error.constructor.name
    };
  }
};

// Usage
const result = await validateAndSaveResult(userData);
if (result.success) {
  console.log('Saved:', result.data);
} else {
  console.error('Failed:', result.error);
}
```

## Promise Utilities

### Timeout Wrapper

Wrap promises with timeout functionality:

```javascript
const withTimeout = (promise, timeoutMs) => {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Operation timed out')), timeoutMs)
    ),
  ]);
};

// Usage
const data = await withTimeout(
  fetch('/api/data'),
  5000
);
```

### Retry Logic

Implement retry with exponential backoff:

```javascript
// Retry operation - legitimate use of catch
const retryOperation = async (operation, maxRetries = 3, delay = 1000) => {
  let lastError;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries) {
        throw error; // Final attempt failed
      }

      console.warn(`Attempt ${attempt} failed, retrying in ${delay}ms:`, error.message);
      await new Promise(resolve => setTimeout(resolve, delay));
      delay *= 2; // Exponential backoff
    }
  }

  throw lastError;
};

// Usage
const fetchData = await retryOperation(
  () => fetch('/api/data').then(r => r.json()),
  3,
  1000
);
```

### Batch Processing

Process items in batches with concurrency limit:

```javascript
const processBatch = async (items, batchSize, processFn) => {
  const results = [];

  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);
    const batchResults = await Promise.all(
      batch.map(item => processFn(item))
    );
    results.push(...batchResults);
  }

  return results;
};

// Usage
const processedUsers = await processBatch(
  userIds,
  10,
  async (userId) => await fetchAndProcessUser(userId)
);
```

### Parallel Execution with Limit

Control concurrency for resource-intensive operations:

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

    if (executing.length >= limit) {
      await Promise.race(executing);
    }
  }

  return Promise.all(results);
};

// Usage - limit to 5 concurrent requests
const data = await parallelLimit(
  urls,
  5,
  async (url) => {
    const response = await fetch(url);
    return response.json();
  }
);
```

## Advanced Patterns

### Queue System

Implement a promise-based queue:

```javascript
class AsyncQueue {
  #queue = [];
  #processing = false;

  async add(asyncFn) {
    return new Promise((resolve, reject) => {
      this.#queue.push({ asyncFn, resolve, reject });
      this.#process();
    });
  }

  async #process() {
    if (this.#processing || this.#queue.length === 0) {
      return;
    }

    this.#processing = true;

    while (this.#queue.length > 0) {
      const { asyncFn, resolve, reject } = this.#queue.shift();

      try {
        const result = await asyncFn();
        resolve(result);
      } catch (error) {
        reject(error);
      }
    }

    this.#processing = false;
  }
}

// Usage
const queue = new AsyncQueue();

const result1 = queue.add(() => fetch('/api/data1').then(r => r.json()));
const result2 = queue.add(() => fetch('/api/data2').then(r => r.json()));

const [data1, data2] = await Promise.all([result1, result2]);
```

### Cancellable Promises

Implement cancellable async operations with AbortController:

```javascript
const fetchWithCancel = (url) => {
  const controller = new AbortController();

  const promise = fetch(url, { signal: controller.signal })
    .then(response => response.json());

  return {
    promise,
    cancel: () => controller.abort(),
  };
};

// Usage
const { promise, cancel } = fetchWithCancel('/api/data');

// Cancel after 5 seconds
setTimeout(cancel, 5000);

try {
  const data = await promise;
  console.log(data);
} catch (error) {
  if (error.name === 'AbortError') {
    console.log('Request cancelled');
  } else {
    console.error('Request failed:', error);
  }
}
```

### Async Generators

Use async generators for streaming data:

```javascript
// Async generator for paginated API
async function* fetchAllPages(endpoint) {
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const response = await fetch(`${endpoint}?page=${page}`);
    const data = await response.json();

    yield data.items;

    hasMore = data.hasNextPage;
    page++;
  }
}

// Usage
for await (const items of fetchAllPages('/api/users')) {
  console.log('Batch:', items);
  processItems(items);
}

// Transform with async generator
async function* transformStream(source, transformFn) {
  for await (const item of source) {
    yield await transformFn(item);
  }
}

// Chain async generators
const allUsers = fetchAllPages('/api/users');
const enrichedUsers = transformStream(allUsers, enrichUserData);

for await (const user of enrichedUsers) {
  console.log(user);
}
```

## Common Pitfalls

### Avoid: Unnecessary Try-Catch

```javascript
// ❌ Unnecessary catch that just rethrows
const fetchData = async () => {
  try {
    const response = await fetch('/api/data');
    return response.json();
  } catch (error) {
    throw error; // Useless - just let it bubble
  }
};

// ✅ Let error bubble naturally
const fetchData = async () => {
  const response = await fetch('/api/data');
  return response.json();
};
```

### Avoid: Missing Await

```javascript
// ❌ Forgot await - returns Promise
const getData = async () => {
  const data = fetch('/api/data'); // Missing await!
  return data.results; // Undefined
};

// ✅ Proper await usage
const getData = async () => {
  const response = await fetch('/api/data');
  const data = await response.json();
  return data.results;
};
```

### Avoid: Sequential When Parallel Possible

```javascript
// ❌ Unnecessary sequential execution
const loadData = async () => {
  const users = await fetchUsers();
  const posts = await fetchPosts();
  const comments = await fetchComments();
  return { users, posts, comments };
};

// ✅ Parallel execution
const loadData = async () => {
  const [users, posts, comments] = await Promise.all([
    fetchUsers(),
    fetchPosts(),
    fetchComments(),
  ]);
  return { users, posts, comments };
};
```

## See Also

- [JavaScript Fundamentals](javascript-fundamentals.md) - Core language features
- [Code Quality](code-quality.md) - Complexity and error handling
- [Modern Patterns](modern-patterns.md) - Advanced patterns
- [Tooling Guide](tooling-guide.md) - ESLint async rules
