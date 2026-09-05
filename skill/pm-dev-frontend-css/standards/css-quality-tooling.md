# CSS Quality & Tooling

Performance optimization, accessibility standards, dark mode implementation, and development tools setup.

## Performance

### Efficient Selectors

```css
/* Preferred: Fast - single class */
.button { }
.card__header { }

/* Avoid: Slow - deep nesting */
.header .nav ul li a span { }

/* Avoid: Slow - attribute without tag */
[type="text"] { }

/* Preferred: Better */
input[type="text"] { }
```

### Minimize Specificity

```css
/* Avoid: High specificity (1,3,1) */
#sidebar .widget .title span { }

/* Preferred: Low specificity (0,1,0) */
.widget-title { }
```

Low specificity is easier to override and prevents specificity wars.

### Avoid Expensive Properties

Use sparingly: `box-shadow`, `border-radius`, `filter`, `transform`, `opacity`

```css
/* Preferred: Apply on state change only */
.button {
  transition: transform 0.2s;
}

.button:hover {
  transform: translateY(-2px);
}

/* Avoid: Animated constantly */
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
/* Avoid: Never remove outlines globally */
* {
  outline: none;
}

/* Preferred: Use :focus-visible for keyboard-only focus */
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

### Color Contrast

**WCAG AA Standards:**
- Normal text: 4.5:1 contrast ratio
- Large text (18pt+/14pt+ bold): 3:1
- UI components: 3:1

```css
/* Preferred: Good contrast */
.button {
  background: #1976d2;  /* Blue */
  color: #ffffff;       /* White - 4.54:1 */
}

/* Avoid: Poor contrast */
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

### Screen Reader Support

Use `.sr-only` (position: absolute, 1px clip) for visually hidden but accessible content. Ensure disabled elements have `opacity: 0.6; cursor: not-allowed`.

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

Dark mode relies on CSS custom properties for theming. For custom property fundamentals and naming conventions, see [CSS Essentials](css-essentials.md#css-custom-properties).

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

### `light-dark()` Function

Simplify dark mode with single-declaration color switching (Baseline 2024):

```css
:root {
  color-scheme: light dark;
}

.page {
  background: light-dark(white, #121212);
  color: light-dark(#1c1b1f, #e6e1e5);
  border-color: light-dark(#e0e0e0, #3d3d3d);
}
```

`light-dark()` automatically selects the appropriate value based on the computed `color-scheme`. Use this for simpler cases; use custom properties with `@media (prefers-color-scheme)` when you need more control.

### `color-mix()` (Baseline 2023)

Create dynamic color variations without preprocessors:

```css
.button--primary {
  background: var(--primary-color);
}

.button--primary:hover {
  /* 20% darker */
  background: color-mix(in srgb, var(--primary-color), black 20%);
}

.button--primary:active {
  /* 30% darker */
  background: color-mix(in srgb, var(--primary-color), black 30%);
}

/* Semi-transparent overlay */
.overlay {
  background: color-mix(in srgb, var(--primary-color), transparent 50%);
}
```

### `@property` — Typed Custom Properties (Baseline 2024)

Define custom property types, enabling transitions and providing defaults:

```css
@property --gradient-angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}

.gradient-card {
  background: conic-gradient(from var(--gradient-angle), #1976d2, #9c27b0);
  transition: --gradient-angle 0.5s;
}

.gradient-card:hover {
  --gradient-angle: 180deg;
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
    "stylelint": "^17.4.0",
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
export default (ctx) => {
  const isDev = ctx.env !== 'production';

  return {
    plugins: {
      'postcss-import': {},
      'postcss-preset-env': {
        stage: isDev ? 0 : 1,
      },
      autoprefixer: {
        grid: 'autoplace',
      },
      csso: isDev ? false : {
        comments: false,
      },
    },
  };
};
```

**What PostCSS Does:**
- **postcss-import** - Inlines `@import` statements
- **postcss-preset-env** - Modern CSS features with fallbacks
- **autoprefixer** - Adds vendor prefixes automatically
- **csso** - Minifies CSS in production

### Stylelint Configuration

For complete Stylelint configuration including property ordering, BEM naming enforcement, and CSS-in-JS setup, see `pm-dev-frontend:lint-config` → `standards/stylelint-setup.md`.

For Prettier and IDE integration, see `pm-dev-frontend:lint-config` → `standards/prettier-configuration.md`.

### PurgeCSS

Remove unused CSS in production builds. Configure `safelist` for dynamic classes (state classes, ARIA selectors):

```javascript
export default {
  content: ['./src/**/*.html', './src/**/*.js'],
  css: ['./dist/css/**/*.css'],
  safelist: {
    standard: ['is-active', 'is-open', 'is-loading'],
    deep: [/^data-/, /^aria-/],
  },
};
```

## Performance Targets

- CSS bundle: < 50KB gzipped
- First Paint: < 1s
- CLS: < 0.1
- Use DevTools Coverage tab to identify unused CSS

## See Also

- [CSS Essentials](css-essentials.md) - Core principles and organization
- [CSS Responsive](css-responsive.md) - Layout patterns and responsive techniques
