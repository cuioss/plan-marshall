# CSS Essentials

Core CSS principles, naming conventions, code organization, and component architecture.

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

### Native CSS Nesting (Baseline 2023)

Use native CSS nesting with the `&` selector for component-scoped styles:

```css
.card {
  padding: 1rem;
  border: 1px solid var(--border-primary);

  & .card__header {
    font-weight: 600;
  }

  & .card__body {
    padding: 0.5rem 0;
  }

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  &--highlighted {
    border-color: var(--primary-color);
  }

  @media (min-width: 768px) {
    padding: 2rem;
  }
}
```

**Note**: Native CSS nesting is baseline across modern browsers. Use it directly without preprocessors or polyfills.

### Cascade Layers (`@layer`) (Baseline 2022)

Use `@layer` to manage specificity without relying solely on source order or BEM:

```css
/* Define layer order — later layers win regardless of specificity */
@layer base, components, utilities;

@layer base {
  a { color: var(--link-color); }
}

@layer components {
  .button { padding: 0.5rem 1rem; }
  .card { border: 1px solid var(--border-primary); }
}

@layer utilities {
  .hidden { display: none; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; }
}
```

### `:has()` Pseudo-Class (Baseline 2023)

The "parent selector" — style elements based on their children or subsequent siblings:

```css
/* Style form group when it contains an invalid input */
.form-group:has(:invalid) {
  border-color: var(--color-error);
}

/* Style card differently when it has an image */
.card:has(img) {
  grid-template-rows: auto 1fr;
}

/* Style label when its sibling input is focused */
label:has(+ input:focus) {
  color: var(--primary-color);
}
```

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
- Avoid nested elements: `.card__body__title` (avoid) — use `.card__title` instead

### Custom Properties Naming

```css
/* Preferred: Semantic names */
--primary-color
--text-base
--spacing-md
--border-radius-sm

/* Avoid: Presentational names */
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
/* Preferred: Low specificity (0,1,0) */
.button { }
.button--primary { }

/* Avoid: High specificity (1,3,1) */
#sidebar .nav ul li a.active { }
```

**Target: Max 0,4,0** (0 IDs, 4 classes max)

### Avoid IDs for Styling

```css
/* Preferred: Use classes */
.header { }

/* Avoid: Don't use IDs */
#header { }
```

### Nesting Limit: 3 Levels

```css
/* Preferred: Good - 2 levels */
.card__header-title { }

/* Avoid: Too nested - 4 levels */
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
  line-height: 1.5;  /* Preferred: Scales */
  line-height: 24px; /* Avoid: Fixed */
}
```

## Property Organization

Order properties logically by category: **Display & Position** → **Flexbox/Grid** → **Box Model** (width, margin, padding, border) → **Visual** (background, border-radius, box-shadow) → **Typography** → **Interaction** (cursor, transition).

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

Each component file follows: **base component** → **elements** (`__element`) → **modifiers** (`--modifier`) → **states** (`:hover`, `.is-active`). Include a file header comment documenting variants, states, and custom properties.

## Utility Classes

Small, single-purpose classes (`.flex`, `.hidden`, `.p-4`, `.text-sm`) for layout adjustments and spacing. When the same utility combination repeats, extract a component class instead.

## Theming

Use custom properties for theming. For dark mode with system preference detection, see [CSS Quality & Tooling](css-quality-tooling.md#dark-mode).

## Browser Compatibility

Target modern browsers (latest 2 versions). Use Autoprefixer via browserslist in package.json -- never write vendor prefixes manually.

## See Also

- [CSS Responsive](css-responsive.md) - Layout patterns and responsive techniques
- [CSS Quality & Tooling](css-quality-tooling.md) - Performance, accessibility, and build tools
