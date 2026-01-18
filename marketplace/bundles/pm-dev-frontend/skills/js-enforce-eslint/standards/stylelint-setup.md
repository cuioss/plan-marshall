# StyleLint Configuration for CSS-in-JS

## Purpose

This document defines StyleLint configuration standards for CSS-in-JS patterns in web components, particularly for Lit components, ensuring consistent CSS styling and quality across CUI projects.

## When to Use StyleLint

StyleLint should be configured for projects that:

- Use Lit components with CSS-in-JS template literals
- Implement custom elements with inline styles
- Have CSS defined within JavaScript files
- Require CSS property validation and ordering
- Need CSS custom property (CSS variables) validation

## Required Dependencies

### StyleLint Core Dependencies

Install StyleLint and essential plugins:

```json
{
  "devDependencies": {
    "stylelint": "^16.10.0",
    "stylelint-config-standard": "^36.0.1",
    "stylelint-order": "^6.0.3",
    "stylelint-declaration-strict-value": "^1.10.6",
    "postcss-lit": "^1.0.0"
  }
}
```

### Dependency Purposes

- **stylelint**: Core StyleLint engine for CSS linting
- **stylelint-config-standard**: Standard CSS rules and best practices
- **stylelint-order**: CSS property ordering and organization
- **stylelint-declaration-strict-value**: CSS custom property enforcement
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
    'stylelint-order',
    'stylelint-declaration-strict-value'
  ],

  // Custom syntax for CSS-in-JS
  customSyntax: 'postcss-lit',

  rules: {
    // Modern CSS formatting
    'color-hex-length': 'short',

    // Logical property ordering
    'order/properties-order': [
      'content', 'display', 'position', 'top', 'right', 'bottom', 'left',
      'z-index', 'flex', 'flex-grow', 'flex-shrink', 'flex-basis',
      'width', 'height', 'margin', 'padding', 'border', 'background',
      'color', 'font', 'text-align', 'opacity', 'transform', 'transition'
    ],

    // CSS Custom Properties enforcement
    'scale-unlimited/declaration-strict-value': [
      ['/color$/', 'fill', 'stroke', 'background-color'],
      {
        'ignoreValues': [
          'currentColor', 'transparent', 'inherit', 'initial', 'unset'
        ]
      }
    ],

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

### CSS Custom Properties

Enforce use of CSS custom properties (variables) for colors and theming:

```javascript
'scale-unlimited/declaration-strict-value': [
  // Properties that must use custom properties
  ['/color$/', 'fill', 'stroke', 'background-color'],
  {
    // Allowed standard values
    'ignoreValues': [
      'currentColor',   // Inherit current text color
      'transparent',    // Fully transparent
      'inherit',        // Inherit from parent
      'initial',        // CSS initial value
      'unset'          // Unset value
    ]
  }
]
```

**Example**:
```javascript
// Correct - using CSS custom property
static styles = css`
  .button {
    background-color: var(--primary-color);
    color: var(--text-color);
  }
`;

// Incorrect - hardcoded color
static styles = css`
  .button {
    background-color: #007bff;  // Error: use CSS custom property
    color: #ffffff;              // Error: use CSS custom property
  }
`;
```

### Custom Property Naming

Enforce kebab-case naming for CSS custom properties:

```javascript
'custom-property-pattern': '^[a-z][a-z0-9]*(-[a-z0-9]+)*$'
```

**Examples**:
```css
/* Correct */
--primary-color: #007bff;
--text-size-large: 1.5rem;
--spacing-unit: 8px;

/* Incorrect */
--primaryColor: #007bff;      /* camelCase not allowed */
--PRIMARY_COLOR: #007bff;     /* UPPER_CASE not allowed */
--text--size: 1rem;           /* double dash not allowed */
```

### Web Component Pseudo-classes

Allow web component-specific pseudo-classes:

```javascript
'selector-pseudo-class-no-unknown': [
  true,
  {
    ignorePseudoClasses: ['host', 'host-context', 'focus-visible'],
  },
]
```

**Example**:
```javascript
static styles = css`
  :host {
    display: block;
    padding: 1rem;
  }

  :host-context(.dark-mode) {
    background-color: var(--dark-background);
  }

  button:focus-visible {
    outline: 2px solid var(--focus-color);
  }
`;
```

### Complexity Limits

Enforce maintainability through complexity limits:

```javascript
'max-nesting-depth': 3,                    // Maximum nesting levels
'selector-max-id': 0,                      // No ID selectors
'selector-max-universal': 1,               // Limit universal selectors
'selector-max-compound-selectors': 4,      // Limit compound selectors
```

## NPM Scripts Integration

### Required Scripts

Add StyleLint scripts to package.json:

```json
{
  "scripts": {
    "lint:style": "stylelint src/**/*.js",
    "lint:style:fix": "stylelint --fix src/**/*.js",
    "validate:css": "npm run lint:style && npm run format:check"
  }
}
```

### Combined Linting Scripts

Integrate with ESLint for comprehensive linting:

```json
{
  "scripts": {
    "lint:js": "eslint src/**/*.js",
    "lint:js:fix": "eslint --fix src/**/*.js",
    "lint:style": "stylelint src/**/*.js",
    "lint:style:fix": "stylelint --fix src/**/*.js",
    "lint": "npm run lint:js && npm run lint:style",
    "lint:fix": "npm run lint:js:fix && npm run lint:style:fix"
  }
}
```

## Maven Integration

### Frontend Maven Plugin Configuration

Integrate StyleLint into Maven build process:

```xml
<execution>
  <id>npm-css-validate</id>
  <goals>
    <goal>npm</goal>
  </goals>
  <phase>verify</phase>
  <configuration>
    <arguments>run validate:css</arguments>
  </configuration>
</execution>
```

### Build Order

Recommended Maven execution order:

1. **install-node-and-npm** (initialize phase)
2. **npm-install** (initialize phase)
3. **npm-lint-fix** (verify phase) - ESLint with auto-fix
4. **npm-css-validate** (verify phase) - StyleLint validation

## Environment-Specific Configuration

### Production Component Overrides

Stricter rules for production code:

```javascript
overrides: [
  {
    files: ['src/main/resources/components/**/*.js'],
    rules: {
      'max-nesting-depth': 3,                      // Enforce shallow nesting
      'selector-max-compound-selectors': 4,        // Limit selector complexity
      'selector-max-specificity': '0,4,0',         // Limit specificity
      'declaration-block-no-redundant-longhand-properties': true,
    },
  },
]
```

### Test File Overrides

Relaxed rules for test files:

```javascript
overrides: [
  {
    files: ['src/test/js/**/*.js', '**/*.test.js'],
    rules: {
      'selector-class-pattern': null,              // Allow any class names
      'custom-property-pattern': null,             // Allow any custom property names
      'max-nesting-depth': null,                   // No nesting limits
      'selector-max-compound-selectors': null,     // No selector complexity limits
    },
  },
]
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

### Issue: Framework-Specific Theme Variables

**Problem**: Configuration includes unnecessary framework-specific patterns

**Solution**: Use generic patterns unless specific framework integration required

```javascript
// Generic (preferred)
'custom-property-pattern': '^[a-z][a-z0-9]*(-[a-z0-9]+)*$'

// Framework-specific (only when needed)
'custom-property-pattern': '^(lumo|vaadin)-[a-z0-9]+(-[a-z0-9]+)*$'
```

### Issue: ES Module Import Errors

**Problem**: `Cannot use import statement outside a module`

**Solution**: Use `export default` syntax when `"type": "module"` is set in package.json

```javascript
// Correct - ES module
export default {
  extends: ['stylelint-config-standard'],
  // ... configuration
};

// Incorrect - CommonJS (not supported with "type": "module")
module.exports = {
  extends: ['stylelint-config-standard'],
  // ... configuration
};
```

### Issue: postcss-lit Parser Errors

**Problem**: StyleLint fails to parse CSS in template literals

**Solution**: Ensure postcss-lit is configured as customSyntax

```javascript
export default {
  customSyntax: 'postcss-lit',  // Required for Lit components
  // ... rest of configuration
};
```

## Best Practices

1. **Use CSS custom properties** - Enforce variables for colors and theming
2. **Order properties logically** - Group related properties together
3. **Limit nesting depth** - Keep CSS flat and maintainable (max 3 levels)
4. **Avoid ID selectors** - Use classes for component styling
5. **Follow kebab-case naming** - Consistent custom property naming
6. **Integrate with build** - Run StyleLint in Maven verify phase
7. **Relax for tests** - Less strict rules for test files
8. **Enable auto-fix** - Use lint:style:fix to automatically correct issues
9. **Document exceptions** - Comment any rule overrides or disabled rules
10. **Keep updated** - Regularly update StyleLint and plugins

## Validation Checklist

- [ ] StyleLint installed with all required plugins
- [ ] .stylelintrc.js configured with ES module syntax
- [ ] postcss-lit configured as customSyntax
- [ ] CSS custom property pattern defined
- [ ] Property ordering configured
- [ ] Web component pseudo-classes allowed
- [ ] package.json includes lint:style scripts
- [ ] Maven pom.xml includes CSS validation execution
- [ ] Environment-specific overrides configured
- [ ] Documentation updated with StyleLint procedures

## Example Lit Component with StyleLint

```javascript
import { LitElement, html, css } from 'lit';

export class ExampleButton extends LitElement {
  static styles = css`
    /* Properties in logical order */
    :host {
      display: inline-block;
    }

    .button {
      /* Layout */
      display: flex;
      position: relative;

      /* Flexbox */
      justify-content: center;
      align-items: center;

      /* Box Model */
      padding: 0.5rem 1rem;
      margin: 0.25rem;

      /* Border */
      border: 1px solid var(--border-color);
      border-radius: 4px;

      /* Background and colors using custom properties */
      background-color: var(--button-background);
      color: var(--button-text);

      /* Typography */
      font-family: var(--font-family);
      font-size: 1rem;

      /* Effects */
      transition: background-color 0.2s ease;
    }

    .button:hover {
      background-color: var(--button-background-hover);
    }

    /* Web component specific pseudo-class */
    :host([disabled]) .button {
      opacity: 0.5;
      background-color: var(--button-disabled);
    }
  `;

  render() {
    return html`
      <button class="button">
        <slot></slot>
      </button>
    `;
  }
}
```
