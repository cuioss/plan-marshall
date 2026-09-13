# ESLint Rule Configurations

## Purpose

This document defines comprehensive ESLint rule configurations including documentation standards, security controls, code quality rules, modern JavaScript patterns, and environment-specific overrides.

## Rule Configuration Overview

ESLint rules are organized into focused categories:

- **Base JavaScript Rules**: Core JavaScript best practices and patterns
- **Documentation Rules**: JSDoc validation and quality standards
- **Security Rules**: Vulnerability detection and security best practices
- **Code Quality Rules**: SonarJS complexity and maintainability analysis
- **Modern JavaScript Rules**: ES6+ features and async patterns
- **Promise/Async Rules**: Promise and async/await best practices
- **Framework-Specific Rules**: Lit and Web Components validation (optional)
- **Environment Overrides**: Test files, production code, mock files

## Base JavaScript Rules

### Import/Export Management

Native ES module support in modern browsers and Node.js handles most import/export validation (unresolved imports, extensions, extraneous dependencies). No import plugin is required in the base configuration.

If additional import linting is needed (e.g., enforcing import order or detecting circular dependencies), use [`eslint-plugin-import-x`](https://github.com/un-ts/eslint-plugin-import-x) — a maintained fork with native flat config support. Do not use the original `eslint-plugin-import` which lacks flat config support.

### Core JavaScript Quality

Fundamental JavaScript best practices:

```javascript
rules: {
  // Variable declarations
  'prefer-const': 'error',               // Require const when possible
  'no-var': 'error',                     // No var declarations
  'no-unused-vars': 'error',             // Error for unused variables

  // Functions
  'class-methods-use-this': 'off',       // Allow methods without 'this'
  'prefer-arrow-callback': 'error',      // Prefer arrow functions for callbacks
  'arrow-parens': ['error', 'always'],   // Always use parentheses in arrow functions

  // Code quality
  'no-console': 'warn',                  // Warning for console statements
  'no-debugger': 'error',                // Error for debugger statements
  'no-underscore-dangle': 'off',         // Allow underscore for private properties
  'no-param-reassign': 'off',            // Allow for test setups
  'no-promise-executor-return': 'off',   // Allow for test utilities

  // Modern JavaScript
  'arrow-spacing': 'error',              // Consistent arrow function spacing
  'object-shorthand': 'error',           // Use object shorthand
  'prefer-template': 'error',            // Use template literals
  'template-curly-spacing': 'error',     // Consistent template spacing
}
```

### Prettier Integration Rules

For Prettier integration rules (disabled style rules and `prettier/prettier: 'error'`), see [prettier-configuration.md](prettier-configuration.md) "ESLint Integration".

## Documentation Rules (JSDoc)

### Required JSDoc Rules

Documentation quality and completeness standards:

```javascript
rules: {
  // JSDoc validation
  'jsdoc/require-description': 'warn',              // Require descriptions
  'jsdoc/require-param-description': 'warn',        // Describe parameters
  'jsdoc/require-returns-description': 'warn',      // Describe return values

  // JSDoc formatting
  'jsdoc/check-alignment': 'error',                 // Proper alignment
  'jsdoc/check-indentation': 'error',               // Consistent indentation
  'jsdoc/check-tag-names': 'error',                 // Valid JSDoc tags
  'jsdoc/check-types': 'error',                     // Valid type annotations
  'jsdoc/require-hyphen-before-param-description': 'error', // Consistent formatting
}
```

## Security Rules

### Required Security Controls

Essential security vulnerability prevention:

```javascript
rules: {
  // Security validation
  'security/detect-object-injection': 'warn',          // Detect object injection
  'security/detect-eval-with-expression': 'error',     // Prevent eval usage
  'security/detect-unsafe-regex': 'error',             // Detect ReDoS vulnerabilities
  'security/detect-buffer-noassert': 'error',          // Safe buffer usage
  'security/detect-child-process': 'error',            // Prevent child process injection
}
```

## Code Quality Rules (SonarJS)

### SonarJS Required Configuration

SonarJS is required for comprehensive quality and complexity analysis:

```javascript
import sonarjs from 'eslint-plugin-sonarjs';

export default [
  sonarjs.configs.recommended,   // Use SonarJS recommended defaults
  {
    plugins: { sonarjs },
    rules: {
      // SonarJS rules use recommended defaults
      // Override only when project requirements differ
    }
  }
];
```

The `sonarjs.configs.recommended` preset enables rules for cognitive complexity (default: 15), code simplification, duplicate detection, and dead code. Override only when necessary:

### SonarJS Customization

Override defaults only when necessary:

```javascript
rules: {
  'sonarjs/cognitive-complexity': ['warn', 20],  // Increase threshold if needed
  'sonarjs/no-duplicate-string': ['warn', { threshold: 3 }], // Adjust threshold
}
```

## Modern JavaScript Rules

### ES6+ Feature Enforcement

Enforce modern JavaScript patterns:

```javascript
rules: {
  // Destructuring and spreading
  'prefer-destructuring': ['error', { array: false, object: true }],
  'prefer-rest-params': 'error',                       // Use rest parameters
  'prefer-spread': 'error',                            // Use spread operator
  'prefer-object-spread': 'error',                     // Use object spread

  // Modern syntax
  'symbol-description': 'error',                       // Require symbol descriptions
  'no-useless-computed-key': 'error',                  // Remove useless computed keys
  'no-useless-rename': 'error',                        // Remove useless renaming
  'no-useless-return': 'error',                        // Remove useless returns

  // Deprecated patterns
  'no-void': 'error',                                  // Disallow void operator
  'no-with': 'error',                                  // Disallow with statements

  // Modern operators
  'prefer-numeric-literals': 'error',                  // Use numeric literals
  'prefer-exponentiation-operator': 'error',           // Use ** operator
  'prefer-regex-literals': 'error',                    // Use regex literals
}
```

## Promise and Async Rules

### Promise Best Practices

Modern asynchronous JavaScript patterns:

```javascript
rules: {
  // Promise handling
  'promise/always-return': 'error',                    // Always return in promise chains
  'promise/catch-or-return': 'error',                  // Handle promise rejections
  'promise/no-return-wrap': 'error',                   // Avoid unnecessary wrapping
  'promise/param-names': 'error',                      // Consistent parameter names
  'promise/no-nesting': 'warn',                        // Avoid nested promises
  'promise/prefer-await-to-then': 'warn',              // Prefer async/await
  'promise/prefer-await-to-callbacks': 'warn',         // Modernize callback patterns
  'prefer-promise-reject-errors': 'error',             // Proper promise rejection
}
```

### Async/Await Rules

Error handling and async function patterns:

```javascript
rules: {
  // Async/await patterns
  'no-throw-literal': 'error',                         // Throw Error objects
  'no-return-await': 'error',                          // Avoid redundant await
  'require-await': 'warn',                             // Require await in async functions
  'no-async-promise-executor': 'error',                // No async promise executors
  'no-await-in-loop': 'warn',                          // Avoid await in loops
  'no-promise-executor-return': 'error',               // No returns in promise executors
}
```

## Maintainability Rules

### Code Complexity Limits

Standards for maintainable code:

```javascript
rules: {
  // Complexity thresholds
  'complexity': ['warn', { max: 15 }],                 // Cyclomatic complexity
  'max-statements': ['warn', { max: 20 }],             // Maximum statements per function
  'max-params': ['warn', { max: 5 }],                  // Maximum function parameters
  'max-nested-callbacks': ['error', { max: 4 }],       // Maximum callback nesting
  'max-depth': ['error', { max: 4 }],                  // Maximum nesting depth

  // Magic numbers
  'no-magic-numbers': ['warn', {
    ignore: [-1, 0, 1, 2, 100, 200, 404, 500, 1000, 30000],
    ignoreArrayIndexes: true,
    ignoreDefaultValues: true
  }],
}
```

### Performance Rules

Code performance and optimization:

```javascript
rules: {
  // Performance
  'no-loop-func': 'error',                             // No functions in loops
  'no-extend-native': 'error',                         // No native prototype extension
  'no-iterator': 'error',                              // No __iterator__ usage
  'no-proto': 'error',                                 // No __proto__ usage
  'no-script-url': 'error',                            // No javascript: URLs
}
```

## Unicorn Best Practices

### Additional Code Quality Rules

Unicorn plugin provides enhanced best practices:

```javascript
rules: {
  // Unicorn overrides (adjust defaults)
  'unicorn/filename-case': 'off',                   // Allow kebab-case for components
  'unicorn/prevent-abbreviations': 'off',           // Allow common abbreviations
  'unicorn/no-null': 'off',                         // Allow null values
  'unicorn/no-array-for-each': 'off',               // Allow forEach for readability

  // Unicorn recommended (keep enabled)
  'unicorn/prefer-dom-node-text-content': 'off',    // Allow textContent usage
  'unicorn/prefer-query-selector': 'error',         // Use querySelector
  'unicorn/prefer-modern-dom-apis': 'error',        // Use modern DOM APIs
  'unicorn/consistent-function-scoping': 'warn',    // Consistent function scoping
}
```

## Framework-Specific Rules (Optional)

### Lit Component Rules

When using Lit for web components:

```javascript
rules: {
  // Lit-specific validation
  'lit/no-legacy-template-syntax': 'error',    // Use modern Lit syntax
  'lit/no-invalid-html': 'error',              // Valid HTML in templates
  'lit/no-value-attribute': 'error',           // Proper attribute binding
  'lit/attribute-value-entities': 'error',     // Proper entity encoding
  'lit/binding-positions': 'error',            // Correct binding syntax
  'lit/no-property-change-update': 'error',    // Avoid property changes in update
  'lit/lifecycle-super': 'error',              // Call super in lifecycle methods
  'lit/no-native-attributes': 'warn',          // Avoid native attributes
}
```

### Web Components Rules

When working with custom elements:

```javascript
rules: {
  // Custom element validation
  'wc/no-constructor-attributes': 'error',     // No attributes in constructor
  'wc/no-invalid-element-name': 'error',       // Valid custom element names
  'wc/no-self-class': 'error',                 // No self-referencing classes
  'wc/require-listener-teardown': 'error',     // Clean up event listeners
  'wc/guard-super-call': 'off',                // Allow for framework components
}
```

## Environment-Specific Overrides

### Test File Overrides

Relaxed rules for test files (`**/*.test.js`, `**/test/**/*.js`, `src/test/js/**/*.js`):

- **Disable**: All JSDoc requirements, complexity rules, magic numbers, security rules, framework rules
- **Relax**: `no-unused-vars` to `warn`, `no-undef` to `off` (Jest globals)
- **Add**: Jest-specific rules (`jest/expect-expect`, `jest/no-focused-tests: 'error'`, `jest/valid-expect`)

### Production Component Overrides

Stricter rules for `src/main/resources/components/**/*.js`:

- **Enforce**: `jsdoc/require-jsdoc: 'error'`, `jsdoc/require-description: 'error'`
- **Quality**: `max-len: 120`, `complexity: 15`, `max-depth: 4`, `max-lines-per-function: 100`

### Mock File Overrides

Maximum flexibility for mock files — disable documentation, complexity, quality, and security rules:

```javascript
{
  files: ['src/test/js/mocks/**/*.js'],
  rules: {
    'jsdoc/require-jsdoc': 'off',
    'sonarjs/no-identical-functions': 'off',
    'sonarjs/cognitive-complexity': 'off',
    'complexity': 'off',
    'max-statements': 'off',
    'max-lines-per-function': 'off',
    'no-unused-vars': 'off',
    'security/detect-object-injection': 'off',
  },
}
```

## Rule Severity Levels

- **error**: Build-breaking (security vulnerabilities, syntax errors, high-risk patterns)
- **warn**: Should fix (complexity, documentation, performance, maintainability)
- **off**: Explicitly disabled (Prettier conflicts, framework exceptions, test relaxations)

## See Also

- [ESLint Configuration](eslint-configuration.md) - Flat config structure and plugin setup
- [ESLint Integration](eslint-integration.md) - Build pipeline and CI/CD integration
- `pm-dev-frontend:javascript` → [Code Quality](../../javascript/standards/code-quality.md) - JavaScript complexity limits that align with ESLint rule thresholds
