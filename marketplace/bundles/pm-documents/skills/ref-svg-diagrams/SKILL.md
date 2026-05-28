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

- **Mandatory visual confirmation before presenting or committing.** Every new or modified SVG MUST be rasterised against both the GitHub light (`#ffffff`) and dark (`#0d1117`) backgrounds (recipe in Step 4 of the Workflow) and **the rendered PNG MUST be read back by the author** (Read tool on the PNG, or open in an external viewer) before the SVG is shown to the user or committed. Authoring an SVG and trusting that "the markup looks right" is forbidden — coordinate math, font fallback, alignment, marker placement, and theme contrast can only be evaluated on the rendered output. Skipping this step has shipped misaligned diagrams to users in the past and is the most common defect class for hand-authored SVGs.
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
| [`standards/diagram-type-block.md`](standards/diagram-type-block.md) | Block / data-flow diagram type — multi-column producer / store / consumer layouts and side-by-side comparisons. The findings-pipeline diagram is the reference implementation. |
| [`standards/diagram-type-graph.md`](standards/diagram-type-graph.md) | Graph / topology diagram type — hub-and-spoke and radial relationships. The plan-worktree-topology diagram is the reference implementation. |
| [`standards/diagram-type-flow.md`](standards/diagram-type-flow.md) | Flow diagram type — single- or multi-track directional movement through stages, with junctions and loops. The post-execute-shipping-flow diagram is the reference implementation. |
| [`standards/diagram-type-stack.md`](standards/diagram-type-stack.md) | Stack diagram type — layered slabs with optional convergence on a consumer. The audit-trail-layers diagram is the reference implementation. |

Future per-diagram-type standards (placeholder — not yet authored):

- `standards/diagram-type-sequence.md` — sequence diagrams (LLM dispatch traces, finalize-step chains).
- `standards/diagram-type-state.md` — state machines (plan phase lifecycle, finding resolution lifecycle).

## Templates

| Template | Pairs with | Use |
|----------|------------|-----|
| [`templates/block-diagram-skeleton.svg`](templates/block-diagram-skeleton.svg) | `diagram-type-block.md` | Three-column block scaffold — producer / store / consumer or N-column comparison. |
| [`templates/graph-diagram-skeleton.svg`](templates/graph-diagram-skeleton.svg) | `diagram-type-graph.md` | Asymmetric hub-and-spoke scaffold — central hub, single primary node on the left, stack of secondary nodes on the right. |
| [`templates/flow-diagram-skeleton.svg`](templates/flow-diagram-skeleton.svg) | `diagram-type-flow.md` | Multi-track flow scaffold — two horizontal tracks with a Y-junction, a Bézier loop, and stage waypoints. |
| [`templates/stack-diagram-skeleton.svg`](templates/stack-diagram-skeleton.svg) | `diagram-type-stack.md` | Three-slab stack scaffold with dashed inter-slab dividers, left-region label gutter, right-region content, and a consumer node on the right with convergent connectors. |

Each starter carries the canonical `<style>` block, arrow marker, theme-neutral palette, and placeholder content shaped to the diagram type's geometry. Copy the matching template, rename, fill in.

## Workflow

### Step 1 — Pick a diagram type

Choose from the per-diagram-type standards. If none of the existing types fit, treat this as a sign that a new diagram-type standard is needed; consult the user before inventing a new pattern.

### Step 2 — Pick a theme-handling strategy

Read [`standards/theme-handling.md`](standards/theme-handling.md) and pick one of the three strategies. Strategy choice depends on contrast needs and rendering surface (does the SVG ship inside an AsciiDoc page, a Markdown README, both?). Record the strategy in a comment at the top of the SVG.

### Step 3 — Author the SVG

Copy the matching template from `templates/`. Fill in content, sticking to the palette and typography in [`standards/visual-language.md`](standards/visual-language.md). Save under `doc/resources/diagrams/{name}.svg`.

### Step 4 — Verify the render (MANDATORY, BLOCKING)

This step is **non-skippable**. Do not present the SVG to the user, embed it in an AsciiDoc page, or commit it without completing the verification below. See the matching Constraint in the Enforcement section above for the rationale.

Render the SVG against both GitHub themes:

```bash
rsvg-convert -b "#ffffff" -w 1200 -o /tmp/diagram-light.png path/to/diagram.svg
rsvg-convert -b "#0d1117" -w 1200 -o /tmp/diagram-dark.png  path/to/diagram.svg
```

Then **read back both PNGs**. In Claude Code, use the `Read` tool on each PNG path so the rasterised result enters the agent's working set — do not rely on having authored the markup correctly. In a local editor, open both files in a viewer.

Verification checklist — every item must be visually confirmed against the rendered PNGs (not the SVG source):

- [ ] Every text run is legible on both backgrounds (light and dark).
- [ ] Every stroke / arrow / divider is visible on both backgrounds (no `#000` on dark, no `#fff` on light, no near-white-on-white from a typo in the theme rules).
- [ ] No content is clipped at the `viewBox` edges (especially long monospace identifiers that may extend past the column box).
- [ ] Alignment is visually consistent — centered content sits on the column midline, left-aligned content shares a consistent left edge.
- [ ] Arrow markers terminate at the right point (no orphan arrowheads floating in whitespace, no missing markers).
- [ ] Captions / labels do not collide with adjacent elements (arrows, separators, neighbouring text).
- [ ] Font fallback rendered as expected (no glyph substitution to Times-style serif where ui-sans-serif was intended).

If any item fails, fix the SVG and re-render. Repeat until the checklist passes on both themes.

**For the full QA process** — additional defect classes the checklist above does not catch (text overflow inside containers, intra-diagram stylistic consistency, curve smoothness, cross-diagram parity, label collisions, smell test), repair workflow, common defect catalogue, and pre-commit gate — see [`standards/visual-qa.md`](standards/visual-qa.md). The Step 4 checklist is the floor; the visual-QA standard is the bar.

**Only after both checklists pass** does authoring move to Step 5.

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
