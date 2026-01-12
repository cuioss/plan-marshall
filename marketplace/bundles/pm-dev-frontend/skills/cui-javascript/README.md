# cui-javascript

Core JavaScript development standards for CUI projects.

## Description

This skill provides comprehensive JavaScript development standards covering ES2022+ features, code quality practices, modern patterns, async programming, and tooling configuration. It focuses on vanilla JavaScript with preference for native APIs, maintaining code quality through complexity limits, and using modern ECMAScript features effectively.

## What's Included

- **JavaScript Fundamentals** - ES modules, const/let best practices, function patterns, vanilla JS preference
- **Code Quality** - Complexity limits, refactoring strategies, maintainable code organization
- **Modern Patterns** - Destructuring, template literals, spread/rest operators, functional methods
- **Async Programming** - Promises, async/await, error handling, concurrent operations
- **Tooling Guide** - ESLint, Prettier, npm scripts, IDE integration

## Key Standards

### Variables
- Use `const` by default, `let` when reassignment needed
- Never use `var`
- Block-scoped declarations

### Functions
- Max 15 cyclomatic complexity
- Max 20 statements per function
- Arrow functions for callbacks and short functions
- Regular functions for methods and constructors

### Modules
- ES modules (import/export) exclusively
- Named exports preferred over default exports
- One module per file for components

### Vanilla JavaScript
- Prefer native `fetch` over axios/ajax
- Use DOM methods directly over jQuery
- Leverage browser APIs before adding dependencies

### Async Operations
- async/await for sequential operations
- Promises for parallel operations (Promise.all)
- Proper error handling with try/catch

## Usage Examples

### When to Activate

Activate this skill when:
- Writing new JavaScript code
- Refactoring existing JavaScript
- Reviewing JavaScript code
- Setting up JavaScript tooling
- Implementing async operations
- Migrating to modern JavaScript

### Example Workflow

1. Writing a new feature:
   - Reference javascript-fundamentals.md for module structure
   - Check code-quality.md for complexity limits
   - Use modern-patterns.md for idiomatic JavaScript
   - Consult async-programming.md for Promise/async patterns

2. Refactoring legacy code:
   - Use code-quality.md to identify complexity issues
   - Apply modern-patterns.md to update syntax
   - Replace callbacks with async/await per async-programming.md

3. Setting up a new project:
   - Follow tooling-guide.md for ESLint/Prettier configuration
   - Configure npm scripts per tooling-guide.md
   - Set up pre-commit hooks

## Quick Reference

### Variable Declaration
```javascript
// ✅ Good
const API_URL = 'https://api.example.com';
let currentPage = 1;

// ❌ Bad
var apiUrl = 'https://api.example.com';
```

### Function Patterns
```javascript
// ✅ Arrow function for callbacks
array.map(item => item.id);

// ✅ Regular function for methods
class User {
  getName() {
    return this.name;
  }
}
```

### Async Operations
```javascript
// ✅ async/await with try/catch
async function fetchData() {
  try {
    const response = await fetch(url);
    return await response.json();
  } catch (error) {
    console.error('Fetch failed:', error);
    throw error;
  }
}
```

### Modern Patterns
```javascript
// ✅ Destructuring
const { name, email } = user;
const [first, ...rest] = items;

// ✅ Template literals
const greeting = `Hello, ${name}!`;

// ✅ Spread operator
const merged = { ...defaults, ...options };
```

## Related Skills

- **cui-css** - CSS development standards
- Testing standards (future skill)
- Web components standards (future skill)

## Standards Documents

- `javascript-fundamentals.md` - Core language features and patterns
- `code-quality.md` - Quality standards and refactoring
- `modern-patterns.md` - ES2022+ patterns and idioms
- `async-programming.md` - Promises and async/await
- `tooling-guide.md` - ESLint, Prettier, build tools
