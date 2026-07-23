# Visual Language

The shared visual style every plan-marshall SVG diagram conforms to. Palette, typography, stroke widths, corner radius, arrow markers, layout grid. Per-diagram-type standards layer on top of this.

The visual reference is the **Vercel / Stripe / Linear** technical-doc aesthetic — restrained palette, monospace identifiers, generous whitespace, optional subtle grid. Concrete decisions:

## Palette

Anchored on [GitHub Primer](https://primer.style/foundations/color) tokens so the diagrams sit natively on both GitHub themes.

### Theme-aware tokens

| Role | Light | Dark | Usage |
|------|-------|------|-------|
| `--stroke` | `#1f2328` | `#f0f6fc` | Primary lines, text, box borders. Primer `fg-default`. |
| `--muted`  | `#59636e` | `#9198a1` | Secondary text, captions, dashed separators, arrow labels. Primer `fg-muted`. |
| `--accent-success` | `#2da44e` | `#3fb950` | Happy-path arrows, success indicators. Primer `success-fg`. |
| `--accent-danger`  | `#cf222e` | `#f85149` | Error paths, failure indicators. Primer `danger-fg`. |

### Theme-neutral fallback

When the theme-aware strategy is impractical (e.g. SVG must render correctly even when the user agent does not honor `prefers-color-scheme`), use the single neutral:

| Role | Color | Notes |
|------|-------|-------|
| Stroke / text / arrows | `#6e7681` | Primer's neutral-emphasis tone — readable on both `#ffffff` and `#0d1117` backgrounds. Less contrast than theme-aware on each theme individually but visually consistent. |

Strategy choice is documented per-diagram per [`theme-handling.md`](theme-handling.md).

### Background

**Always transparent.** Diagrams never declare a background `<rect>` or `fill` on the root `<svg>`. The page background shows through. This is what makes both palettes work on either GitHub theme.

## Typography

Single system-font stack. **No custom fonts**, no `@import`, no web fonts (they break in SVG-as-image).

| Role | Stack | Size | Weight | Style |
|------|-------|------|--------|-------|
| Column header | `ui-sans-serif, -apple-system, system-ui, 'Segoe UI', sans-serif` | 15 px | 600 | upright |
| Item identifier (code) | `ui-monospace, 'SF Mono', Menlo, Consolas, monospace` | 12 px | 400 | upright |
| Item identifier emphasised | same | 12 px | 700 | upright |
| Caption / footer / annotation | sans-serif stack | 11 px | 400 | italic |
| Arrow label | sans-serif stack | 11 px | 400 | italic |

Body identifiers are **monospace** because they refer to file names, skill names, script notations, JSON keys — content that benefits from the typeface signalling "this is code." Prose annotations are sans-serif because they are prose.

## Geometry

### Stroke widths

| Element | Width |
|---------|-------|
| Container box border | 1.2 px |
| Arrow / connector line | 1.5 px |
| Divider / dash | 0.6 px with `stroke-dasharray="3 3"` |
| Optional background grid (when used) | 0.5 px, 10–20% opacity |

### Corner radius

| Element | `rx` / `ry` |
|---------|-------------|
| Container box | 6 |
| Smaller inner box / pill | 4 |
| Square / sharp | only for emphasised central elements where the rectangular shape is the visual cue |

### Arrow markers

Filled triangle, 9 × 9 marker viewBox, `refX="9" refY="5"`.

```svg
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
        markerWidth="9" markerHeight="9" orient="auto">
  <path d="M0,0 L10,5 L0,10 z" class="muted-fill"/>
</marker>
```

Marker fill follows the stroke palette via a CSS class (so it adapts to theme alongside everything else).

## Layout grid

Diagrams are designed in a notional 8-pixel grid. All positions and sizes should snap to multiples of 8 wherever practical, except for centred text where snapping to the column midline takes precedence.

### Standard `viewBox` sizes

| Aspect | viewBox | Use |
|--------|---------|-----|
| Wide (16:9-ish) | `0 0 900 500` | Three-column block diagrams, sequence diagrams. The default. |
| Tall (4:5) | `0 0 600 750` | Single-column dispatch trees, state machines. |
| Square | `0 0 600 600` | Component-relationship diagrams, simple two-node flows. |

### Padding and gutters

| Spacing | Value | Notes |
|---------|-------|-------|
| Outer margin (`viewBox` edge → first content) | 20 px minimum | Lets the diagram breathe inside any container that adds its own padding. |
| Inter-column gutter | 40 px | Between major content groups. Arrows live in the gutter. |
| Intra-column item spacing | 18–22 px | Between sibling text items inside a single column. Tighter looks cramped; looser drifts visually. |
| Header → first item | 30 px | From column header text baseline to first content item. |

## Optional subtle background grid

The "Vercel aesthetic" subtle grid is **opt-in** and used sparingly — only for diagrams large enough to benefit from spatial reference cues. When used:

```svg
<defs>
  <pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">
    <path d="M 16 0 L 0 0 0 16" class="grid-line"/>
  </pattern>
</defs>
<rect width="100%" height="100%" fill="url(#grid)"/>
```

`.grid-line` style: `stroke: var(--muted); stroke-width: 0.5; opacity: 0.15; fill: none;` (or equivalent class swaps via media query).

Most diagrams should **omit** the grid. The default is no grid.

## Naming conventions

| Element | Convention |
|---------|-----------|
| SVG file name | `kebab-case.svg`. Match the concept it depicts (e.g. `findings-pipeline.svg`, `dispatch-resolution.svg`). |
| Style class names | semantic (`stroke`, `text`, `muted`, `accent-success`), never visual (`color-red`, `dashed-line`). |
| `<title>` element | One sentence, sentence case, no trailing period. Used as accessible name. |
| `<desc>` element | One paragraph describing the diagram's meaning. Used by assistive tech. |

## Anti-patterns

The following are explicitly out of scope for this visual language:

- **3-D effects, shadows, gradients.** The aesthetic is flat. Drop-shadows make SVG large and render inconsistently across themes.
- **Bright primary colors** (red, blue, yellow as decorative). The palette is intentionally restrained. Accent colors are reserved for semantic meaning (success / danger).
- **Custom fonts** (Google Fonts, web fonts, embedded base64 fonts). SVGs render as images on GitHub; web fonts fail silently and the diagram falls back to a generic serif. Use the system stack only.
- **PNG / JPG embedded inside SVG.** Defeats the point of SVG. If a raster image is needed, ship it as a separate PNG.
- **Hand-rolled curves.** Use straight orthogonal lines or single quadratic Bézier curves. No complex paths.

## Worked example

See `findings-pipeline.svg` under `doc/resources/diagrams/` for the reference implementation of this visual language applied to a three-column block diagram. The diagram-type-block standard ([`diagram-type-block.md`](diagram-type-block.md)) walks through its construction.
