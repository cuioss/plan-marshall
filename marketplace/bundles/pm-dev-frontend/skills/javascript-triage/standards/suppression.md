# JavaScript/TypeScript Suppression Syntax

How to suppress various types of findings in JavaScript and TypeScript code.

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

## TypeScript Suppressions

### @ts-ignore

Ignores TypeScript error on next line. **Use sparingly**.

```typescript
// @ts-ignore - Legacy API returns untyped data
const result = legacyApi.getData();
```

### @ts-expect-error (Preferred)

Same as `@ts-ignore` but fails if there's no error. **Preferred** because it fails when fix makes it unnecessary.

```typescript
// @ts-expect-error - Testing error handling with invalid input
processData(null);
```

### @ts-nocheck

Disables TypeScript checking for entire file. **Use only for legacy JS files**.

```typescript
// @ts-nocheck
// Legacy JavaScript file pending migration
```

### Type Assertions

For type-related issues, prefer proper typing over suppression:

```typescript
// Instead of @ts-ignore, use assertion
const element = document.getElementById('app') as HTMLDivElement;

// Or type guard
if (element instanceof HTMLDivElement) {
  element.style.display = 'none';
}
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

### TypeScript Config (tsconfig.json)

```json
{
  "compilerOptions": {
    "skipLibCheck": true
  },
  "exclude": ["**/generated/**"]
}
```

## Jest/Vitest Test Suppressions

### Expected Errors in Tests

```typescript
// Test that function throws
expect(() => {
  // @ts-expect-error - Testing with invalid input type
  processData('invalid');
}).toThrow();
```

### Mocking Types

```typescript
// When mock doesn't match full interface
const mockService = {
  getData: jest.fn(),
} as unknown as DataService; // Type assertion for partial mock
```

## Best Practices

### Always Include Justification

```javascript
// Good - explains why suppression is appropriate
// eslint-disable-next-line no-console -- Temporary debug for JIRA-123
console.log(diagnosticData);

// Bad - no explanation
// eslint-disable-next-line no-console
console.log(diagnosticData);
```

### Prefer @ts-expect-error Over @ts-ignore

```typescript
// Good - will fail when error is fixed
// @ts-expect-error - Legacy API returns untyped data
const result = oldApi.fetch();

// Avoid - stays silent even when unnecessary
// @ts-ignore
const result = oldApi.fetch();
```

### Scope Minimally

```javascript
// Good - suppresses only the specific line
// eslint-disable-next-line no-console
console.log('Debug');
doSomething();

// Avoid - suppresses entire block
/* eslint-disable no-console */
console.log('Debug');
doSomething(); // This line is also covered unnecessarily
/* eslint-enable no-console */
```

### Use .eslintignore for Directories

```
# .eslintignore
**/generated/**
**/dist/**
**/node_modules/**
coverage/
```

## When NOT to Suppress

- Security-related rules (no-eval, no-implied-eval)
- Type safety rules in new TypeScript code
- Accessibility rules (jsx-a11y rules)
- Issues that can be fixed with minimal effort
- Issues in new code (only suppress in legacy)
