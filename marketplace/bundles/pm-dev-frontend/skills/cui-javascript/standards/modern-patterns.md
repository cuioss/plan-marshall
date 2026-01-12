# Modern Patterns

Advanced JavaScript patterns including classes, functional programming, composition, and performance optimization.

## Overview

Modern JavaScript provides powerful patterns for building maintainable applications. This guide covers modern syntax fundamentals, object-oriented patterns, functional programming techniques, composition strategies, and performance optimizations.

## Modern Syntax Patterns

### Destructuring

Use destructuring for object and array manipulation:

```javascript
// Object destructuring
const { name, email, preferences = {} } = user;
const { theme, language } = preferences;

// Array destructuring
const [first, second, ...rest] = items;
const [head, ...tail] = sortedItems;

// Function parameter destructuring
const createConfig = ({ endpoint, timeout = 5000, retries = 3 }) => ({
  endpoint,
  timeout,
  retries,
  timestamp: Date.now(),
});

// Nested destructuring (when readable)
const {
  config: { api: { endpoint, timeout } },
  user: { name, permissions }
} = applicationState;
```

### Template Literals

Use template literals for string interpolation:

```javascript
// String interpolation
const message = `Hello, ${user.name}! You have ${messageCount} messages.`;

// Multi-line strings
const htmlTemplate = `
  <div class="user-card">
    <h2>${user.name}</h2>
    <p>${user.email}</p>
  </div>
`;

// Complex expressions
const apiUrl = `${baseUrl}/api/v${apiVersion}/users/${userId}?include=${includes.join(',')}`;

// Conditional content
const status = `User is ${user.isActive ? 'active' : 'inactive'}`;
```

### Spread and Rest Operators

Use spread and rest operators effectively:

```javascript
// Object spreading
const defaultOptions = { timeout: 5000, retries: 3 };
const customOptions = { retries: 5, cache: true };
const finalOptions = { ...defaultOptions, ...customOptions };

// Array spreading
const mergedItems = [...existingItems, ...newItems];
const clonedArray = [...originalArray];

// Rest parameters
const processItems = (primaryItem, ...additionalItems) => {
  console.log('Processing primary:', primaryItem);
  additionalItems.forEach(item => console.log('Additional:', item));
};

// Array destructuring with rest
const [head, ...tail] = items;
const [first, second, ...remaining] = sortedItems;
```

## Object Patterns

Use modern object syntax and methods:

```javascript
// Object shorthand properties
const createConfig = (endpoint, timeout, retries) => ({
  endpoint,
  timeout,
  retries,
  timestamp: Date.now(),
});

// Computed property names
const createDynamicObject = (key, value) => ({
  [key]: value,
  [`${key}Processed`]: processValue(value),
});

// Object spread for immutable updates
const updateUser = (user, updates) => ({
  ...user,
  ...updates,
  lastModified: Date.now(),
});

// Object.entries for iteration
const processConfig = (config) => {
  Object.entries(config).forEach(([key, value]) => {
    console.log(`${key}: ${value}`);
  });
};

// Object.keys, Object.values
const keys = Object.keys(config);
const values = Object.values(config);

// Object.fromEntries for transformation
const normalized = Object.fromEntries(
  Object.entries(data).map(([key, value]) => [
    key.toLowerCase(),
    value
  ])
);
```

## Array Methods

Use functional array methods:

```javascript
// Transformation chain
const processedItems = items
  .filter(item => item.isActive)
  .map(item => ({
    ...item,
    processed: true,
    timestamp: Date.now(),
  }))
  .sort((a, b) => a.priority - b.priority);

// Finding elements
const activeUser = users.find(user => user.status === 'active');
const hasAdminUser = users.some(user => user.role === 'admin');
const allValidated = users.every(user => user.isValidated);

// Aggregation with reduce
const totalValue = items.reduce((sum, item) => sum + item.value, 0);

// Grouping with reduce
const groupedByCategory = items.reduce((groups, item) => {
  const key = item.category;
  groups[key] = groups[key] || [];
  groups[key].push(item);
  return groups;
}, {});

// Flattening arrays
const flattened = nested.flat();
const deepFlattened = deeplyNested.flat(Infinity);

// Map and flatten in one step
const allTags = posts.flatMap(post => post.tags);
```

## Class Patterns

### Modern Class Syntax

Use ES2022+ class features including private fields and static members:

```javascript
class DataManager {
  // Private fields
  #privateData = new Map();
  #maxSize = 100;

  // Static properties
  static DEFAULT_CONFIG = {
    timeout: 5000,
    retries: 3,
  };

  constructor(config = {}) {
    this.config = { ...DataManager.DEFAULT_CONFIG, ...config };
    this.cache = new Map();
    this.subscribers = new Set();
  }

  // Public methods
  async getData(key) {
    if (this.cache.has(key)) {
      return this.cache.get(key);
    }

    const data = await this.#fetchData(key);
    this.cache.set(key, data);
    this.#enforceMaxSize();
    return data;
  }

  // Private methods
  async #fetchData(key) {
    const response = await fetch(`/api/data/${key}`);
    return response.json();
  }

  #enforceMaxSize() {
    if (this.cache.size > this.#maxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }

  // Getters and setters
  get size() {
    return this.cache.size;
  }

  set maxSize(value) {
    this.#maxSize = Math.max(1, value);
    this.#enforceMaxSize();
  }

  // Static methods
  static create(config) {
    return new DataManager(config);
  }
}

// Usage
const manager = DataManager.create({ timeout: 3000 });
await manager.getData('user-123');
console.log(manager.size);
```

### Class Initialization Patterns

```javascript
class Component {
  #initialized = false;

  constructor(element) {
    this.element = element;
    this.state = {};
  }

  // Lazy initialization
  async init() {
    if (this.#initialized) return;

    await this.#loadDependencies();
    this.#setupEventListeners();
    this.#initialized = true;
  }

  async #loadDependencies() {
    this.config = await fetch('/config.json').then(r => r.json());
  }

  #setupEventListeners() {
    this.element.addEventListener('click', this.handleClick.bind(this));
  }

  handleClick(event) {
    // Access this.state, this.config
  }
}
```

## Composition Patterns

Favor composition over inheritance for flexibility and reusability.

### Mixins

Create reusable behavior with mixins:

```javascript
// Event emitter mixin
const EventEmitterMixin = (Base) => class extends Base {
  constructor(...args) {
    super(...args);
    this.listeners = new Map();
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return this;
  }

  off(event, callback) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
    return this;
  }

  emit(event, data) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
    return this;
  }
};

// Disposable mixin
const DisposableMixin = (Base) => class extends Base {
  constructor(...args) {
    super(...args);
    this.#resources = [];
  }

  #resources = [];

  addResource(resource) {
    this.#resources.push(resource);
  }

  dispose() {
    this.#resources.forEach(resource => {
      if (typeof resource.dispose === 'function') {
        resource.dispose();
      }
    });
    this.#resources = [];
  }
};

// Compose mixins
class Component extends EventEmitterMixin(DisposableMixin(HTMLElement)) {
  connectedCallback() {
    this.emit('connected', { element: this });
  }

  disconnectedCallback() {
    this.dispose();
  }
}
```

### Factory Functions

Use factory functions for flexible object creation:

```javascript
// API client factory
const createApiClient = (baseUrl, options = {}) => {
  const defaultOptions = {
    timeout: 5000,
    retries: 3,
    headers: { 'Content-Type': 'application/json' },
  };

  const config = { ...defaultOptions, ...options };

  const request = async (endpoint, requestOptions) => {
    const url = `${baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...config,
      ...requestOptions,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  };

  return {
    get: (endpoint) => request(endpoint, { method: 'GET' }),

    post: (endpoint, data) => request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

    put: (endpoint, data) => request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

    delete: (endpoint) => request(endpoint, { method: 'DELETE' }),
  };
};

// Usage
const api = createApiClient('https://api.example.com', {
  timeout: 3000,
  headers: {
    'Authorization': 'Bearer token',
    'Content-Type': 'application/json',
  },
});

const user = await api.get('/users/123');
await api.post('/users', { name: 'John' });
```

### Module Pattern

Create encapsulated modules with public APIs:

```javascript
const CacheManager = (() => {
  // Private state
  const cache = new Map();
  const stats = { hits: 0, misses: 0 };

  // Private functions
  const isExpired = (entry) => {
    return Date.now() > entry.expiresAt;
  };

  const cleanup = () => {
    for (const [key, entry] of cache.entries()) {
      if (isExpired(entry)) {
        cache.delete(key);
      }
    }
  };

  // Public API
  return {
    set(key, value, ttl = 60000) {
      cache.set(key, {
        value,
        expiresAt: Date.now() + ttl,
      });
    },

    get(key) {
      const entry = cache.get(key);

      if (!entry) {
        stats.misses++;
        return null;
      }

      if (isExpired(entry)) {
        cache.delete(key);
        stats.misses++;
        return null;
      }

      stats.hits++;
      return entry.value;
    },

    clear() {
      cache.clear();
      stats.hits = 0;
      stats.misses = 0;
    },

    getStats() {
      return { ...stats, size: cache.size };
    },

    startCleanup(interval = 60000) {
      return setInterval(cleanup, interval);
    },
  };
})();

// Usage
CacheManager.set('user', userData, 120000);
const user = CacheManager.get('user');
console.log(CacheManager.getStats());
```

## Functional Programming

### Pure Functions

Write pure functions whenever possible - same input always produces same output, no side effects:

```javascript
// ✅ Pure functions
const calculateTax = (amount, rate) => amount * rate;

const formatCurrency = (amount, currency = 'USD') =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);

const normalizeText = (text) =>
  text.trim().toLowerCase().replace(/\s+/g, ' ');

// ❌ Impure functions (side effects)
let total = 0;
const addToTotal = (amount) => {
  total += amount; // Mutates external state
  return total;
};
```

### Higher-Order Functions

Functions that take or return functions:

```javascript
// Function that returns a function
const createMultiplier = (factor) => {
  return (num) => num * factor;
};

const double = createMultiplier(2);
const triple = createMultiplier(3);

console.log(double(5)); // 10
console.log(triple(5)); // 15

// Function that takes a function
const withLogging = (fn) => {
  return (...args) => {
    console.log(`Calling with args:`, args);
    const result = fn(...args);
    console.log(`Result:`, result);
    return result;
  };
};

const add = (a, b) => a + b;
const loggedAdd = withLogging(add);
loggedAdd(2, 3); // Logs execution and result

// Composition
const compose = (...fns) => (value) =>
  fns.reduceRight((acc, fn) => fn(acc), value);

const pipe = (...fns) => (value) =>
  fns.reduce((acc, fn) => fn(acc), value);

// Usage
const processUser = pipe(
  normalizeEmail,
  validateEmail,
  enrichUserData,
  formatUserObject
);

const user = processUser(rawUserData);
```

### Function Currying

Transform multi-parameter functions into sequences of single-parameter functions:

```javascript
// Curried function
const multiply = (a) => (b) => a * b;

const double = multiply(2);
const triple = multiply(3);

console.log(double(5)); // 10
console.log(triple(5)); // 15

// Practical example
const createElement = (tag) => (className) => (content) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content) element.textContent = content;
  return element;
};

const createDiv = createElement('div');
const createCard = createDiv('card');
const createUserCard = createCard('User Profile');

// Partial application
const createButton = (label, onClick) => {
  const button = document.createElement('button');
  button.textContent = label;
  button.addEventListener('click', onClick);
  return button;
};

const createSaveButton = (onClick) => createButton('Save', onClick);
const createCancelButton = (onClick) => createButton('Cancel', onClick);
```

### Immutability

Always return new objects/arrays instead of mutating:

```javascript
// ✅ Immutable updates
const updateUser = (user, updates) => ({
  ...user,
  ...updates,
  lastModified: Date.now(),
});

const addItem = (items, newItem) => [...items, newItem];

const removeItem = (items, index) => [
  ...items.slice(0, index),
  ...items.slice(index + 1),
];

const updateItem = (items, index, updates) =>
  items.map((item, i) => (i === index ? { ...item, ...updates } : item));

// ❌ Mutable operations (avoid)
const badUpdate = (user, updates) => {
  user.name = updates.name; // Mutates original
  return user;
};
```

## Performance Patterns

### Memoization

Cache expensive function results:

```javascript
// Simple memoization
const memoize = (fn) => {
  const cache = new Map();

  return (...args) => {
    const key = JSON.stringify(args);

    if (cache.has(key)) {
      return cache.get(key);
    }

    const result = fn(...args);
    cache.set(key, result);
    return result;
  };
};

// Usage
const expensiveCalculation = (n) => {
  // Complex calculation
  return n * n * n;
};

const memoizedCalc = memoize(expensiveCalculation);

// First call - calculates
console.log(memoizedCalc(5)); // Slow

// Second call - cached
console.log(memoizedCalc(5)); // Fast
```

### Lazy Evaluation

Delay execution until needed:

```javascript
// Lazy property
class DataLoader {
  #dataCache = null;

  get data() {
    if (this.#dataCache === null) {
      this.#dataCache = this.#loadData();
    }
    return this.#dataCache;
  }

  #loadData() {
    // Expensive operation
    return fetch('/api/data').then(r => r.json());
  }
}

// Lazy sequence
function* lazyRange(start, end) {
  for (let i = start; i <= end; i++) {
    yield i;
  }
}

const numbers = lazyRange(1, 1000000);
// No computation until iteration
for (const num of numbers) {
  if (num > 10) break; // Only generates 10 numbers
}
```

### Debouncing and Throttling

Control function execution frequency:

```javascript
// Debounce - wait for pause in calls
const debounce = (fn, delay) => {
  let timeoutId;

  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
};

// Throttle - limit execution rate
const throttle = (fn, limit) => {
  let inThrottle;

  return (...args) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

// Usage
const handleSearch = debounce((query) => {
  // API call
}, 300);

const handleScroll = throttle(() => {
  // Update UI
}, 100);

// Input event
input.addEventListener('input', (e) => {
  handleSearch(e.target.value);
});

// Scroll event
window.addEventListener('scroll', handleScroll);
```

## Advanced Patterns

### Observer Pattern

Implement publish-subscribe:

```javascript
class EventBus {
  #listeners = new Map();

  on(event, callback) {
    if (!this.#listeners.has(event)) {
      this.#listeners.set(event, new Set());
    }
    this.#listeners.get(event).add(callback);

    // Return unsubscribe function
    return () => this.off(event, callback);
  }

  off(event, callback) {
    const callbacks = this.#listeners.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }

  emit(event, data) {
    const callbacks = this.#listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }

  once(event, callback) {
    const unsubscribe = this.on(event, (data) => {
      callback(data);
      unsubscribe();
    });
    return unsubscribe;
  }
}

// Usage
const bus = new EventBus();

const unsubscribe = bus.on('user:login', (user) => {
  console.log('User logged in:', user);
});

bus.emit('user:login', { id: 1, name: 'John' });
unsubscribe();
```

### Builder Pattern

Construct complex objects step by step:

```javascript
class QueryBuilder {
  #query = {
    select: [],
    from: null,
    where: [],
    orderBy: [],
    limit: null,
  };

  select(...fields) {
    this.#query.select.push(...fields);
    return this;
  }

  from(table) {
    this.#query.from = table;
    return this;
  }

  where(condition) {
    this.#query.where.push(condition);
    return this;
  }

  orderBy(field, direction = 'ASC') {
    this.#query.orderBy.push({ field, direction });
    return this;
  }

  limit(count) {
    this.#query.limit = count;
    return this;
  }

  build() {
    return { ...this.#query };
  }
}

// Usage
const query = new QueryBuilder()
  .select('id', 'name', 'email')
  .from('users')
  .where('isActive = true')
  .where('role = "admin"')
  .orderBy('name', 'ASC')
  .limit(10)
  .build();
```

## See Also

- [JavaScript Fundamentals](javascript-fundamentals.md) - Core patterns
- [Code Quality](code-quality.md) - Refactoring and maintainability
- [Async Programming](async-programming.md) - Asynchronous patterns
- [Tooling Guide](tooling-guide.md) - Development tools
