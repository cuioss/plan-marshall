# CSS Responsive Design

Mobile-first approach, layout patterns, container queries, and responsive techniques for CUI projects.

## Mobile-First Principle

Start with mobile styles, then enhance for larger screens.

### Why Mobile-First?

- Most users browse on mobile
- Forces focus on essential content
- Better performance (load less initially)
- Progressive enhancement philosophy

### Basic Pattern

```css
/* Base styles (mobile) */
.container {
  padding: 1rem;
}

/* Tablet */
@media (min-width: 768px) {
  .container {
    padding: 2rem;
    max-width: 768px;
    margin: 0 auto;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .container {
    max-width: 1024px;
  }
}
```

### Standard Breakpoints

```css
/* Mobile: < 768px (default, no media query) */

/* Tablet: >= 768px */
@media (min-width: 768px) { }

/* Desktop: >= 1024px */
@media (min-width: 1024px) { }

/* Wide: >= 1440px */
@media (min-width: 1440px) { }
```

Define as custom properties:

```css
:root {
  --breakpoint-tablet: 768px;
  --breakpoint-desktop: 1024px;
  --breakpoint-wide: 1440px;
}
```

## CSS Grid Layouts

### Dashboard Layout

```css
.dashboard {
  display: grid;
  grid-template-areas:
    "header"
    "main"
    "footer";
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
  gap: 1rem;
}

.dashboard__header { grid-area: header; }
.dashboard__main { grid-area: main; }
.dashboard__footer { grid-area: footer; }

/* Tablet: Add sidebar */
@media (min-width: 768px) {
  .dashboard {
    grid-template-areas:
      "header header"
      "sidebar main"
      "footer footer";
    grid-template-columns: 250px 1fr;
  }

  .dashboard__sidebar { grid-area: sidebar; }
}

/* Desktop: Add right column */
@media (min-width: 1024px) {
  .dashboard {
    grid-template-areas:
      "header header header"
      "sidebar main aside"
      "footer footer footer";
    grid-template-columns: 250px 1fr 300px;
  }

  .dashboard__aside { grid-area: aside; }
}
```

### Content Grid

```css
.content-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr;  /* Mobile: Single column */
}

@media (min-width: 768px) {
  .content-grid {
    grid-template-columns: repeat(2, 1fr);  /* Tablet: 2 columns */
  }
}

@media (min-width: 1024px) {
  .content-grid {
    grid-template-columns: repeat(3, 1fr);  /* Desktop: 3 columns */
  }
}
```

### Auto-Fit Pattern

Responsive without media queries:

```css
.auto-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

/* Automatically adjusts columns based on available space */
```

## Flexbox Layouts

### Common Patterns

**Navigation**
```css
.nav {
  display: flex;
  gap: 1rem;
  align-items: center;
}

/* Mobile: Stack vertically */
@media (max-width: 767px) {
  .nav {
    flex-direction: column;
  }
}
```

**Card Layout**
```css
.card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card__body {
  flex: 1;  /* Grows to fill space */
}
```

**Center Content**
```css
.center-box {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
}
```

**Responsive Flex Wrap**
```css
.flex-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.flex-grid__item {
  flex: 1 1 100%;  /* Mobile: Full width */
}

@media (min-width: 768px) {
  .flex-grid__item {
    flex: 1 1 calc(50% - 0.5rem);  /* Tablet: Half width */
  }
}

@media (min-width: 1024px) {
  .flex-grid__item {
    flex: 1 1 calc(33.333% - 0.67rem);  /* Desktop: Third width */
  }
}
```

## Container Queries

Modern approach: Components respond to container width, not viewport width.

### Basic Setup

```css
.card-container {
  container-type: inline-size;
  container-name: card;
}

.card {
  padding: 1rem;
}

/* Respond to container width */
@container card (min-width: 400px) {
  .card {
    display: grid;
    grid-template-columns: 150px 1fr;
    padding: 1.5rem;
  }
}

@container card (min-width: 600px) {
  .card {
    grid-template-columns: 200px 1fr 150px;
  }
}
```

### Benefits

- Truly reusable components
- Works in any context (sidebar, main, modal)
- More maintainable than viewport queries

### Product Card Example

```css
.product {
  container-type: inline-size;
}

.product__layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@container (min-width: 400px) {
  .product__layout {
    flex-direction: row;
    align-items: center;
  }
}
```

## Responsive Typography

### Fluid Typography with clamp()

Automatically scaling text:

```css
:root {
  /* clamp(min, preferred, max) */
  --font-sm: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
  --font-base: clamp(0.875rem, 0.8rem + 0.375vw, 1rem);
  --font-lg: clamp(1rem, 0.9rem + 0.5vw, 1.125rem);
  --font-xl: clamp(1.125rem, 1rem + 0.625vw, 1.25rem);
  --font-2xl: clamp(1.25rem, 1.1rem + 0.75vw, 1.5rem);
  --font-3xl: clamp(1.5rem, 1.3rem + 1vw, 1.875rem);
  --font-4xl: clamp(1.875rem, 1.6rem + 1.375vw, 2.25rem);
}

h1 { font-size: var(--font-4xl); }
h2 { font-size: var(--font-3xl); }
body { font-size: var(--font-base); }
```

### Traditional Approach

```css
body {
  font-size: 0.875rem;  /* Mobile */
}

@media (min-width: 768px) {
  body {
    font-size: 1rem;    /* Tablet */
  }
}

@media (min-width: 1024px) {
  body {
    font-size: 1.125rem; /* Desktop */
  }
}
```

## Responsive Images

### Flexible Images

```css
img {
  max-width: 100%;
  height: auto;
  display: block;
}
```

### Art Direction

```html
<picture>
  <source media="(min-width: 1024px)" srcset="hero-large.jpg">
  <source media="(min-width: 768px)" srcset="hero-medium.jpg">
  <img src="hero-small.jpg" alt="Hero">
</picture>
```

### Responsive Background Images

```css
.hero {
  background-image: url('hero-small.jpg');
  background-size: cover;
  background-position: center;
}

@media (min-width: 768px) {
  .hero {
    background-image: url('hero-medium.jpg');
  }
}

@media (min-width: 1024px) {
  .hero {
    background-image: url('hero-large.jpg');
  }
}
```

## Responsive Spacing

### Fluid Spacing

```css
:root {
  --spacing-sm: clamp(0.5rem, 1vw, 1rem);
  --spacing-md: clamp(1rem, 2vw, 2rem);
  --spacing-lg: clamp(2rem, 4vw, 4rem);
}

.section {
  padding: var(--spacing-md);
}
```

### Traditional Approach

```css
.section {
  padding: 1rem;
}

@media (min-width: 768px) {
  .section {
    padding: 2rem;
  }
}

@media (min-width: 1024px) {
  .section {
    padding: 3rem;
  }
}
```

## Common Responsive Patterns

### Hide/Show at Breakpoints

```css
/* Show on mobile only */
.mobile-only {
  display: block;
}

@media (min-width: 768px) {
  .mobile-only {
    display: none;
  }
}

/* Show on tablet and up */
.tablet-up {
  display: none;
}

@media (min-width: 768px) {
  .tablet-up {
    display: block;
  }
}
```

### Responsive Columns

```css
.columns {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (min-width: 768px) {
  .columns {
    flex-direction: row;
  }

  .columns > * {
    flex: 1;
  }
}
```

### Responsive Tables

```css
/* Mobile: Card-like view */
table { display: block; }
thead { display: none; }
tbody, tr, td { display: block; }

td::before {
  content: attr(data-label) ": ";
  font-weight: bold;
}

/* Desktop: Normal table */
@media (min-width: 768px) {
  table { display: table; }
  thead { display: table-header-group; }
  tbody { display: table-row-group; }
  tr { display: table-row; }
  td { display: table-cell; }
  td::before { content: none; }
}
```

## Touch-Friendly Design

See **css-quality-tooling.md** Accessibility section for touch target requirements (minimum 44x44px) and implementation patterns.

## Print Styles

```css
@media print {
  /* Hide non-essential elements */
  .navigation,
  .sidebar {
    display: none;
  }

  /* Optimize for printing */
  body {
    color: black;
    background: white;
  }

  /* Show URLs */
  a::after {
    content: " (" attr(href) ")";
  }

  /* Page breaks */
  .section {
    page-break-inside: avoid;
  }

  h1, h2, h3 {
    page-break-after: avoid;
  }
}
```

## Testing Responsive Design

### Browser DevTools

Test at all breakpoints:
- 320px (small mobile)
- 375px (mobile)
- 768px (tablet)
- 1024px (desktop)
- 1440px (large desktop)

Test features:
- Touch interactions
- Throttled network
- High DPI displays

## Best Practices

1. **Start mobile-first** - Always
2. **Use container queries** - For truly reusable components
3. **Fluid typography** - Use clamp() for automatic scaling
4. **Auto-fit grid** - For flexible layouts without media queries
5. **Test at breakpoints** - Use real devices when possible
6. **44px touch targets** - Ensure mobile usability
7. **Flexible images** - Always use `max-width: 100%`

## See Also

- [CSS Essentials](css-essentials.md) - Core principles and organization
- [CSS Quality & Tooling](css-quality-tooling.md) - Performance and build tools
