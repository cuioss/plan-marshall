# CSS Essentials

Core CSS principles, naming conventions, code organization, and component architecture for CUI projects.

## Modern CSS Features

### CSS Custom Properties

```css
/* Define reusable design tokens */
:root {
  --primary-color: #1976d2;
  --spacing-unit: 0.5rem;
  --font-base: 1rem;
}

/* Use throughout CSS */
.button {
  background-color: var(--primary-color);
  padding: var(--spacing-unit);
}

/* Component-scoped variables */
.card {
  --card-padding: 1rem;
  padding: var(--card-padding);
}

/* Variants override variables */
.card--compact {
  --card-padding: 0.5rem;
}
```

### Modern Layout

- **CSS Grid** - Page layouts
- **Flexbox** - Component layouts
- **Container Queries** - Responsive components

### Modern Functions

```css
/* Fluid sizing with clamp() */
.heading {
  font-size: clamp(1.5rem, 4vw, 3rem);
}

/* Calculations */
.container {
  width: calc(100% - 2rem);
}

/* Logical comparisons */
.box {
  width: min(500px, 100%);
  height: max(200px, 50vh);
}
```

## Naming Conventions

### BEM Methodology

```css
/* Block - standalone component */
.card { }

/* Element - part of a block */
.card__header { }
.card__body { }
.card__footer { }

/* Modifier - variant of block or element */
.card--highlighted { }
.card--large { }
.card__header--sticky { }
```

**BEM Rules:**
- Use lowercase and hyphens (kebab-case)
- Block names describe *what it is*, not what it looks like
- Elements use double underscore `__`
- Modifiers use double dash `--`
- Avoid nested elements: `.card__body__title` ❌ Use `.card__title` ✓

### Custom Properties Naming

```css
/* ✅ Semantic names */
--primary-color
--text-base
--spacing-md
--border-radius-sm

/* ❌ Presentational names */
--blue
--size-16
```

### State Classes

Temporary states use `.is-*` or `.has-*` prefix:

```css
.button.is-active { }
.button.is-disabled { }
.button.is-loading { }
.card.has-error { }
```

## Selector Best Practices

### Keep Specificity Low

```css
/* ✅ Low specificity (0,1,0) */
.button { }
.button--primary { }

/* ❌ High specificity (1,3,1) */
#sidebar .nav ul li a.active { }
```

**Target: Max 0,4,0** (0 IDs, 4 classes max)

### Avoid IDs for Styling

```css
/* ✅ Use classes */
.header { }

/* ❌ Don't use IDs */
#header { }
```

### Nesting Limit: 3 Levels

```css
/* ✅ Good - 2 levels */
.card__header-title { }

/* ❌ Too nested - 4 levels */
.card .inner .header .title { }
```

## Value Units

**Font Sizes: rem or em**
```css
.text-sm { font-size: 0.875rem; }  /* 14px */
.text-base { font-size: 1rem; }    /* 16px */
```

**Spacing: rem**
```css
.button {
  padding: 0.5rem 1rem;
  margin-bottom: 1rem;
}
```

**Line Height: Unitless**
```css
.text {
  line-height: 1.5;  /* ✅ Scales */
  line-height: 24px; /* ❌ Fixed */
}
```

## Property Organization

Order properties logically:

```css
.component {
  /* Display & Position */
  display: flex;
  position: relative;
  z-index: 10;

  /* Flexbox/Grid */
  flex-direction: column;
  justify-content: center;
  gap: 1rem;

  /* Box Model */
  width: 100%;
  margin: 1rem;
  padding: 1rem;
  border: 1px solid gray;

  /* Visual */
  background: white;
  border-radius: 0.25rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);

  /* Typography */
  color: #333;
  font-size: 1rem;
  line-height: 1.5;

  /* Interaction */
  cursor: pointer;
  transition: all 0.2s ease;
}
```

## File Structure

### Directory Organization

```text
src/css/
├── base/
│   ├── reset.css           # Browser reset
│   ├── variables.css       # CSS custom properties
│   └── typography.css      # Base typography
├── components/
│   ├── button.css
│   ├── card.css
│   ├── navigation.css
│   └── form.css
├── layout/
│   ├── grid.css
│   ├── container.css
│   └── header-footer.css
├── utilities/
│   ├── spacing.css
│   ├── display.css
│   └── typography.css
└── main.css               # Import orchestration
```

### Import Order

```css
/* main.css */

/* 1. Base - Foundation */
@import './base/reset.css';
@import './base/variables.css';
@import './base/typography.css';

/* 2. Layout - Structure */
@import './layout/grid.css';
@import './layout/container.css';

/* 3. Components - UI Elements */
@import './components/button.css';
@import './components/card.css';

/* 4. Utilities - Helpers (last) */
@import './utilities/spacing.css';
@import './utilities/display.css';
```

## Component Architecture

### Component File Pattern

```css
/* ==========================================================================
   Component Name
   ========================================================================== */

/**
 * Component Description
 *
 * Variants: .component--variant
 * States: :hover, :focus, .is-active
 * Custom Properties: --component-var
 */

/* Base Component */
.component {
  /* Base styles */
}

/* Component Elements */
.component__element {
  /* Element styles */
}

/* Component Modifiers */
.component--modifier {
  /* Modifier styles */
}

/* Component States */
.component:hover { }
.component.is-active { }
```

### Button Component Example

```css
/**
 * Button Component
 *
 * @example
 * <button class="button button--primary">Click me</button>
 */

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.5rem;
  padding: 0.5rem 1rem;

  background: var(--button-bg, var(--color-neutral-100));
  border: 1px solid var(--button-border, var(--color-neutral-300));
  border-radius: var(--border-radius-md);

  font-family: inherit;
  font-size: 1rem;
  font-weight: 500;
  color: var(--button-color, var(--color-neutral-900));

  cursor: pointer;
  transition: all 0.15s ease;
}

.button__icon {
  margin-right: 0.5rem;
}

.button--primary {
  --button-bg: var(--color-primary-600);
  --button-color: white;
}

.button--large {
  min-height: 3rem;
  padding: 0.75rem 1.5rem;
  font-size: 1.125rem;
}

.button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.button:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

.button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}
```

## Utility Classes

Small, single-purpose classes for common patterns:

```css
/* Display */
.flex { display: flex; }
.grid { display: grid; }
.hidden { display: none; }

/* Flexbox */
.flex-col { flex-direction: column; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }

/* Spacing (scale: 0-8) */
.p-0 { padding: 0; }
.p-2 { padding: 0.5rem; }
.p-4 { padding: 1rem; }
.m-2 { margin: 0.5rem; }
.mx-auto { margin-left: auto; margin-right: auto; }

/* Typography */
.text-sm { font-size: 0.875rem; }
.text-lg { font-size: 1.125rem; }
.font-bold { font-weight: 700; }
```

### When to Use Utilities

**Use utilities for:**
- Quick layout adjustments
- Common spacing patterns
- One-off styling needs

**Don't use utilities for:**
- Complex components (create proper component class)
- Styles that always appear together (create a component)

```html
<!-- ✅ Good: Utilities for layout, component for semantics -->
<div class="flex items-center gap-4">
  <button class="button button--primary">Save</button>
</div>

<!-- ❌ Bad: Too many utilities, should be a component -->
<div class="inline-flex items-center px-4 py-2 bg-blue text-white rounded">
  Button
</div>
```

## Architecture Patterns

### Component-Based (Recommended)

Organize CSS around reusable components:

```text
✅ Advantages:
- Easy to find related styles
- Components are portable
- Scales well

✅ Use when:
- Building component library
- Large applications
- Team collaboration
```

### Hybrid Approach (Recommended)

Components + utilities:

```css
/* Components for reusable patterns */
.card { }
.button { }

/* Utilities for layout and spacing */
.flex { }
.gap-4 { }
```

## Comments and Documentation

### Component Documentation

```css
/**
 * Button Component
 *
 * Primary interactive element for user actions.
 *
 * Variants:
 * - .button--primary: Main call-to-action
 * - .button--secondary: Alternative action
 * - .button--large: Increased size
 *
 * Custom Properties:
 * - --button-bg: Background color
 * - --button-color: Text color
 */
.button {
  /* Implementation */
}
```

### Inline Comments

```css
.element {
  /* Prevent FOUC on page load */
  opacity: 0;

  /* Create new stacking context */
  transform: translateZ(0);
}
```

## Theming with Custom Properties

Use CSS custom properties for theming to enable easy color scheme switching:

```css
:root {
  --bg-primary: white;
  --text-primary: #1c1b1f;
}

/* Components use custom properties */
.page {
  background: var(--bg-primary);
  color: var(--text-primary);
}
```

For complete dark mode implementation including system preference detection and manual toggle, see [CSS Quality & Tooling](css-quality-tooling.md#dark-mode).

## Browser Compatibility

Target modern browsers (latest 2 versions):
- Chrome, Firefox, Safari, Edge

**Vendor Prefixes:**
- Use Autoprefixer - don't write manually
- Configure via browserslist in package.json

```json
{
  "browserslist": [
    "last 2 Chrome versions",
    "last 2 Firefox versions",
    "last 2 Safari versions",
    "last 2 Edge versions"
  ]
}
```

## Maintenance Guidelines

- Remove unused CSS regularly (PurgeCSS)
- Check for duplicate patterns
- Follow BEM strictly
- Document complex logic
- Keep variable naming consistent

## See Also

- [CSS Responsive](css-responsive.md) - Layout patterns and responsive techniques
- [CSS Quality & Tooling](css-quality-tooling.md) - Performance, accessibility, and build tools
