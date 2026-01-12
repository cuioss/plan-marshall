# CSS Development Standards

## Overview

Modern CSS development standards for CUI projects covering fundamentals, responsive design, performance optimization, accessibility, and tooling.

## Purpose

Ensures consistent, high-quality CSS through:
- Modern CSS features (custom properties, Grid, Flexbox, Container Queries)
- BEM naming conventions and component architecture
- Mobile-first responsive design patterns
- Performance optimization and accessibility compliance
- PostCSS/Stylelint/Prettier integration

## Standards Included

1. **css-essentials.md** - Core principles, BEM naming, custom properties, selectors, file structure, component architecture
2. **css-responsive.md** - Mobile-first approach, Grid/Flexbox layouts, Container Queries, fluid typography, responsive patterns
3. **css-quality-tooling.md** - Performance, accessibility, dark mode, PostCSS/Stylelint/Prettier setup, build pipeline

## Key Features

### CSS Essentials
- Modern CSS features (custom properties, Grid, Flexbox, clamp())
- BEM methodology and semantic naming
- Low specificity selectors (max 0,4,0)
- Component architecture and utility classes

### Responsive Design
- Mobile-first with progressive enhancement
- CSS Grid layouts (dashboard, content grid, auto-fit)
- Flexbox patterns (navigation, cards, centering)
- Container Queries for component-level responsiveness
- Fluid typography with clamp()

### Quality & Tooling
- Performance (efficient selectors, containment, critical CSS)
- Accessibility (focus management, WCAG contrast ratios, motion preferences)
- Dark mode (system preference and manual toggle)
- PostCSS/Stylelint/Prettier configuration
- Build pipeline and CI/CD integration

## Quick Examples

### BEM Component
```css
/**
 * Button Component
 *
 * @example
 * <button class="button button--primary">Click me</button>
 */
.button {
  display: inline-flex;
  padding: 0.5rem 1rem;
  background: var(--button-bg, var(--color-neutral-100));
  border-radius: var(--border-radius-md);
}

.button--primary {
  --button-bg: var(--color-primary-600);
  --button-color: white;
}
```

### Responsive Grid
```css
.dashboard {
  display: grid;
  grid-template-areas:
    "header"
    "main"
    "footer";
  min-height: 100vh;
  gap: 1rem;
}

@media (min-width: 768px) {
  .dashboard {
    grid-template-areas:
      "header header"
      "sidebar main"
      "footer footer";
    grid-template-columns: 250px 1fr;
  }
}
```

### Container Queries
```css
.card-container {
  container-type: inline-size;
}

.card {
  padding: 1rem;
}

@container (min-width: 400px) {
  .card {
    display: grid;
    grid-template-columns: 150px 1fr;
  }
}
```

### Dark Mode
```css
:root {
  --bg-primary: white;
  --text-primary: #1c1b1f;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #121212;
    --text-primary: #e6e1e5;
  }
}

.page {
  background: var(--bg-primary);
  color: var(--text-primary);
}
```

## When to Use

Activate when:
- Writing/modifying CSS code
- Setting up CSS tooling
- Implementing design systems
- Building responsive layouts
- Optimizing CSS performance
- Ensuring accessibility
- Reviewing CSS code

## Getting Started

1. **Install tooling**
   ```json
   "devDependencies": {
     "postcss": "^8.4.0",
     "stylelint": "^15.0.0",
     "prettier": "^3.0.0"
   }
   ```

2. **Configure PostCSS** (see css-quality-tooling.md)
3. **Configure Stylelint** (see css-quality-tooling.md)
4. **Configure Prettier** (see css-quality-tooling.md)
5. **Follow BEM naming** and use custom properties
6. **Run quality checks** before committing

## Best Practices

1. Use CSS custom properties for design tokens
2. Follow mobile-first approach
3. Use BEM naming convention
4. Keep specificity low (max 0,4,0)
5. Implement container queries for responsive components
6. Support dark mode via custom properties
7. Ensure accessibility (focus-visible, contrast ratios, motion preferences)
8. Run Stylelint and Prettier before committing

## Integration

Works with:
- **PostCSS** - CSS processing and optimization
- **Stylelint** - Linting and code quality
- **Prettier** - Code formatting
- **Maven frontend-maven-plugin** - Build automation
- **cui-javascript** skill - Frontend JavaScript standards

## Resources

- `css-essentials.md` - Core principles and component architecture
- `css-responsive.md` - Responsive design patterns
- `css-quality-tooling.md` - Performance, accessibility, and tooling
- [MDN CSS Reference](https://developer.mozilla.org/en-US/docs/Web/CSS)
- [Can I Use](https://caniuse.com/) - Browser compatibility
