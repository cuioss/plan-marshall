---
name: css
description: Modern CSS standards covering native nesting, cascade layers, Container Queries, custom properties, responsive design, accessibility, and PostCSS/Stylelint tooling
user-invocable: false
---

# CSS Development Standards

## Enforcement

- **Execution mode**: Reference — load specific standards on-demand based on current task
- **Prohibited actions**: Do not generate legacy CSS patterns (vendor prefixes handled by Autoprefixer, no IE/legacy fallbacks)
- **Constraints**: Prefer native CSS features (nesting, layers, custom properties) over preprocessor equivalents

Modern CSS development standards covering fundamentals, responsive design, performance, and accessibility.

## Prerequisites

- Modern browser support (CSS Grid, Custom Properties, Container Queries)
- CSS preprocessor or PostCSS toolchain (optional)
- Stylelint for linting (see `pm-dev-frontend:lint-config` for setup)

## Workflow

### Step 1: Load CSS Essentials

Load this standard for any CSS implementation work.

```
Read: standards/css-essentials.md
```

Covers core principles, BEM naming, custom properties, selectors, and file structure.

### Step 2: Load Additional Standards (As Needed)

**Responsive Design** (load for layout work):
```
Read: standards/css-responsive.md
```

Use when: Building responsive layouts, working with Grid/Flexbox, Container Queries, or fluid typography.

**Quality and Tooling** (load for performance or accessibility work):
```
Read: standards/css-quality-tooling.md
```

Use when: Optimizing CSS performance, implementing dark mode, improving accessibility, or configuring PostCSS/Stylelint.

## Related Skills

- `pm-dev-frontend:lint-config` — Stylelint, Prettier configuration
- `pm-dev-frontend:javascript` — JavaScript standards
