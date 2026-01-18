# JSDoc Documentation Standards

## Overview

JSDoc documentation standards for CUI JavaScript projects covering functions, classes, modules, types, and web components.

## Purpose

Ensures consistent, high-quality JavaScript documentation through:
- Standardized JSDoc patterns for all code elements
- ESLint integration for automated validation
- Clear writing style guidelines
- Type safety through JSDoc annotations

## Standards Included

1. **jsdoc-essentials.md** - Core JSDoc syntax, tags, ESLint setup, requirements
2. **jsdoc-patterns.md** - Quick reference patterns for functions, classes, modules, types, web components

## Key Features

### Documentation Requirements
- **Mandatory**: Public functions, classes, exported modules, complex logic
- **Optional**: Private methods, simple utilities
- **Required tags**: @param, @returns, @throws, @example
- **Optional tags**: @since, @author, @see, @deprecated

### ESLint Integration
- **eslint-plugin-jsdoc** for automated validation
- Enforces description, parameter, and return documentation
- Type checking using JSDoc annotations

## Quick Examples

### Function
```javascript
/**
 * Calculates the total price including tax.
 *
 * @param {number} price - Base price before tax
 * @param {number} taxRate - Tax rate as decimal
 * @returns {number} Total price including tax
 * @throws {Error} When price or taxRate is negative
 * @example
 * const total = calculateTotalPrice(100, 0.08); // 108
 */
function calculateTotalPrice(price, taxRate) {
  // Implementation
}
```

### Class
```javascript
/**
 * Manages JWT token validation.
 *
 * @class JWTManager
 * @example
 * const manager = new JWTManager({ issuer: 'https://auth.example.com' });
 * const isValid = await manager.validateToken(token);
 */
class JWTManager {
  constructor(config) { /* ... */ }
  async validateToken(token) { /* ... */ }
}
```

### Web Component
```javascript
/**
 * JWT Configuration component.
 *
 * @customElement qwc-jwt-config
 * @extends {LitElement}
 * @fires config-changed - When configuration updates
 * @cssproperty --jwt-primary-color - Primary theme color
 */
class QwcJwtConfig extends LitElement {
  // Implementation
}
```

## When to Use

Activate when:
- Writing/documenting JavaScript code
- Creating web components
- Reviewing documentation quality
- Setting up JSDoc/ESLint integration
- Refactoring code

## Getting Started

1. **Install ESLint JSDoc plugin**
   ```json
   "devDependencies": {
     "eslint-plugin-jsdoc": "^46.8.0"
   }
   ```

2. **Configure ESLint**
   ```javascript
   module.exports = {
     extends: ['plugin:jsdoc/recommended'],
     rules: {
       'jsdoc/require-description': 'error',
       'jsdoc/require-param-description': 'error'
     }
   };
   ```

3. **Activate skill and document code**
4. **Run ESLint** to validate

## Best Practices

1. Document as you code
2. Be specific about behavior and constraints
3. Document all error conditions
4. Provide realistic examples
5. Keep docs synchronized with code
6. Validate with ESLint

## Integration

Works with:
- **cui-javascript** - Core JavaScript development standards
- **cui-javascript-unit-testing** - Test documentation
- **cui-css** - CSS documentation patterns

## Resources

- `jsdoc-essentials.md` - Core requirements and setup
- `jsdoc-patterns.md` - Pattern reference for all code types
- [JSDoc Official](https://jsdoc.app/)
- [eslint-plugin-jsdoc](https://github.com/gajus/eslint-plugin-jsdoc)
