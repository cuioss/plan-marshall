# JavaScript Fundamentals

Core JavaScript patterns including ES modules, variable declarations, functions, and vanilla JavaScript preference.

## Overview

Modern JavaScript development uses ES2022+ features with a preference for vanilla JavaScript over libraries. This guide covers the fundamental patterns and conventions for writing clean, maintainable JavaScript code.

## ECMAScript Version Support

**Target**: ES2022 (ES13) and later features
**Browser Support**: Modern browsers with native ES modules
**Node.js**: Version 20.12.2 LTS or later
**Transpilation**: Babel for test environments only

## Vanilla JavaScript Preference

**Critical Rule**: Prefer vanilla JavaScript where possible: fetch instead of ajax. If it is not too complex to implement without jQuery/cash, always resort to vanilla JS.

### Why Vanilla JavaScript?

- Better performance by avoiding unnecessary library overhead
- Reduced bundle sizes and faster load times
- Native browser API usage for modern features
- Elimination of legacy dependencies

### Examples

```javascript
// ✅ Preferred: Vanilla JavaScript fetch
const response = await fetch('/api/data');
const data = await response.json();

// ❌ Avoid: jQuery ajax
$.ajax({
  url: '/api/data',
  success: (data) => { /* ... */ }
});

// ✅ Preferred: Native DOM manipulation
document.querySelector('.button').addEventListener('click', handleClick);

// ❌ Avoid: jQuery DOM manipulation
$('.button').on('click', handleClick);

// ✅ Preferred: Native element selection
const elements = document.querySelectorAll('.item');
const array = Array.from(elements);

// ❌ Avoid: jQuery selection
const elements = $('.item');

// ✅ Preferred: Native class manipulation
element.classList.add('active');
element.classList.remove('hidden');
element.classList.toggle('expanded');

// ❌ Avoid: jQuery class manipulation
$(element).addClass('active').removeClass('hidden');
```

## ES Modules

Use ES modules exclusively for all JavaScript code.

### Module Exports

```javascript
// Named exports (preferred)
export const utilityFunction = () => {
  // Implementation
};

export class ComponentClass {
  // Implementation
}

// Default exports (when appropriate)
export default class MainComponent {
  // Implementation
}

// Re-exports
export { SomeClass } from './some-module.js';
export * from './utilities.js';
```

### Import Patterns

Follow consistent import order:

```javascript
// 1. Framework imports first
import { html, css, LitElement } from 'lit';

// 2. Third-party imports
import { customElement, property } from 'lit/decorators.js';

// 3. Local imports (relative paths)
import { validateInput } from '../utilities/validation.js';
import { API_ENDPOINTS } from '../config/constants.js';

// Import specific items, avoid wildcard imports
import { debounce, throttle } from '../utilities/performance.js';
```

### Module Organization

**One module per file** for components:

```javascript
// user-profile.js
export class UserProfile {
  // Component implementation
}
```

**Utility modules** can export multiple related functions:

```javascript
// validation-utils.js
export const validateEmail = (email) => {
  // Implementation
};

export const validatePhone = (phone) => {
  // Implementation
};

export const validateRequired = (value) => {
  // Implementation
};
```

## Variable Declarations

Use `const` by default, `let` when reassignment is needed. **Never use `var`**.

### Const for Immutable Bindings

```javascript
// ✅ Preferred: const for values that don't change
const apiEndpoint = 'https://api.example.com';
const userConfig = { timeout: 5000 };
const MAX_RETRIES = 3;

// Object/array contents can still be modified
const users = [];
users.push(newUser); // Valid

const config = { timeout: 5000 };
config.retries = 3; // Valid
```

### Let for Reassignment

```javascript
// ✅ Use let when reassignment is necessary
let currentUser = null;
let retryCount = 0;
let isProcessing = false;

// Loop variables
for (let i = 0; i < items.length; i++) {
  // ...
}

// Block-scoped reassignment
if (condition) {
  let temp = processData();
  result = temp;
}
```

### Never Use Var

```javascript
// ❌ Never use var - function-scoped, hoisting issues
// var deprecatedVariable = 'avoid this';

// ✅ Use const or let instead
const properVariable = 'use this';
```

## Functions

Choose appropriate function syntax based on use case.

### Arrow Functions

Use arrow functions for utilities, callbacks, and short functions:

```javascript
// Utility functions
const processData = (data) => {
  return data.map(item => item.value);
};

// Single expression - implicit return
const double = (x) => x * 2;
const getFullName = (user) => `${user.firstName} ${user.lastName}`;

// Event handlers
const handleClick = (event) => {
  event.preventDefault();
  // Handle event
};

// Array methods
const activeUsers = users.filter(user => user.isActive);
const userNames = users.map(user => user.name);
```

### Regular Functions

Use regular functions for methods and constructors:

```javascript
// Class methods
class DataProcessor {
  constructor(options) {
    this.options = options;
  }

  processItems(items) {
    return items.filter(item => this.isValid(item));
  }

  isValid(item) {
    return item && item.value > 0;
  }
}

// Object methods when 'this' is needed
const calculator = {
  value: 0,

  add(n) {
    this.value += n;
    return this;
  },

  multiply(n) {
    this.value *= n;
    return this;
  },
};
```

### Function Parameters

For comprehensive coverage of function parameter patterns including destructuring, default parameters, and rest parameters, see [modern-patterns.md](modern-patterns.md) section "Destructuring Patterns".

## Common Patterns

### Conditional Execution

```javascript
// Optional chaining
const userName = user?.profile?.name;
const firstItem = items?.[0];
const result = obj?.method?.();

// Nullish coalescing
const timeout = options.timeout ?? 5000;
const name = user.name ?? 'Anonymous';

// Short-circuit evaluation
const value = input || defaultValue; // Falsy check
const value = input ?? defaultValue; // Null/undefined check
```

### Type Checking

```javascript
// Type checks
const isArray = Array.isArray(value);
const isObject = value !== null && typeof value === 'object';
const isFunction = typeof value === 'function';

// Instance checks
const isDate = value instanceof Date;
const isError = value instanceof Error;

// Existence checks
const exists = value !== null && value !== undefined;
const hasProperty = Object.hasOwn(obj, 'property');
```

## See Also

- [Code Quality](code-quality.md) - Complexity limits and refactoring
- [Modern Patterns](modern-patterns.md) - Advanced JavaScript patterns
- [Async Programming](async-programming.md) - Promises and async/await
- [Tooling Guide](tooling-guide.md) - ESLint and development tools
