# ESLint Configuration Standards

## Purpose

This document defines ESLint flat configuration structure, required dependencies, plugin management, and environment setup for consistent JavaScript linting.

## ESLint Flat Configuration

### Configuration File Structure

All projects must use ESLint with flat configuration format. Create `eslint.config.js` in the project root:

```javascript
import js from '@eslint/js';
import sonarjs from 'eslint-plugin-sonarjs';
import jsdoc from 'eslint-plugin-jsdoc';
import jest from 'eslint-plugin-jest';
import security from 'eslint-plugin-security';
import unicorn from 'eslint-plugin-unicorn';
import promise from 'eslint-plugin-promise';
import prettier from 'eslint-plugin-prettier';

export default [
  js.configs.recommended,
  {
    plugins: {
      sonarjs,
      jsdoc,
      jest,
      security,
      unicorn,
      promise,
      prettier,
    },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        console: 'readonly',
        process: 'readonly',
        document: 'readonly',
        window: 'readonly',
        navigator: 'readonly',
        HTMLElement: 'readonly',
        customElements: 'readonly',
        CSSStyleSheet: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        Headers: 'readonly',
        fetch: 'readonly',
      },
    },
    rules: {
      // Rule configuration (see eslint-rules.md)
    },
  },
  // Test file configuration
  {
    files: ['**/*.test.js', '**/test/**/*.js'],
    plugins: { jest },
    languageOptions: {
      globals: {
        jest: 'readonly',
        describe: 'readonly',
        it: 'readonly',
        test: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
      },
    },
    rules: {
      // Test-specific overrides (see eslint-rules.md)
    },
  },
];
```

### Configuration Requirements

**File Name**: `eslint.config.js` (required, not .eslintrc.js)

**Syntax**: ES module format with `export default`

**Structure**: Array of configuration objects

**Plugin Import**: Direct imports instead of string references

**No Legacy Format**: Do not use .eslintrc.json, .eslintrc.yml, or .eslintrc.js with legacy format

## Required Dependencies

### Core ESLint Dependencies

All projects must include these core dependencies in `package.json`:

```json
{
  "devDependencies": {
    "eslint": "^10.0.0",
    "@eslint/js": "^10.0.0"
  }
}
```

### Required Plugin Dependencies

All projects must include these plugin dependencies:

```json
{
  "devDependencies": {
    "eslint-plugin-jest": "^28.8.3",
    "eslint-plugin-jsdoc": "^62.8.0",
    "eslint-plugin-unicorn": "^63.0.0",
    "eslint-plugin-security": "^3.0.0",
    "eslint-plugin-promise": "^7.0.0",
    "eslint-plugin-sonarjs": "^4.0.0",
    "eslint-plugin-prettier": "^5.0.0",
    "prettier": "^3.0.3"
  }
}
```

### Plugin Purpose

- **@eslint/js**: Official ESLint recommended configuration (replaces airbnb-base)
- **eslint-plugin-jest**: Jest testing best practices and rule validation
- **eslint-plugin-jsdoc**: JSDoc documentation standards enforcement
- **eslint-plugin-unicorn**: Additional JavaScript best practices beyond standard ESLint
- **eslint-plugin-security**: Security vulnerability detection and prevention
- **eslint-plugin-promise**: Promise and async/await best practices
- **eslint-plugin-sonarjs**: Code quality and complexity analysis (required for maintainability)
- **eslint-plugin-prettier**: Prettier integration for consistent formatting
- **prettier**: Code formatter (must be last in extends chain)

## ES Module Requirements

ESLint flat config requires `"type": "module"` in package.json. Use ES `import`/`export default` syntax -- not CommonJS `require`/`module.exports`.

## Framework-Specific Extensions

### Web Components Configuration

For projects using Lit or custom elements, add framework-specific plugins:

```javascript
import lit from 'eslint-plugin-lit';
import wc from 'eslint-plugin-wc';

export default [
  js.configs.recommended,
  {
    plugins: {
      // ... base plugins
      lit,
      wc,
    },
    rules: {
      'lit/no-invalid-html': 'error',
      'lit/no-legacy-template-syntax': 'error',
      'lit/attribute-value-entities': 'error',
      'wc/require-listener-teardown': 'error',
      'wc/no-constructor-attributes': 'error',
    }
  }
];
```

**Additional Dependencies**:
```json
{
  "devDependencies": {
    "eslint-plugin-lit": "^1.11.0",
    "eslint-plugin-wc": "^2.0.4"
  }
}
```

### Node.js Configuration

For Node.js projects, configure Node.js-specific environment:

```javascript
export default [
  js.configs.recommended,
  {
    languageOptions: {
      globals: {
        // Node.js globals
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        require: 'readonly',
        module: 'readonly',
        exports: 'readonly',
        Buffer: 'readonly',
      },
    },
    rules: {
      'no-console': 'warn', // Allow console in Node.js
    }
  }
];
```

## Plugin Order

Prettier must be last to override formatting rules. Rules are namespaced by plugin: `'jsdoc/require-description'`, `'security/detect-eval-with-expression'`, `'prettier/prettier'`.

## File-Specific Overrides

Use multiple configuration objects in the array for file-specific rules:

```javascript
export default [
  { /* base rules */ },
  { files: ['**/*.test.js', '**/test/**/*.js'], rules: { /* relaxed for tests */ } },
  { files: ['src/main/resources/components/**/*.js'], rules: { /* stricter for production */ } },
  { files: ['src/test/js/mocks/**/*.js'], rules: { /* relaxed for mocks */ } },
];
```

## Common Configuration Issues

### Issue: Cannot use import statement outside a module

**Cause**: Missing `"type": "module"` in package.json

**Solution**: Add ES module support to package.json:
```json
{
  "type": "module"
}
```

### Issue: Plugin not found

**Cause**: Plugin not installed or incorrect import

**Solution**: Verify plugin is installed and imported correctly:
```bash
npm install --save-dev eslint-plugin-jsdoc
```
```javascript
import jsdoc from 'eslint-plugin-jsdoc';
```

### Issue: Configuration file not found

**Cause**: Wrong filename or location

**Solution**: Ensure file is named `eslint.config.js` in project root (not .eslintrc.js)

### Issue: Rules not applying

**Cause**: Plugin not registered in plugins object

**Solution**: Add plugin to plugins object before using its rules:
```javascript
plugins: { jsdoc },
rules: { 'jsdoc/require-description': 'warn' }
```

### Issue: Conflicting rules between plugins

**Cause**: Multiple plugins defining similar rules

**Solution**: Disable conflicting rules explicitly:
```javascript
rules: {
  'indent': 'off',              // Disabled in favor of Prettier
  'prettier/prettier': 'error', // Prettier handles indentation
}
```

## Migration from Legacy

Key changes from `.eslintrc.js` to flat config:
- **File**: `.eslintrc.js` → `eslint.config.js`
- **Export**: `module.exports` → `export default`
- **Structure**: Single object → Array of objects
- **Plugins**: String references → Direct imports
- **Environment**: `env` object → `languageOptions.globals`

## Validation

```bash
# Verify configuration loads
npx eslint --print-config src/main/resources/example.js

# Test linting
npx eslint src/main/resources/example.js
```
