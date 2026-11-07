# StyleLint Configuration for CSS-in-JS

## Purpose

StyleLint configuration standards for **CSS-in-JS patterns in web components** (Lit). This document does not cover pure CSS file linting — for standalone `.css` files, use Stylelint with `stylelint-config-standard` directly (see [CSS Quality & Tooling](../../css/standards/css-quality-tooling.md) for tooling setup).

## When to Use StyleLint

Configure StyleLint with `postcss-lit` for projects that:

- Use Lit components with CSS-in-JS template literals (`css\`...\``)
- Implement custom elements with inline styles in JavaScript
- Have CSS defined within JavaScript files
- Need CSS custom property validation within components

## Required Dependencies

### StyleLint Core Dependencies

Install StyleLint and essential plugins:

```json
{
  "devDependencies": {
    "stylelint": "^17.0.0",
    "stylelint-config-standard": "^40.0.0",
    "stylelint-order": "^7.0.1",
    "postcss-lit": "^1.3.1"
  }
}
```

### Dependency Purposes

- **stylelint**: Core StyleLint engine for CSS linting
- **stylelint-config-standard**: Standard CSS rules and best practices
- **stylelint-order**: CSS property ordering and organization
- **postcss-lit**: PostCSS parser for CSS in Lit template literals


## StyleLint Configuration

### ES Module Configuration

Create `.stylelintrc.js` with ES module syntax (when `"type": "module"` is set):

```javascript
/**
 * StyleLint configuration for CSS-in-JS in web components
 *
 * This configuration ensures consistent CSS styling within
 * component template literals and CSS-in-JS constructs.
 */

export default {
  extends: [
    'stylelint-config-standard'
  ],

  plugins: [
    'stylelint-order'
  ],

  // Custom syntax for CSS-in-JS
  customSyntax: 'postcss-lit',

  rules: {
    // Modern CSS formatting
    'color-hex-length': 'short',
    'color-named': 'never',

    // Enforce CSS custom properties for color values
    'declaration-property-value-allowed-list': {
      'color': ['/^var\\(--/', 'currentColor', 'inherit', 'initial', 'unset', 'transparent'],
      'background-color': ['/^var\\(--/', 'currentColor', 'inherit', 'initial', 'unset', 'transparent'],
      'border-color': ['/^var\\(--/', 'currentColor', 'inherit', 'initial', 'unset', 'transparent'],
      'fill': ['/^var\\(--/', 'currentColor', 'inherit', 'initial', 'unset', 'transparent'],
      'stroke': ['/^var\\(--/', 'currentColor', 'inherit', 'initial', 'unset', 'transparent'],
    },

    // Logical property ordering (see "Property Ordering" section below for full list)
    'order/properties-order': [ /* ... */ ],

    // CSS Custom Properties patterns
    'custom-property-pattern': '^[a-z][a-z0-9]*(-[a-z0-9]+)*$',
    'custom-property-empty-line-before': 'never',

    // Web component-specific CSS patterns
    'selector-pseudo-class-no-unknown': [
      true,
      {
        ignorePseudoClasses: ['host', 'host-context', 'focus-visible'],
      },
    ],

    // Performance and maintainability
    'max-nesting-depth': 3,
    'selector-max-id': 0,
    'selector-max-universal': 1,

    // Disable rules that conflict with CSS-in-JS
    'no-empty-source': null,
    'value-keyword-case': null,
  },

  overrides: [
    {
      files: ['src/main/resources/components/**/*.js'],
      rules: {
        // Stricter rules for production components
        'max-nesting-depth': 3,
        'selector-max-compound-selectors': 4,
      },
    },
    {
      files: ['src/test/js/**/*.js'],
      rules: {
        // Relaxed rules for test files
        'selector-class-pattern': null,
        'custom-property-pattern': null,
      },
    },
  ],
};
```

## Rule Configuration Details

### Property Ordering

Enforce logical CSS property order for consistency and readability:

```javascript
'order/properties-order': [
  // Layout
  'content',
  'display',
  'position',
  'top', 'right', 'bottom', 'left',
  'z-index',

  // Flexbox
  'flex', 'flex-grow', 'flex-shrink', 'flex-basis',
  'flex-direction', 'flex-wrap', 'justify-content', 'align-items',

  // Box Model
  'width', 'height',
  'min-width', 'max-width',
  'min-height', 'max-height',
  'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
  'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',

  // Border
  'border', 'border-width', 'border-style', 'border-color',
  'border-radius',

  // Background
  'background', 'background-color', 'background-image',
  'background-position', 'background-size', 'background-repeat',

  // Typography
  'color',
  'font', 'font-family', 'font-size', 'font-weight',
  'line-height', 'letter-spacing',
  'text-align', 'text-decoration', 'text-transform',

  // Visual Effects
  'opacity',
  'box-shadow',
  'transform',
  'transition',
  'animation'
]
```

### Color Enforcement

Use `color-named: never` and `declaration-property-value-allowed-list` (shown in config above) to enforce `var(--*)` custom properties for all color properties. Hardcoded hex values or named colors are rejected.

### Custom Property Naming

Pattern `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` enforces kebab-case: `--primary-color` (correct), `--primaryColor` (rejected).

### Web Component Pseudo-classes

The `ignorePseudoClasses: ['host', 'host-context', 'focus-visible']` config allows `:host`, `:host-context()`, and `:focus-visible` selectors.

## NPM Scripts

```json
{
  "scripts": {
    "lint:style": "stylelint src/**/*.js",
    "lint:style:fix": "stylelint --fix src/**/*.js"
  }
}
```

Integrate with ESLint via combined `lint` / `lint:fix` scripts (see [eslint-integration.md](eslint-integration.md)).

## Maven Integration

Add StyleLint in the **verify** phase via frontend-maven-plugin:

```xml
<execution>
  <id>npm-css-validate</id>
  <goals><goal>npm</goal></goals>
  <phase>verify</phase>
  <configuration><arguments>run lint:style</arguments></configuration>
</execution>
```

## Common Configuration Issues

### Issue: Duplicate Rule Definitions

**Problem**: Same rule appears multiple times in configuration

**Symptoms**: `There are duplicate names used: property-no-unknown`

**Solution**: Remove duplicate rule definitions, keep only one instance per rule

```javascript
// Incorrect - duplicate rules
rules: {
  'property-no-unknown': true,
  'property-no-unknown': [true, { ignoreProperties: ['composes'] }],  // Duplicate
}

// Correct - single rule definition
rules: {
  'property-no-unknown': [true, { ignoreProperties: ['composes'] }],
}
```

### Issue: ES Module Import Errors

Use `export default` syntax when `"type": "module"` is set. CommonJS `module.exports` is not supported.

### Issue: postcss-lit Parser Errors

Ensure `customSyntax: 'postcss-lit'` is set in the config. This is required for Lit template literal parsing.
