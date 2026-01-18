# ESLint Configuration Standards

## Purpose

This document defines ESLint v9 flat configuration structure, required dependencies, plugin management, and environment setup for consistent JavaScript linting across all CUI projects.

## ESLint v9 Flat Configuration

### Configuration File Structure

All projects must use ESLint v9+ with flat configuration format. Create `eslint.config.js` in the project root:

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

### Core ESLint v9 Dependencies

All projects must include these core dependencies in `package.json`:

```json
{
  "devDependencies": {
    "eslint": "^9.14.0",
    "@eslint/js": "^9.14.0",
    "eslint-config-prettier": "^9.0.0"
  }
}
```

### Required Plugin Dependencies

All projects must include these plugin dependencies:

```json
{
  "devDependencies": {
    "eslint-plugin-jest": "^28.8.3",
    "eslint-plugin-jsdoc": "^46.8.0",
    "eslint-plugin-unicorn": "^48.0.0",
    "eslint-plugin-security": "^1.7.1",
    "eslint-plugin-promise": "^6.1.1",
    "eslint-plugin-sonarjs": "^2.0.3",
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

## ES Module Configuration

### Package.json Configuration

ESLint flat configuration requires ES module support in `package.json`:

```json
{
  "type": "module"
}
```

### Import Syntax

Use ES module import syntax in `eslint.config.js`:

```javascript
// Correct - ES module imports
import js from '@eslint/js';
import jsdoc from 'eslint-plugin-jsdoc';

// Incorrect - CommonJS requires (not supported)
const js = require('@eslint/js');
const jsdoc = require('eslint-plugin-jsdoc');
```

### Export Syntax

Use ES module export syntax:

```javascript
// Correct - ES module export
export default [
  js.configs.recommended,
  {
    plugins: { jsdoc },
    rules: { /* configuration */ }
  }
];

// Incorrect - CommonJS exports (not supported)
module.exports = [ /* configuration */ ];
```

## Environment Configuration

### Language Options

Configure language version and module type:

```javascript
languageOptions: {
  ecmaVersion: 2022,    // ES2022 support
  sourceType: 'module', // ES modules
}
```

### Global Variables

Define global variables available in all environments:

```javascript
languageOptions: {
  globals: {
    // Browser globals
    document: 'readonly',
    window: 'readonly',
    navigator: 'readonly',
    console: 'readonly',

    // Web Components globals
    HTMLElement: 'readonly',
    customElements: 'readonly',
    CSSStyleSheet: 'readonly',

    // Timer globals
    setInterval: 'readonly',
    clearInterval: 'readonly',
    setTimeout: 'readonly',
    clearTimeout: 'readonly',

    // Fetch API
    Headers: 'readonly',
    fetch: 'readonly',

    // Node.js globals (if applicable)
    process: 'readonly',
  },
}
```

### Test Environment Globals

Configure globals for test files using file-specific configuration:

```javascript
{
  files: ['**/*.test.js', '**/test/**/*.js'],
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
}
```

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

## Plugin Configuration

### Base Plugin Setup

Configure all required plugins in the plugins object:

```javascript
plugins: {
  sonarjs,
  jsdoc,
  jest,
  security,
  unicorn,
  promise,
  prettier,
}
```

### Plugin Order

**Order matters for extends**: Prettier must be last to override formatting rules:

```javascript
export default [
  js.configs.recommended,           // Base ESLint rules
  sonarjs.configs.recommended,      // SonarJS quality rules
  // ... other plugin configs
  {
    plugins: { prettier },
    rules: {
      'prettier/prettier': 'error',  // Prettier must be last
    }
  }
];
```

### Plugin Rule Namespacing

Rules are namespaced by plugin name:

```javascript
rules: {
  'jsdoc/require-description': 'warn',        // jsdoc plugin
  'jest/no-focused-tests': 'error',           // jest plugin
  'sonarjs/cognitive-complexity': 'error',    // sonarjs plugin
  'security/detect-eval-with-expression': 'error', // security plugin
  'unicorn/prefer-query-selector': 'error',   // unicorn plugin
  'promise/always-return': 'error',           // promise plugin
  'prettier/prettier': 'error',               // prettier plugin
}
```

## File-Specific Configuration

### Configuration Array Structure

Use multiple configuration objects for file-specific overrides:

```javascript
export default [
  // Base configuration for all files
  {
    plugins: { /* plugins */ },
    rules: { /* base rules */ }
  },

  // Test file overrides
  {
    files: ['**/*.test.js', '**/test/**/*.js'],
    rules: { /* relaxed rules for tests */ }
  },

  // Production component overrides
  {
    files: ['src/main/resources/components/**/*.js'],
    rules: { /* stricter rules for production */ }
  },

  // Mock file overrides
  {
    files: ['src/test/js/mocks/**/*.js'],
    rules: { /* relaxed rules for mocks */ }
  },
];
```

### File Pattern Syntax

Use glob patterns to target specific files:

```javascript
files: ['**/*.test.js'],              // All test files
files: ['**/test/**/*.js'],           // All files in test directories
files: ['src/main/**/*.js'],          // All files in src/main
files: ['**/*.{js,jsx}'],             // Multiple extensions
files: ['!**/node_modules/**'],       // Exclude pattern (rarely needed)
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

## Migration from Legacy Configuration

### Legacy .eslintrc.js to Flat Config

**Before (Legacy)**:
```javascript
module.exports = {
  extends: ['plugin:jsdoc/recommended'],
  plugins: ['jsdoc'],
  rules: { /* rules */ }
};
```

**After (Flat Config)**:
```javascript
import js from '@eslint/js';
import jsdoc from 'eslint-plugin-jsdoc';

export default [
  js.configs.recommended,
  {
    plugins: { jsdoc },
    rules: { /* rules */ }
  }
];
```

### Key Differences

- **File name**: .eslintrc.js → eslint.config.js
- **Export**: module.exports → export default
- **Structure**: Object → Array of objects
- **Plugins**: String references → Direct imports
- **Extends**: String array → Imported config objects
- **Environment**: env object → languageOptions.globals

## Configuration Validation

### Verify Configuration

Test configuration works correctly:

```bash
# Verify configuration loads without errors
npx eslint --print-config src/main/resources/example.js

# Test linting on sample file
npx eslint src/main/resources/example.js

# Check for rule conflicts
npx eslint --debug src/main/resources/example.js 2>&1 | grep -i conflict
```

### Validate Plugin Installation

Verify all plugins are installed:

```bash
npm list eslint-plugin-jsdoc
npm list eslint-plugin-jest
npm list eslint-plugin-sonarjs
npm list eslint-plugin-security
npm list eslint-plugin-unicorn
npm list eslint-plugin-promise
npm list eslint-plugin-prettier
```

## Best Practices

1. **Always use flat config** - ESLint v9 flat configuration is the modern standard
2. **Set "type": "module"** - Required for ES module imports in configuration
3. **Install all required plugins** - JSDoc, Jest, SonarJS, Security, Unicorn, Promise, Prettier
4. **Use direct imports** - Import plugins directly, not as strings
5. **Prettier must be last** - Always configure Prettier last to avoid conflicts
6. **Use file-specific overrides** - Relax rules for tests, strict for production
7. **Test configuration** - Verify configuration loads and lints correctly
8. **Keep plugins updated** - Regularly update ESLint and plugin versions
9. **Document exceptions** - Comment any unusual rule configurations
10. **Use recommended configs** - Start with plugin recommended configs before customizing
