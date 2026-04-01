# JavaScript Suppression Syntax

How to suppress various types of findings in JavaScript code.

## ESLint Suppressions

### Line-Level Suppression

```javascript
// Disable specific rule for next line
// eslint-disable-next-line no-console
console.log('Debug message');

// Disable multiple rules for next line
// eslint-disable-next-line no-console, no-debugger
console.log('Debug'); debugger;

// Disable on same line
console.log('Debug'); // eslint-disable-line no-console
```

### Block-Level Suppression

```javascript
/* eslint-disable no-console */
console.log('First');
console.log('Second');
/* eslint-enable no-console */
```

### File-Level Suppression

```javascript
// At top of file - disables for entire file
/* eslint-disable no-console */

// Rest of file...
```

### With Justification (Recommended)

```javascript
// eslint-disable-next-line no-console -- Required for debugging production issues
console.log('Critical diagnostic:', data);
```

## Stylelint Suppressions

### Line-Level

```css
.class {
  /* stylelint-disable-next-line property-no-unknown */
  custom-property: value;
}
```

### Block-Level

```css
/* stylelint-disable selector-class-pattern */
.myLegacyClass {
  color: red;
}
/* stylelint-enable selector-class-pattern */
```

### File-Level

```css
/* stylelint-disable */
/* All rules disabled for this file */
```

## Prettier

Prettier formatting cannot be suppressed inline. Options:

1. **Fix the formatting** (recommended)
2. **Configure `.prettierrc`** to allow the pattern
3. **Add to `.prettierignore`** for files that shouldn't be formatted

```
# .prettierignore
**/generated/**
**/vendor/**
legacy-file.js
```

## Configuration-Level Suppressions

### ESLint Config (eslint.config.js)

```javascript
export default [
  {
    files: ['**/generated/**'],
    rules: {
      'no-console': 'off',
    },
  },
];
```

## Jest Test Suppressions

### Expected Errors in Tests

```javascript
// Test that function throws
expect(() => {
  processData('invalid');
}).toThrow();
```

## Best Practices

### Always Include Justification

```javascript
// Preferred: Explains why suppression is appropriate
// eslint-disable-next-line no-console -- Temporary debug for JIRA-123
console.log(diagnosticData);

// Avoid: No explanation
// eslint-disable-next-line no-console
console.log(diagnosticData);
```

### Scope Minimally

```javascript
// Preferred: Suppresses only the specific line
// eslint-disable-next-line no-console
console.log('Debug');
doSomething();

// Avoid: Suppresses entire block
/* eslint-disable no-console */
console.log('Debug');
doSomething(); // This line is also covered unnecessarily
/* eslint-enable no-console */
```

### Use ESLint Ignores for Directories

In `eslint.config.js` (flat config):

```javascript
export default [
  {
    ignores: ['**/generated/**', '**/dist/**', '**/node_modules/**', 'coverage/'],
  },
  // ... other configs
];
```

## When NOT to Suppress

- Security-related rules (no-eval, no-implied-eval)
- Accessibility rules (jsx-a11y rules)
- Issues that can be fixed with minimal effort
- Issues in new code (only suppress in legacy)

## See Also

- [Severity Guidelines](severity.md) - Decision criteria for handling findings by severity and context
