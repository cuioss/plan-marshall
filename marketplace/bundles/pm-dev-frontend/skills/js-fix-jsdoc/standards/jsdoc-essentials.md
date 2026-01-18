# JSDoc Essentials

## Purpose

Core JSDoc standards for CUI JavaScript projects including required tags, ESLint integration, and documentation requirements.

## ESLint Configuration

### Required Plugin

```json
{
  "devDependencies": {
    "eslint-plugin-jsdoc": "^46.8.0"
  }
}
```

### Configuration

```javascript
// .eslintrc.js
module.exports = {
  extends: ['plugin:jsdoc/recommended'],
  plugins: ['jsdoc'],
  rules: {
    'jsdoc/require-description': 'error',
    'jsdoc/require-param-description': 'error',
    'jsdoc/require-returns-description': 'error',
    'jsdoc/require-example': 'warn'
  }
};
```

## Documentation Requirements

### Mandatory Documentation

Must be documented:
- All public functions and methods
- All classes and constructors
- All exported modules
- Complex algorithms or business logic
- Configuration objects and constants

### Optional Documentation

May be documented based on complexity:
- Private methods (when complex)
- Simple getter/setter methods
- Utility functions (when purpose isn't clear from name)

## Comment Structure

```javascript
/**
 * Brief one-line description.
 *
 * Optional detailed description providing context and
 * important implementation details.
 *
 * @param {type} paramName - Description
 * @param {type} [optionalParam] - Description (optional)
 * @returns {type} Description of return value
 * @throws {Error} Description of when errors are thrown
 * @example
 * // Usage example
 * const result = functionName('example');
 */
```

## Required Tags

### @param

```javascript
/**
 * @param {string} username - User's login name (3-50 chars)
 * @param {number} age - User's age in years
 * @param {boolean} [isActive=true] - Whether account is active (optional)
 */
```

### @returns

```javascript
/**
 * @returns {boolean} True if validation succeeds
 * @returns {Promise<User>} Promise resolving to user object
 * @returns {void} This function does not return a value
 */
```

### @throws

```javascript
/**
 * @throws {TypeError} When input is not a string
 * @throws {ValidationError} When validation fails
 * @throws {NetworkError} When API request fails
 */
```

### @example

```javascript
/**
 * @example
 * // Basic usage
 * const result = calculateTotal(100, 0.08);
 * console.log(result); // 108
 *
 * @example
 * // With error handling
 * try {
 *   const result = calculateTotal(-100, 0.08);
 * } catch (error) {
 *   console.error('Error:', error.message);
 * }
 */
```

## Optional Tags

- `@since` - Version when added (e.g., `@since 1.2.0`)
- `@author` - Original author or team
- `@see` - References to related code (e.g., `@see {@link OtherClass}`)
- `@deprecated` - For deprecated functionality with migration path
- `@todo` - For planned improvements

## Type Annotations

### Basic Types

```javascript
/**
 * @param {string} name
 * @param {number} age
 * @param {boolean} isActive
 * @param {Array<string>} items
 * @param {Object} config
 * @param {Promise<User>} userPromise
 */
```

### Union Types

```javascript
/**
 * @param {string|number} id - Can be string or number
 * @param {User|null} user - User object or null
 */
```

### Custom Types

```javascript
/**
 * @typedef {Object} User
 * @property {string} id - User identifier
 * @property {string} email - Email address
 * @property {Array<string>} roles - User roles
 */

/**
 * @param {User} user - User object
 * @returns {User} Updated user
 */
```

## Writing Style

- **Present tense** - "Calculates total", not "Will calculate"
- **Active voice** - "Validates input", not "Input is validated"
- **Complete sentences** - Proper capitalization and punctuation
- **Clear and specific** - Avoid vague descriptions like "processes data"
- **No redundancy** - Don't just repeat the function name

## Build Integration

### npm Scripts

```json
{
  "scripts": {
    "docs": "jsdoc -c jsdoc.conf.json",
    "docs:validate": "npm run lint:js"
  }
}
```

### JSDoc Configuration

Create `jsdoc.conf.json`:

```json
{
  "source": {
    "include": ["./src/main/resources/dev-ui/"],
    "exclude": ["node_modules/", "target/"]
  },
  "opts": {
    "destination": "target/docs/",
    "recurse": true
  }
}
```

## Validation

Run ESLint to validate:
```bash
npm run lint:js
```

Common validation errors:
- Missing descriptions
- Missing parameter descriptions
- Invalid type annotations
- Parameter name mismatches
