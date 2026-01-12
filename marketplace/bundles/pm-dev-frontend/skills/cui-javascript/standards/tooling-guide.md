# Tooling Guide

ESLint configuration, Prettier setup, npm scripts, and development workflow for JavaScript projects.

## Overview

Modern JavaScript projects require robust tooling for code quality, formatting, and workflow automation. This guide covers ESLint v9+ configuration, Prettier integration, npm scripts, and IDE setup.

## Package.json Setup

### Dependencies

Add these dev dependencies to your project:

```json
{
  "type": "module",
  "devDependencies": {
    "eslint": "^9.14.0",
    "@eslint/js": "^9.14.0",
    "eslint-config-prettier": "^9.0.0",
    "eslint-plugin-prettier": "^5.0.0",
    "eslint-plugin-sonarjs": "^1.0.0",
    "eslint-plugin-jsdoc": "^48.0.0",
    "eslint-plugin-jest": "^28.0.0",
    "eslint-plugin-security": "^2.0.0",
    "eslint-plugin-unicorn": "^51.0.0",
    "eslint-plugin-promise": "^6.1.0",
    "prettier": "^3.0.0"
  }
}
```

### Scripts

Define npm scripts for development workflow:

```json
{
  "scripts": {
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write \"**/*.{js,mjs,json}\"",
    "format:check": "prettier --check \"**/*.{js,mjs,json}\"",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "quality": "npm run lint && npm run format:check",
    "prepare": "npm run quality"
  }
}
```

## ESLint v9 Configuration

### Basic Setup

Create `eslint.config.js` with ES module format:

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
      // See rules section below
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
      'sonarjs/cognitive-complexity': 'off',
      'max-statements': 'off',
    },
  },
];
```

### Core Rules

Configure essential linting rules:

```javascript
rules: {
  // Modern JavaScript
  'no-var': 'error',
  'prefer-const': 'error',
  'prefer-arrow-callback': 'error',
  'arrow-body-style': ['error', 'as-needed'],

  // Code Quality
  'complexity': ['error', 15],
  'max-statements': ['error', 20],
  'max-params': ['error', 5],
  'max-depth': ['error', 3],
  'max-nested-callbacks': ['error', 3],

  // Best Practices
  'no-console': 'warn',
  'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  'no-shadow': 'error',
  'eqeqeq': ['error', 'always'],
  'no-eval': 'error',
  'no-implied-eval': 'error',

  // Promises
  'promise/always-return': 'error',
  'promise/no-return-wrap': 'error',
  'promise/param-names': 'error',
  'promise/catch-or-return': 'error',
  'promise/no-nesting': 'warn',

  // Security
  'security/detect-object-injection': 'warn',
  'security/detect-non-literal-regexp': 'warn',
  'security/detect-unsafe-regex': 'error',

  // SonarJS
  'sonarjs/cognitive-complexity': ['error', 15],
  'sonarjs/no-duplicate-string': ['error', 3],
  'sonarjs/no-identical-functions': 'error',
  'sonarjs/no-redundant-boolean': 'error',

  // JSDoc
  'jsdoc/require-description': 'warn',
  'jsdoc/require-param-description': 'warn',
  'jsdoc/require-returns-description': 'warn',
  'jsdoc/check-tag-names': 'error',

  // Unicorn
  'unicorn/prefer-node-protocol': 'error',
  'unicorn/prefer-module': 'error',
  'unicorn/no-array-for-each': 'warn',
  'unicorn/prefer-spread': 'error',
}
```

### Running ESLint

```bash
# Lint all files
npm run lint

# Auto-fix issues
npm run lint:fix

# Lint specific file
npx eslint src/utils.js

# Lint with specific config
npx eslint --config eslint.config.js src/
```

## Prettier Configuration

### Basic Setup

Create `.prettierrc.js`:

```javascript
/**
 * Prettier configuration for JavaScript projects
 *
 * This configuration ensures consistent code formatting across
 * JavaScript and CSS-in-JS files with environment-specific overrides.
 */

export default {
  // Basic formatting options
  printWidth: 120,
  tabWidth: 2,
  useTabs: false,
  semi: true,
  singleQuote: true,
  quoteProps: 'as-needed',

  // Object and array formatting
  trailingComma: 'es5',
  bracketSpacing: true,
  bracketSameLine: false,

  // Arrow function parentheses
  arrowParens: 'always',

  // Prose formatting
  proseWrap: 'preserve',

  // HTML formatting
  htmlWhitespaceSensitivity: 'css',

  // End of line
  endOfLine: 'lf',

  // Embedded language formatting
  embeddedLanguageFormatting: 'auto',

  // File-specific overrides
  overrides: [
    {
      files: ['*.js', '*.mjs'],
      options: {
        printWidth: 120,
        singleQuote: true,
        trailingComma: 'es5',
        arrowParens: 'always',
        bracketSpacing: true,
        bracketSameLine: false,
      },
    },
    {
      files: 'src/test/**/*.js',
      options: {
        printWidth: 100,
        singleQuote: true,
        trailingComma: 'es5',
        arrowParens: 'avoid',
      },
    },
  ],
};
```

### Core Formatting Rules

- **Print Width**: 120 characters for production, 100 for tests
- **Tab Width**: 2 spaces
- **Use Tabs**: false (always spaces)
- **Semicolons**: true (always use semicolons)
- **Single Quotes**: true (prefer single quotes)
- **Trailing Commas**: 'es5' (where valid in ES5)
- **Bracket Spacing**: true (spaces in object literals)
- **Arrow Parens**: 'always' (always use parentheses)
- **End of Line**: 'lf' (Unix line endings)

### Running Prettier

```bash
# Format all files
npm run format

# Check formatting
npm run format:check

# Format specific file
npx prettier --write src/utils.js

# Check specific file
npx prettier --check src/utils.js
```

### Prettier Ignore

Create `.prettierignore`:

```
# Dependencies
node_modules/
package-lock.json

# Build output
dist/
build/
target/

# Coverage
coverage/

# Generated files
*.min.js
```

## ESLint + Prettier Integration

### Ensure Compatibility

Make sure ESLint and Prettier don't conflict:

```javascript
// eslint.config.js
import prettier from 'eslint-plugin-prettier';
import eslintConfigPrettier from 'eslint-config-prettier';

export default [
  // ... other configs
  eslintConfigPrettier, // Disable conflicting rules
  {
    plugins: {
      prettier,
    },
    rules: {
      'prettier/prettier': 'error', // Run Prettier as ESLint rule
    },
  },
];
```

### Single Command for All Checks

```bash
# Run both lint and format check
npm run quality
```

## IDE Integration

### VS Code

Install extensions:
- ESLint
- Prettier - Code formatter

Create `.vscode/settings.json`:

```json
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "eslint.validate": ["javascript"],
  "eslint.options": {
    "overrideConfigFile": "eslint.config.js"
  },
  "prettier.requireConfig": true
}
```

### IntelliJ IDEA

1. Install Prettier plugin
2. Install ESLint plugin
3. Enable "Run eslint --fix on save"
4. Enable "Run Prettier on save"
5. Configure file watchers (optional)

Settings → Languages & Frameworks → JavaScript → Prettier:
- Prettier package: `./node_modules/prettier`
- Run on save: true

Settings → Languages & Frameworks → JavaScript → Code Quality Tools → ESLint:
- Automatic ESLint configuration
- Run eslint --fix on save: true

## Pre-commit Hooks

### Using Husky + lint-staged

Install dependencies:

```bash
npm install --save-dev husky lint-staged
npx husky install
npx husky add .husky/pre-commit "npx lint-staged"
```

Configure in `package.json`:

```json
{
  "lint-staged": {
    "*.{js,mjs}": [
      "prettier --write",
      "eslint --fix"
    ]
  }
}
```

Now code is automatically formatted and linted before each commit.

## npm Scripts Reference

### Essential Scripts

```json
{
  "scripts": {
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write \"**/*.{js,mjs,json}\"",
    "format:check": "prettier --check \"**/*.{js,mjs,json}\"",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "quality": "npm run lint && npm run format:check && npm test"
  }
}
```

### Advanced Scripts

```json
{
  "scripts": {
    "lint:staged": "eslint --fix",
    "lint:report": "eslint . --format html --output-file eslint-report.html",
    "format:diff": "prettier --list-different \"**/*.{js,mjs,json}\"",
    "quality:ci": "npm run lint && npm run format:check && npm run test:coverage",
    "clean": "rm -rf dist/ coverage/ node_modules/",
    "prebuild": "npm run quality",
    "build": "/* your build command */",
    "pretest": "npm run lint",
    "prepare": "husky install"
  }
}
```

## CI/CD Integration

### GitHub Actions Example

`.github/workflows/quality.yml`:

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint

      - name: Check formatting
        run: npm run format:check

      - name: Run tests
        run: npm run test:coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
```

## Troubleshooting

### ESLint Issues

**Error: Must use import to load ES Module**
- Ensure `"type": "module"` in package.json
- Use `eslint.config.js` (not `.eslintrc.js`)
- Use ES module syntax (import/export)

**Error: Plugin not found**
```bash
npm install --save-dev eslint-plugin-name
```

**Rules not working**
- Check rule is enabled in config
- Verify plugin is imported and added to plugins object
- Run with `--debug` flag: `npx eslint --debug file.js`

### Prettier Issues

**Not formatting on save**
- Check VS Code settings
- Verify `.prettierrc.js` exists
- Restart VS Code

**Conflicts with ESLint**
- Ensure `eslint-config-prettier` is installed
- Add to ESLint config after other configs
- Run `npm run quality` to check both

**Formatting ignored**
- Check `.prettierignore` file
- Verify file extension is in script glob
- Run with `--debug-check`: `npx prettier --debug-check file.js`

## Performance Tips

### ESLint

- Use `.eslintcache` (auto-generated)
- Lint only changed files in CI
- Use `--cache` flag: `eslint --cache .`
- Configure `ignorePatterns` in config

### Prettier

- Use `.prettierignore` to skip large generated files
- Run on changed files only in pre-commit
- Enable cache in IDE settings

### npm Scripts

- Use `npm ci` instead of `npm install` in CI
- Run tests in parallel when possible
- Cache node_modules in CI

## See Also

- [JavaScript Fundamentals](javascript-fundamentals.md) - Core patterns
- [Code Quality](code-quality.md) - Complexity and maintainability
- [Modern Patterns](modern-patterns.md) - Advanced patterns
- [Async Programming](async-programming.md) - Asynchronous code
