# JavaScript Refactoring Triggers

This document defines when and how to identify violations that require refactoring in JavaScript codebases. It provides systematic criteria for detecting code quality issues and determining when action is required.

## Purpose

Define clear trigger criteria for identifying code that needs refactoring. Each section answers the question: "When should I take action to improve this code?"

---

## When to Enforce Vanilla JavaScript Usage

**Apply vanilla JavaScript refactoring when:**

### jQuery/Cash Usage Detected

Legacy library usage for simple operations that have native equivalents.

**Action Required:** Replace with native JavaScript per vanilla JavaScript preference.

**Examples:**
- Replace `$.ajax()` with `fetch()`
- Replace `$('.selector')` with `document.querySelector()`
- Replace `$.each()` with `Array.forEach()`
- Replace `$(element).addClass()` with `element.classList.add()`
- Replace `$(element).show()/hide()` with `element.style.display`

### Unnecessary Library Dependencies

Libraries used for features that are available natively in modern JavaScript.

**Action Required:** Remove dependency and use native alternatives.

**Common Replacements:**
- Lodash array methods → Native array methods (`map`, `filter`, `reduce`, `find`)
- Moment.js → Native `Date` or date-fns (only if complex date manipulation needed)
- Request libraries → Native `fetch` API
- Axios → Native `fetch` with proper error handling
- jQuery animations → CSS transitions/animations or Web Animations API

### Complex Implementation Threshold

**Evaluation Criteria:** Only keep libraries when vanilla JS would be overly complex.

**Threshold:** More than 50 lines of custom code vs 5-10 lines with library.

**Action Required:** Document justification for library retention.

**Valid Library Usage Examples:**
- Complex charting libraries (Chart.js, D3.js)
- Rich text editors (TinyMCE, Quill)
- Complex date calculations (date-fns for business logic)
- State management for large applications (Redux, MobX)

---

## When to Remove Test/Mock Code from Production

**Apply test code removal when:**

### Test-Specific Imports

Mock libraries or test utilities imported in production code.

**Action Required:** Remove all test-specific imports and code.

**Common Violations:**
```javascript
// ❌ Never in production files
import { jest } from '@jest/globals';
import { mock } from 'jest-mock';
import testHelper from './test-utils';
```

**Mock implementations left in production code:**
```javascript
// ❌ Remove from production
const mockUserData = {
  id: 'test-123',
  name: 'Test User'
};
```

**Test helper functions in production modules:**
```javascript
// ❌ Move to test files
export function createTestUser() { ... }
```

### Conditional Test Logic

`if (process.env.NODE_ENV === 'test')` blocks in production code.

**Action Required:** Extract test-specific behavior to test files.

**Refactoring Pattern:** Use dependency injection or configuration patterns.

**Example:**
```javascript
// ❌ Avoid
function fetchData() {
  if (process.env.NODE_ENV === 'test') {
    return mockData;
  }
  return fetch('/api/data');
}

// ✅ Better - use dependency injection
function fetchData(dataSource = defaultDataSource) {
  return dataSource.getData();
}
```

### Development-Only Code

Debug statements, console logs, or development helpers.

**Action Required:** Remove or properly guard with build-time conditions.

**Exception:** Legitimate debug modes with proper configuration.

**Examples:**
```javascript
// ❌ Remove from production
console.log('Debug: user data', userData);
debugger;

// ✅ OK - proper debug mode
if (config.debugMode) {
  logger.debug('User data', userData);
}
```

---

## When to Improve Modularization

**Apply modularization improvements when:**

### Large Monolithic Files

Files exceeding 300-400 lines indicate poor separation of concerns.

**Action Required:** Split into focused modules.

**Target:** Single responsibility per module.

**Refactoring Strategy:**
1. Identify distinct concerns within the file
2. Create separate modules for each concern
3. Use ES modules for imports/exports
4. Maintain clear module boundaries

### Mixed Concerns

UI logic mixed with business logic or data fetching.

**Action Required:** Separate concerns into distinct modules.

**Pattern:** Model-View-Controller or similar separation.

**Example Structure:**
```
components/
  UserProfile.js       // UI component
services/
  userService.js       // API calls
models/
  User.js             // Business logic
utils/
  validators.js       // Validation logic
```

### Duplicate Code Blocks

Same logic repeated across files.

**Action Required:** Extract to shared utilities.

**Threshold:** Duplication of 10+ lines or complex logic.

**Exception:** Simple 1-5 line patterns that would overcomplicate if extracted.

**Examples:**
```javascript
// ❌ Duplicated across files
function formatDate(date) {
  return new Intl.DateTimeFormat('en-US').format(date);
}

// ✅ Extract to utils/dateFormatter.js
export function formatDate(date) {
  return new Intl.DateTimeFormat('en-US').format(date);
}
```

### Over-Modularization

Excessive splitting for trivial functionality.

**Warning Signs:**
- Modules with single 1-5 line functions
- More import statements than actual code
- Circular dependency patterns emerging
- Files that are just re-exports

**Action Required:** Consolidate related simple functions.

**Example:**
```javascript
// ❌ Over-modularized
// utils/add.js
export const add = (a, b) => a + b;

// utils/subtract.js
export const subtract = (a, b) => a - b;

// ✅ Better - group related functions
// utils/math.js
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
export const multiply = (a, b) => a * b;
```

---

## When to Update Package.json

**Apply package.json updates when:**

### Outdated Dependencies

Dependencies with newer stable versions available.

**Action Required:** Update to latest stable versions.

**Process:**
1. Run `npm outdated` to identify updates
2. Update dependencies incrementally (not all at once)
3. Run `npm audit` after each update
4. Test thoroughly after updates
5. Check for breaking changes in release notes

**Priority:**
- Critical: Security vulnerabilities
- High: Major framework updates with important features
- Medium: Minor version updates
- Low: Patch updates

### Security Vulnerabilities

`npm audit` reports vulnerabilities.

**Action Required:** Fix all critical and high vulnerabilities immediately.

**Process:**
1. Run `npm audit` to identify vulnerabilities
2. Run `npm audit fix` for automatic fixes
3. Manually update packages for remaining issues
4. If no fix available, consider alternative packages
5. Document any unresolvable vulnerabilities with justification

**Severity Levels:**
- **Critical/High:** Fix immediately, block releases
- **Moderate:** Fix within sprint
- **Low:** Fix when convenient

### Unused Dependencies

Packages listed but not imported anywhere.

**Action Required:** Remove after verification.

**Detection Methods:**
- Use `depcheck` tool
- Manual verification via search
- Check package usage in IDE

**Verification Steps:**
1. Search for package imports in codebase
2. Check for dynamic imports
3. Verify build tool usage (Webpack plugins, etc.)
4. Check package.json scripts for usage
5. Remove only if truly unused

### Missing Scripts

Standard scripts not defined.

**Action Required:** Add required scripts.

**Required Scripts:**
```json
{
  "scripts": {
    "test": "jest",
    "test:coverage": "jest --coverage",
    "test:watch": "jest --watch",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "build": "webpack --mode production",
    "dev": "webpack serve --mode development"
  }
}
```

### Incorrect Dependency Types

Dependencies in wrong section (dependencies vs devDependencies).

**Action Required:** Move to correct section.

**Rule:**
- **dependencies:** Runtime dependencies needed in production
- **devDependencies:** Build tools, test frameworks, linters

**Examples:**
```json
{
  "dependencies": {
    "react": "^18.0.0",
    "axios": "^1.0.0"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "eslint": "^8.0.0",
    "webpack": "^5.0.0"
  }
}
```

---

## When to Fix JSDoc and Comments

**Apply documentation fixes when:**

### Missing JSDoc

Public functions without JSDoc comments.

**Action Required:** Add JSDoc following standards.

**Required Elements:**
- Description
- `@param` for each parameter
- `@returns` for return value
- `@throws` for exceptions

**Example:**
```javascript
/**
 * Fetches user data from the API
 * @param {string} userId - The user's unique identifier
 * @returns {Promise<User>} The user object
 * @throws {Error} If user not found or network error
 */
async function fetchUser(userId) {
  // ...
}
```

### Trivial Comments

Comments stating the obvious.

**Action Required:** Remove redundant comments.

**Examples to Remove:**
```javascript
// ❌ Trivial - remove
// Set the name
this.name = name;

// ❌ Trivial - remove
// Increment counter by 1
counter++;

// ❌ Trivial - remove
// Return the result
return result;
```

### Standard Field Comments

Comments on common patterns that don't add value.

**Action Required:** Remove comments on standard fields.

**Examples:**
```javascript
// ❌ Remove - obvious
/** The user's email address */
email: string;

// ❌ Remove - standard pattern
/** Logger instance */
const logger = getLogger('UserService');

// ✅ Keep - adds context
/** Email must be verified before account activation */
email: string;
```

### Outdated Documentation

Comments not matching current implementation.

**Action Required:** Update to reflect current behavior.

**Focus Areas:**
- Parameter type changes
- Return value changes
- Behavior modifications
- Removed features

**Example:**
```javascript
// ❌ Outdated
/**
 * @param {string} id - User ID
 * @returns {User} User object
 */
async function getUser(id) {
  // Now returns Promise<User | null> instead of User
  // ...
}

// ✅ Updated
/**
 * @param {string} id - User ID
 * @returns {Promise<User | null>} User object or null if not found
 */
async function getUser(id) {
  // ...
}
```

### Complex Logic Without Comments

Non-obvious algorithms or business logic.

**Action Required:** Add explanatory comments for complex sections.

**Threshold:** Logic requiring more than 30 seconds to understand.

**Example:**
```javascript
// ✅ Good - explains complex logic
// Calculate compound interest using the formula: A = P(1 + r/n)^(nt)
// where P = principal, r = rate, n = compounds per year, t = years
const amount = principal * Math.pow(1 + rate / compoundsPerYear, compoundsPerYear * years);
```

---

## Implementation Guidance

For detailed implementation patterns on HOW to implement these fixes, refer to:

- **cui-javascript** skill - Core patterns and modern JavaScript
- **cui-javascript-linting** skill - ESLint configuration
- **cui-jsdoc** skill - Documentation implementation details
- **cui-javascript-project** skill - Package.json configuration

This document defines WHEN to apply refactoring actions. Implementation skills define HOW to implement the fixes.
