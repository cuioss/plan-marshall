# ESLint Rule Configurations

## Purpose

This document defines comprehensive ESLint rule configurations including documentation standards, security controls, code quality rules, modern JavaScript patterns, and environment-specific overrides for CUI projects.

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

Essential module management rules:

```javascript
rules: {
  'import/no-unresolved': 'off',                    // Allow unresolved imports for mocks
  'import/extensions': 'off',                       // No file extensions required
  'import/prefer-default-export': 'off',            // Allow named exports
  'import/no-extraneous-dependencies': [
    'error',
    { devDependencies: true }
  ],
}
```

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

Disable style rules handled by Prettier:

```javascript
rules: {
  // Code style rules (disabled in favor of Prettier)
  'quotes': 'off',                    // Handled by Prettier
  'semi': 'off',                      // Handled by Prettier
  'indent': 'off',                    // Handled by Prettier
  'max-len': [
    'warn',
    {
      code: 120,
      ignoreComments: true,
      ignoreUrls: true
    }
  ],
  'comma-dangle': 'off',            // Handled by Prettier
  'object-curly-spacing': 'off',    // Handled by Prettier
  'array-bracket-spacing': 'off',   // Handled by Prettier

  // Prettier integration
  'prettier/prettier': 'error',
}
```

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

### JSDoc Best Practices

**When to document**:
- All public functions and methods
- All classes and constructors
- All exported modules
- Complex algorithms or business logic

**Required tags**:
- `@param` for all parameters
- `@returns` for non-void returns
- `@throws` for error conditions
- `@example` for public APIs

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

### Security Best Practices

**Critical security rules**:
- Never use `eval()` or `Function()` constructor
- Validate all user input before use
- Avoid dynamic object property access with user input
- Use safe regex patterns to prevent ReDoS attacks
- Sanitize data before insertion into DOM

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

### SonarJS Default Rules

The recommended configuration enables these rules with error severity:

**Complexity and Maintainability**:
- `sonarjs/cognitive-complexity` - Limits cognitive complexity (default: 15)
- `sonarjs/no-identical-functions` - Detects duplicate functions
- `sonarjs/no-duplicate-string` - Detects duplicate string literals

**Code Simplification**:
- `sonarjs/no-collapsible-if` - Simplifies conditional logic
- `sonarjs/prefer-immediate-return` - Simplifies return statements
- `sonarjs/prefer-object-literal` - Enforces object literals
- `sonarjs/prefer-single-boolean-return` - Simplifies boolean returns
- `sonarjs/no-small-switch` - Warns about small switch statements
- `sonarjs/no-redundant-boolean` - Removes redundant booleans

**Dead Code Detection**:
- `sonarjs/no-unused-collection` - Detects unused collections
- `sonarjs/no-useless-catch` - Removes useless catch blocks

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
  'complexity': ['warn', { max: 10 }],                 // Cyclomatic complexity
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

Relaxed rules for test files:

```javascript
{
  files: ['**/*.test.js', '**/test/**/*.js', 'src/test/js/**/*.js'],
  rules: {
    // Disable JSDoc requirements
    'jsdoc/require-jsdoc': 'off',
    'jsdoc/require-description': 'off',
    'jsdoc/require-param-description': 'off',
    'jsdoc/require-returns-description': 'off',
    'jsdoc/require-param-type': 'off',
    'jsdoc/require-returns': 'off',

    // Relax complexity rules
    'sonarjs/cognitive-complexity': 'off',
    'sonarjs/no-duplicate-string': 'off',
    'complexity': 'off',
    'max-statements': 'off',
    'max-params': 'off',
    'max-lines-per-function': 'off',

    // Relax code quality rules
    'no-magic-numbers': 'off',
    'require-await': 'off',
    'no-unused-expressions': 'off',
    'no-unused-vars': 'warn',
    'no-undef': 'off',    // Jest globals handled by environment

    // Relax security and promise rules
    'security/detect-object-injection': 'off',
    'promise/prefer-await-to-then': 'off',
    'promise/always-return': 'off',
    'no-promise-executor-return': 'off',

    // Relax framework rules
    'unicorn/consistent-function-scoping': 'off',
    'lit/no-legacy-template-syntax': 'off',

    // Jest-specific rules
    'jest/expect-expect': [
      'error',
      {
        assertFunctionNames: ['expect', 'assert*', 'should*'],
      },
    ],
    'jest/no-disabled-tests': 'warn',
    'jest/no-focused-tests': 'error',
    'jest/prefer-to-have-length': 'error',
    'jest/valid-expect': 'error',
  },
}
```

### Production Component Overrides

Stricter rules for production code:

```javascript
{
  files: ['src/main/resources/components/**/*.js'],
  rules: {
    // Enforce documentation
    'jsdoc/require-jsdoc': 'error',           // Require JSDoc for public components
    'jsdoc/require-description': 'error',     // Require descriptions

    // Enforce quality standards
    'max-len': ['warn', { code: 120 }],       // Line length limit
    'complexity': ['warn', { max: 15 }],      // Cyclomatic complexity
    'max-depth': ['error', { max: 4 }],       // Maximum nesting depth
    'max-lines-per-function': ['warn', { max: 100 }], // Function length limit
  },
}
```

### Mock File Overrides

Maximum flexibility for mock files:

```javascript
{
  files: ['src/test/js/mocks/**/*.js'],
  rules: {
    // Disable all documentation requirements
    'jsdoc/require-jsdoc': 'off',

    // Disable all complexity rules
    'sonarjs/no-identical-functions': 'off',
    'sonarjs/cognitive-complexity': 'off',
    'complexity': 'off',
    'max-statements': 'off',
    'max-lines-per-function': 'off',

    // Disable code quality rules
    'unicorn/consistent-function-scoping': 'off',
    'unicorn/no-array-reduce': 'off',
    'unicorn/prefer-logical-operator-over-ternary': 'off',
    'no-restricted-syntax': 'off',
    'no-plusplus': 'off',
    'class-methods-use-this': 'off',
    'no-unused-vars': 'off',

    // Disable security rules
    'security/detect-object-injection': 'off',
    'promise/prefer-await-to-then': 'off',
    'promise/always-return': 'off',
    'no-promise-executor-return': 'off',
  },
}
```

## Rule Severity Levels

### Severity Definitions

**error**: Build-breaking issues that must be fixed immediately
- Security vulnerabilities
- Syntax errors
- Clear violations of standards
- High-risk patterns

**warn**: Issues that should be addressed but don't break builds
- Complexity warnings
- Documentation suggestions
- Performance considerations
- Maintainability concerns

**off**: Rules that are explicitly disabled
- Conflicts with Prettier
- Framework-specific exceptions
- Test environment relaxations
- False positive patterns

## Best Practices

1. **Start with recommended configs** - Use plugin recommended settings as baseline
2. **Override sparingly** - Only customize rules when necessary for project needs
3. **Document exceptions** - Comment why rules are disabled or customized
4. **Use environment overrides** - Relax rules for tests, strict for production
5. **Enable security rules** - Always keep security rules at error severity
6. **Balance quality and productivity** - Avoid overly restrictive rules
7. **Review regularly** - Periodically review rule configuration for relevance
8. **Test configuration** - Verify rules work as expected on sample code
9. **Consider team feedback** - Adjust rules based on team experience
10. **Keep plugins updated** - Update plugins to get latest rule improvements
