# Modern Patterns

Modern JavaScript syntax patterns, functional programming techniques, and performance optimizations.

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
```

### Spread and Rest Operators

```javascript
// Object spreading
const defaultOptions = { timeout: 5000, retries: 3 };
const finalOptions = { ...defaultOptions, ...customOptions };

// Array spreading (shallow copy only — use structuredClone() for deep copies)
const mergedItems = [...existingItems, ...newItems];
const clonedArray = [...originalArray];

// Rest parameters
const processItems = (primaryItem, ...additionalItems) => {
  additionalItems.forEach(item => console.log('Additional:', item));
};
```

## Object Patterns

Use modern object syntax and methods:

```javascript
// Object shorthand properties
const createConfig = (endpoint, timeout, retries) => ({
  endpoint, timeout, retries, timestamp: Date.now(),
});

// Computed property names
const createDynamicObject = (key, value) => ({
  [key]: value,
  [`${key}Processed`]: processValue(value),
});

// Object.entries, Object.keys, Object.values
Object.entries(config).forEach(([key, value]) => {
  console.log(`${key}: ${value}`);
});
const keys = Object.keys(config);
const values = Object.values(config);

// Object.fromEntries for transformation
const normalized = Object.fromEntries(
  Object.entries(data).map(([key, value]) => [key.toLowerCase(), value])
);
```

## Array Methods

Use functional array methods:

```javascript
// Transformation chain
const processedItems = items
  .filter(item => item.isActive)
  .map(item => ({ ...item, processed: true, timestamp: Date.now() }))
  .sort((a, b) => a.priority - b.priority);

// Finding elements
const activeUser = users.find(user => user.status === 'active');
const hasAdminUser = users.some(user => user.role === 'admin');
const allValidated = users.every(user => user.isValidated);

// Aggregation with reduce
const totalValue = items.reduce((sum, item) => sum + item.value, 0);

// Grouping (ES2024 — prefer Object.groupBy over manual reduce)
const groupedByCategory = Object.groupBy(items, item => item.category);

// Flattening
const flattened = nested.flat();
const allTags = posts.flatMap(post => post.tags);
```

### Immutable Array Methods (ES2023+)

Prefer these over manual spread patterns — they return new arrays without mutating the original:

```javascript
const items = [3, 1, 4, 1, 5];

// Preferred: ES2023: toSorted(), toReversed(), toSpliced(), with()
const sorted = items.toSorted((a, b) => a - b);    // [1, 1, 3, 4, 5]
const reversed = items.toReversed();                 // [5, 1, 4, 1, 3]
const spliced = items.toSpliced(1, 2, 9);           // [3, 9, 1, 5]
const replaced = items.with(2, 99);                  // [3, 1, 99, 1, 5]

// Original is unchanged
console.log(items); // [3, 1, 4, 1, 5]

// Avoid: mutating originals or manual spread patterns
// items.sort(), items.reverse(), items.splice()
// [...items.slice(0, index), ...items.slice(index + 1)]
```

### Set Methods

Native set operations (finalized in ES2025, supported in all modern browsers):

```javascript
const frontend = new Set(['js', 'css', 'html']);
const backend = new Set(['js', 'python', 'go']);

frontend.union(backend);              // Set {'js', 'css', 'html', 'python', 'go'}
frontend.intersection(backend);       // Set {'js'}
frontend.difference(backend);         // Set {'css', 'html'}
frontend.symmetricDifference(backend); // Set {'css', 'html', 'python', 'go'}
frontend.isSubsetOf(backend);         // false
frontend.isSupersetOf(backend);       // false
```

## Class Patterns

Use ES2022+ class features including private fields and static members:

```javascript
class DataManager {
  #cache = new Map();
  #maxSize = 100;

  static DEFAULT_CONFIG = { timeout: 5000, retries: 3 };

  constructor(config = {}) {
    this.config = { ...DataManager.DEFAULT_CONFIG, ...config };
  }

  async getData(key) {
    if (this.#cache.has(key)) return this.#cache.get(key);
    const data = await this.#fetchData(key);
    this.#cache.set(key, data);
    return data;
  }

  async #fetchData(key) {
    const response = await fetch(`/api/data/${key}`);
    return response.json();
  }

  get size() { return this.#cache.size; }

  set maxSize(value) { this.#maxSize = Math.max(1, value); }

  static create(config) { return new DataManager(config); }
}
```

## Composition Patterns

Favor composition over inheritance for flexibility and reusability.

### Mixins

```javascript
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

  emit(event, data) {
    const callbacks = this.listeners.get(event);
    if (callbacks) callbacks.forEach(cb => cb(data));
    return this;
  }
};

// Compose mixins
class Component extends EventEmitterMixin(HTMLElement) {
  connectedCallback() {
    this.emit('connected', { element: this });
  }
}
```

### Factory Functions

```javascript
const createApiClient = (baseUrl, options = {}) => {
  const config = { timeout: 5000, retries: 3, ...options };

  const request = async (endpoint, requestOptions) => {
    const response = await fetch(`${baseUrl}${endpoint}`, { ...config, ...requestOptions });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    return response.json();
  };

  return {
    get: (endpoint) => request(endpoint, { method: 'GET' }),
    post: (endpoint, data) => request(endpoint, { method: 'POST', body: JSON.stringify(data) }),
    put: (endpoint, data) => request(endpoint, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (endpoint) => request(endpoint, { method: 'DELETE' }),
  };
};
```

## Functional Programming

Favor pure functions (same input → same output, no side effects) wherever possible.

### Higher-Order Functions and Currying

```javascript
// Currying - function that returns a function
const createMultiplier = (factor) => (num) => num * factor;
const double = createMultiplier(2);
const triple = createMultiplier(3);

// Decorator pattern
const withLogging = (fn) => (...args) => {
  console.log(`Calling with args:`, args);
  const result = fn(...args);
  console.log(`Result:`, result);
  return result;
};

// Composition utilities
const compose = (...fns) => (value) =>
  fns.reduceRight((acc, fn) => fn(acc), value);

const pipe = (...fns) => (value) =>
  fns.reduce((acc, fn) => fn(acc), value);

const processUser = pipe(normalizeEmail, validateEmail, enrichUserData, formatUserObject);

// Practical currying
const createElement = (tag) => (className) => (content) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content) element.textContent = content;
  return element;
};
const createDiv = createElement('div');
const createCard = createDiv('card');
```

### Immutability

Always return new objects/arrays instead of mutating. Use ES2023+ immutable array methods where available:

```javascript
const updateUser = (user, updates) => ({
  ...user, ...updates, lastModified: Date.now(),
});

const addItem = (items, newItem) => [...items, newItem];

// Preferred: ES2023: use toSpliced() and with() instead of manual spread
const removeItem = (items, index) => items.toSpliced(index, 1);

const updateItem = (items, index, updates) =>
  items.with(index, { ...items[index], ...updates });
```

### Deep Cloning

Use `structuredClone()` for deep copies instead of `JSON.parse(JSON.stringify())` or manual spread:

```javascript
const original = { name: 'Alice', tags: ['admin'], meta: { created: new Date() } };

// Preferred: structuredClone — handles nested objects, Date, Map, Set, ArrayBuffer
const deep = structuredClone(original);
deep.tags.push('editor'); // original.tags unchanged

// Avoid: loses Date objects, fails on circular references
// const broken = JSON.parse(JSON.stringify(original));

// Spread is fine for shallow copies only
const shallow = { ...original };
```

## Performance Patterns

### Debouncing and Throttling

```javascript
const debounce = (fn, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
};

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

const handleSearch = debounce((query) => { /* API call */ }, 300);
const handleScroll = throttle(() => { /* Update UI */ }, 100);
```

## See Also

- [JavaScript Fundamentals](javascript-fundamentals.md) - Core patterns
- [Code Quality](code-quality.md) - Refactoring and maintainability
- [Async Programming](async-programming.md) - Asynchronous patterns
- `pm-dev-frontend:lint-config` - ESLint and development tools
