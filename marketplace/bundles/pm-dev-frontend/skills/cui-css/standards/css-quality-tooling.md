# CSS Quality & Tooling

Performance optimization, accessibility standards, dark mode implementation, and development tools setup for CUI projects.

## Performance

### Efficient Selectors

```css
/* ✅ Fast - single class */
.button { }
.card__header { }

/* ❌ Slow - deep nesting */
.header .nav ul li a span { }

/* ❌ Slow - attribute without tag */
[type="text"] { }

/* ✅ Better */
input[type="text"] { }
```

### Minimize Specificity

```css
/* ❌ High specificity (1,3,1) */
#sidebar .widget .title span { }

/* ✅ Low specificity (0,1,0) */
.widget-title { }
```

Low specificity is easier to override and prevents specificity wars.

### Avoid Expensive Properties

Use sparingly: `box-shadow`, `border-radius`, `filter`, `transform`, `opacity`

```css
/* ✅ Apply on state change only */
.button {
  transition: transform 0.2s;
}

.button:hover {
  transform: translateY(-2px);
}

/* ❌ Animated constantly */
.element {
  animation: pulse 1s infinite;
}
```

### CSS Containment

Isolate layout calculations:

```css
.card {
  contain: layout;
}

.sidebar {
  contain: size layout;
}
```

### Critical CSS

Inline above-the-fold styles:

```html
<head>
  <style>
    /* Critical CSS - inline */
    body { margin: 0; font-family: sans-serif; }
    .header { /* ... */ }
  </style>

  <!-- Load rest async -->
  <link rel="preload" href="styles.css" as="style" onload="this.rel='stylesheet'">
</head>
```

### Reduce Bundle Size

- Use PurgeCSS in build
- Minify with cssnano/csso
- Enable gzip/brotli compression
- Code splitting by route

## Accessibility

### Focus Management

```css
/* ❌ Never remove outlines globally */
* {
  outline: none;
}

/* ✅ Use :focus-visible for keyboard-only focus */
*:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(25, 118, 210, 0.1);
}
```

**Skip to Content Link:**

```css
.skip-to-content {
  position: absolute;
  left: -9999px;
}

.skip-to-content:focus {
  position: fixed;
  top: 1rem;
  left: 1rem;
  background: var(--color-primary);
  color: white;
  padding: 1rem;
  z-index: 999;
}
```

### Color Contrast

**WCAG AA Standards:**
- Normal text: 4.5:1 contrast ratio
- Large text (18pt+/14pt+ bold): 3:1
- UI components: 3:1

```css
/* ✅ Good contrast */
.button {
  background: #1976d2;  /* Blue */
  color: #ffffff;       /* White - 4.54:1 */
}

/* ❌ Poor contrast */
.button {
  background: #64b5f6;  /* Light blue */
  color: #ffffff;       /* White - 2.46:1 - FAIL */
}
```

**Test with:** Browser DevTools, WebAIM Contrast Checker

### Motion and Animation

Respect user preferences:

```css
/* Default: animations enabled */
.element {
  transition: transform 0.3s ease;
}

.element:hover {
  transform: scale(1.05);
}

/* Respect prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Screen Reader Considerations

**Visually Hidden:**

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

**Interactive States:**

```css
/* Ensure disabled elements are clear */
.button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Loading states */
.button[aria-busy="true"] {
  position: relative;
  color: transparent;
}

.button[aria-busy="true"]::after {
  content: '';
  position: absolute;
  width: 1rem;
  height: 1rem;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
```

### Touch Targets

Minimum 44x44px:

```css
.button,
.link {
  min-height: 44px;
  min-width: 44px;
  padding: 0.75rem 1rem;
}
```

## Dark Mode

### System Preference

```css
:root {
  --bg-primary: white;
  --text-primary: #1c1b1f;
  --border-primary: #e0e0e0;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #121212;
    --text-primary: #e6e1e5;
    --border-primary: #3d3d3d;
  }
}

/* Components automatically adapt */
.page {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}
```

### Manual Toggle

```css
[data-theme="light"] {
  --bg-primary: white;
  --text-primary: #1c1b1f;
}

[data-theme="dark"] {
  --bg-primary: #121212;
  --text-primary: #e6e1e5;
}
```

```javascript
// Toggle theme
document.documentElement.setAttribute('data-theme', theme);
localStorage.setItem('theme', theme);
```

## Maintainability

### DRY Principle

```css
/* ❌ Repetitive */
.button-primary {
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  font-weight: 500;
}

.button-secondary {
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  font-weight: 500;
}

/* ✅ Use shared class + modifier */
.button {
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  font-weight: 500;
}

.button--primary { /* variant styles */ }
.button--secondary { /* variant styles */ }
```

### Avoid Magic Numbers

```css
/* ❌ What is 23px? */
.element {
  margin-top: 23px;
}

/* ✅ Use variables with semantic names */
.element {
  margin-top: var(--spacing-md);
}
```

### Documentation

```css
/**
 * Complex component requiring explanation
 *
 * This uses a specific technique because...
 * Browser-specific workaround for Safari...
 */
.complex-component {
  /* Specific fix for IE11 grid bug */
  display: -ms-grid;
}
```

## Development Tools

### Package.json Setup

```json
{
  "devDependencies": {
    "postcss": "^8.4.0",
    "postcss-cli": "^10.0.0",
    "autoprefixer": "^10.4.0",
    "postcss-preset-env": "^9.0.0",
    "postcss-import": "^15.0.0",
    "postcss-nested": "^6.0.0",
    "stylelint": "^15.0.0",
    "stylelint-config-standard": "^34.0.0",
    "stylelint-order": "^6.0.0",
    "prettier": "^3.0.0",
    "csso-cli": "^4.0.0",
    "purgecss": "^5.0.0"
  },
  "scripts": {
    "css:dev": "postcss src/css/**/*.css --dir dist/css --watch",
    "css:build": "postcss src/css/**/*.css --dir dist/css --env production",
    "css:lint": "stylelint 'src/css/**/*.css'",
    "css:lint:fix": "stylelint 'src/css/**/*.css' --fix",
    "css:format": "prettier --write 'src/css/**/*.css'",
    "css:purge": "purgecss --css dist/css/*.css --content 'src/**/*.html' --output dist/css",
    "css:quality": "npm run css:lint && npm run css:format:check"
  }
}
```

### PostCSS Configuration

Create `postcss.config.js`:

```javascript
module.exports = (ctx) => {
  const isDev = ctx.env !== 'production';

  return {
    plugins: {
      'postcss-import': {},
      'postcss-nested': {},
      'postcss-preset-env': {
        stage: isDev ? 0 : 1
      },
      'autoprefixer': {
        grid: 'autoplace'
      },
      'csso': isDev ? false : {
        comments: false
      }
    }
  };
};
```

**What PostCSS Does:**
- **postcss-import** - Inlines `@import` statements
- **postcss-nested** - Sass-like nesting support
- **postcss-preset-env** - Modern CSS features with fallbacks
- **autoprefixer** - Adds vendor prefixes automatically
- **csso** - Minifies CSS in production

### Stylelint Configuration

Create `.stylelintrc.js`:

```javascript
module.exports = {
  extends: [
    'stylelint-config-standard',
    'stylelint-config-prettier'
  ],
  plugins: [
    'stylelint-order'
  ],
  rules: {
    // Enforce property order
    'order/properties-order': [
      'content',
      'display',
      'position',
      'top',
      'right',
      'bottom',
      'left',
      'z-index',
      'flex-direction',
      'justify-content',
      'align-items',
      'gap',
      'width',
      'height',
      'margin',
      'padding',
      'border',
      'background',
      'color',
      'font-family',
      'font-size',
      'line-height',
      'opacity',
      'cursor',
      'transform',
      'transition'
    ],

    // Naming
    'selector-class-pattern': '^[a-z][a-z0-9]*(-[a-z0-9]+)*(__[a-z0-9]+(-[a-z0-9]+)*)?(--[a-z0-9]+(-[a-z0-9]+)*)?$',

    // Best practices
    'selector-max-id': 0,
    'selector-max-specificity': '0,4,0',
    'selector-max-compound-selectors': 3,
    'max-nesting-depth': 3,
    'color-named': 'never',
    'declaration-no-important': true
  }
};
```

### Prettier Configuration

Create `.prettierrc`:

```json
{
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "semi": true,
  "singleQuote": true,
  "trailingComma": "es5",
  "bracketSpacing": true
}
```

### IDE Integration

**VS Code** - `.vscode/settings.json`:

```json
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "css.validate": false,
  "stylelint.validate": ["css"],
  "[css]": {
    "editor.codeActionsOnSave": {
      "source.fixAll.stylelint": true
    }
  }
}
```

### Build Pipeline

**Development:**
```bash
npm run css:dev  # Watch and rebuild
```

**Production:**
```bash
npm run css:build  # Minify and optimize
npm run css:purge  # Remove unused CSS
```

**Quality Checks:**
```bash
npm run css:lint       # Check linting
npm run css:format:check  # Check formatting
npm run css:quality    # Both checks
```

### PurgeCSS Setup

Create `purgecss.config.js`:

```javascript
module.exports = {
  content: [
    './src/**/*.html',
    './src/**/*.js'
  ],
  css: ['./dist/css/**/*.css'],
  output: './dist/css',
  safelist: {
    standard: ['is-active', 'is-open', 'is-loading'],
    deep: [/^data-/, /^aria-/],
    greedy: [/^modal-/, /^dropdown-/]
  }
};
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: CSS Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run css:quality
      - run: npm run css:build
```

## Performance Metrics

### Target Metrics

- CSS Bundle Size: < 50KB gzipped
- First Paint: < 1s
- Layout Shifts (CLS): < 0.1
- No unused CSS: > 90% used

### Monitoring

```bash
# Check bundle size
ls -lh dist/styles.css

# Analyze with DevTools
- Coverage tab for unused CSS
- Performance tab for paint times
- Lighthouse for overall score
```

## Best Practices

1. **Write efficient selectors** - Use single classes
2. **Keep specificity low** - Max 0,4,0
3. **Use containment** - Isolate layout calculations
4. **Inline critical CSS** - Above-the-fold styles
5. **Ensure focus visibility** - Use :focus-visible
6. **Meet contrast ratios** - 4.5:1 for text
7. **Respect motion preferences** - Use prefers-reduced-motion
8. **Support dark mode** - Use custom properties
9. **Remove unused CSS** - PurgeCSS in builds
10. **Run quality checks** - Lint and format before committing

## See Also

- [CSS Essentials](css-essentials.md) - Core principles and organization
- [CSS Responsive](css-responsive.md) - Layout patterns and responsive techniques
