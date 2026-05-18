---
name: ref-svg-diagrams
description: Authoring standards for SVG technical diagrams — uniform visual language, theme handling, AsciiDoc embedding, per-diagram-type patterns
user-invocable: false
---

# SVG Diagrams Skill

Reference standards for authoring SVG technical diagrams (data-flow blocks, sequence, state, dispatch graphs) with a uniform plan-marshall visual language. Covers the visual style, how SVGs adapt to GitHub's light / dark themes when embedded in `.adoc` and `.md` pages, and how to embed them with the correct AsciiDoc macro.

## Enforcement

**Execution mode**: Read the standards for the diagram type you are authoring, then hand-author the SVG (or export from a tool — Excalidraw / draw.io — and conform the output to the standards). Save under `doc/resources/diagrams/{name}.svg`.

**Prohibited actions:**

- Do not embed external assets (no `<image href="https://…">`). Use Base64 data URLs or inline SVG primitives only.
- Do not commit raster screenshots in place of SVG. PNG / JPG is only for content that cannot be vectorised (photographs, hero illustrations).
- Do not bake hard-coded `#000` or `#fff` colors into diagram strokes / fills — they become invisible on the opposite theme. Use the palette tokens from [`standards/visual-language.md`](standards/visual-language.md).
- Do not introduce a per-diagram font stack. The system fonts in `visual-language.md` are the only stack used.

**Constraints:**

- Every SVG declares `viewBox` (not fixed width/height) so it scales.
- Every SVG includes `role="img"` plus `<title>` and `<desc>` elements for accessibility.
- Theme handling follows one of the three strategies in [`standards/theme-handling.md`](standards/theme-handling.md). Strategy is chosen at author time and recorded in a comment at the top of the SVG.
- AsciiDoc embedding uses the macro form documented in [`standards/asciidoc-embedding.md`](standards/asciidoc-embedding.md). Inline `<img>` HTML is not used.
- Per-diagram-type standards live under `standards/diagram-type-{name}.md`. They define geometry, naming conventions, and any type-specific affordances on top of the shared visual language.

## When to use this skill

Load this skill when:

- Adding a new architectural / data-flow / dispatch diagram to `doc/`.
- Touching an existing diagram under `doc/resources/diagrams/`.
- Authoring a sequence or state-machine diagram (future diagram-type standards land here).

Do not load this skill for:

- Hero / logo images (those are PNG or AI-generated; styled in CSS, not constrained by this spec).
- Screenshots (raster PNG, captured as-is).
- Diagrams embedded inside skill / standards docs under `marketplace/bundles/` — those continue to use ASCII art for diff-ability. The visual-SVG style is for the user-facing `doc/` tree.

## Standards

| Document | Scope |
|----------|-------|
| [`standards/visual-language.md`](standards/visual-language.md) | The shared visual language — palette, typography, stroke widths, corner radius, arrow markers, layout grid. Read first. |
| [`standards/theme-handling.md`](standards/theme-handling.md) | The three theme-handling strategies (theme-neutral / theme-aware via CSS / theme-aware via two files) with full SVG samples. Pick one strategy per diagram and document the choice. |
| [`standards/asciidoc-embedding.md`](standards/asciidoc-embedding.md) | The `image::` macro form, file-path conventions, accessibility (alt text, title, desc), and how AsciiDoctor renders the macro. |
| [`standards/diagram-type-block.md`](standards/diagram-type-block.md) | Block / data-flow diagram type — multi-column producer / store / consumer layouts. The findings-pipeline diagram is the reference implementation. |

Future per-diagram-type standards (placeholder — not yet authored):

- `standards/diagram-type-sequence.md` — sequence diagrams (LLM dispatch flows, finalize-step chains).
- `standards/diagram-type-state.md` — state machines (plan phase lifecycle, finding resolution lifecycle).
- `standards/diagram-type-graph.md` — call graphs / dependency graphs (skill-loading bubble resolution, agent dispatch tree).

## Templates

| Template | Use |
|----------|-----|
| [`templates/block-diagram-skeleton.svg`](templates/block-diagram-skeleton.svg) | Starter SVG with the standard `<style>` block, marker definition, and three-column scaffold. Copy, rename, fill in. |

## Workflow

### Step 1 — Pick a diagram type

Choose from the per-diagram-type standards. If none of the existing types fit, treat this as a sign that a new diagram-type standard is needed; consult the user before inventing a new pattern.

### Step 2 — Pick a theme-handling strategy

Read [`standards/theme-handling.md`](standards/theme-handling.md) and pick one of the three strategies. Strategy choice depends on contrast needs and rendering surface (does the SVG ship inside an AsciiDoc page, a Markdown README, both?). Record the strategy in a comment at the top of the SVG.

### Step 3 — Author the SVG

Copy the matching template from `templates/`. Fill in content, sticking to the palette and typography in [`standards/visual-language.md`](standards/visual-language.md). Save under `doc/resources/diagrams/{name}.svg`.

### Step 4 — Verify the render

Render the SVG against both light and dark backgrounds before committing:

```bash
rsvg-convert -b "#ffffff" -w 1200 -o /tmp/diagram-light.png path/to/diagram.svg
rsvg-convert -b "#0d1117" -w 1200 -o /tmp/diagram-dark.png  path/to/diagram.svg
```

Open both PNGs. Every text run and stroke must be legible on both backgrounds. Alignment must be visually consistent (no off-center content inside centered containers).

### Step 5 — Embed in the AsciiDoc page

Reference via the `image::` macro per [`standards/asciidoc-embedding.md`](standards/asciidoc-embedding.md). Render the page locally:

```bash
asciidoctor --safe-mode=safe -o /tmp/page.html path/to/page.adoc
```

Confirm the rendered HTML carries the `<img src="...svg">` reference and that the link resolves.

## Related

- [`templates/block-diagram-skeleton.svg`](templates/block-diagram-skeleton.svg) — starter for the first supported diagram type
- `pm-documents:ref-asciidoc` — AsciiDoc syntax and formatting standards (sibling skill)
- `pm-documents:recipe-verify-architecture-diagrams` — PlantUML-based architecture diagrams (different surface; this skill is for hand-authored SVGs in user-facing `doc/`)
