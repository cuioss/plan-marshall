# Diagram Type — Block / Data-Flow

The first per-diagram-type standard. Covers multi-column block diagrams: producer / store / consumer layouts, side-by-side comparisons, and any "N labelled boxes connected by labelled arrows" structure.

Reference implementation: `doc/resources/diagrams/findings-pipeline.svg`.

## When to use this type

Use a block diagram when the relationship between things is **flow** (data, control, dispatch) or **side-by-side comparison** (alternatives that share a structure). Specifically:

- **Producer / consumer flow** — the canonical use. One or more producers add to a store; one or more consumers read from the store and act.
- **Pipeline stages** — left-to-right transformation through named stages.
- **Layered architecture** — top-to-bottom layers each with their own concerns.
- **Comparative panels** — two or more alternatives in adjacent columns with arrows showing relationships.

Use a different diagram type when:

- The structure is a **sequence over time** → use the (future) sequence diagram type.
- The structure is **states and transitions** → use the (future) state-machine diagram type.
- The structure is a **DAG of dependencies** → use the (future) graph diagram type.

## Layout grid

Block diagrams divide the canvas into vertical **columns** separated by **gutters**. Each column has a header at the top and content beneath. Arrows live in the gutters, never inside columns.

```text
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  COL HEADER  │  │  COL HEADER  │  │  COL HEADER  │
├──────────────┤  ├──────────────┤  ├──────────────┤
│              │  │              │  │              │
│   content    │──▶   content    │──▶   content    │
│              │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘

   COLUMN 1       gutter           gutter
   (260 wide)     (40 wide)        (40 wide)
```

### Standard configurations

| Columns | viewBox | Column width | Use |
|---------|---------|--------------|-----|
| 2 | `0 0 700 500` | 300 | Producer ⟶ consumer, two-option comparison |
| 3 | `0 0 900 500` | 260 | Producer / store / consumer (the default) |
| 4 | `0 0 1100 500` | 240 | Multi-stage pipeline |

Width × N columns + 40 × (N-1) gutters + 40 outer margin per side = viewBox width. The 8-pixel-grid principle applies — round to multiples of 8 when adjusting.

## Content positioning

### Headers

Column headers are **centered horizontally** on the column's midline. y-coordinate: 28. Header class: `col-header`, sans-serif, 15px / 600 weight (see [`visual-language.md`](visual-language.md) § Typography).

### Item lists (left-aligned items)

When a column's content is a list of items with hierarchical structure (bold header + sub-items, e.g. `phase-6-finalize` + indented sub-steps), **left-align** the list:

- First item left edge: `column_left + 16`.
- Bold header: `class="item-bold"`.
- Sub-items: indented 14 px from the bold parent.
- Vertical spacing: 18–22 px between adjacent items.

### Item lists (centered items)

When a column's content is a flat list of equivalent items (e.g. JSONL filenames in the manage-findings store), **center-align** the list on the column midline. This matches the centered column header and looks intentional.

The choice between left- and center-aligned lists is made per column based on whether the content has hierarchical structure. **Do not mix alignments inside the same column.** If one column is centered and a sibling column is left-aligned, the contrast reads as deliberate (different content shape gets different alignment). If alignments alternate within a column, the diagram looks broken.

### Box around the column

Each column gets a rounded-rectangle container box per [`visual-language.md`](visual-language.md) § Geometry:

```svg
<rect class="stroke" x="20" y="44" width="260" height="420" rx="6" ry="6"/>
```

`rx="6"`, stroke 1.2 px, fill="none". The box starts 16 px below the column header baseline.

## Arrows and labels

### Inter-column arrows

Arrows live in the gutter between columns. Two patterns:

**Single-direction (producer → store):**

```svg
<line class="arrow" x1="280" y1="220" x2="316" y2="220" marker-end="url(#arrow)"/>
<text x="298" y="212" class="muted" text-anchor="middle">add</text>
```

**Bi-directional (store ↔ consumer — query / resolve):**

```svg
<line class="arrow" x1="584" y1="205" x2="616" y2="205" marker-end="url(#arrow)"/>
<text x="600" y="197" class="muted" text-anchor="middle">query</text>

<line class="arrow" x1="616" y1="240" x2="584" y2="240" marker-end="url(#arrow)"/>
<text x="600" y="232" class="muted" text-anchor="middle">resolve</text>
```

The two arrows are offset vertically by ~35 px so their labels do not collide. Label y-coordinate sits 8 px above the arrow line.

### Intra-column markers

Dashed horizontal lines separate logical groups inside a column box (see the JSONL group separators in `findings-pipeline.svg`):

```svg
<line class="sep" x1="360" y1="125" x2="540" y2="125"/>
```

Centered, 180 px wide inside a 260-wide column, dasharray `3 3`. Use sparingly — at most 2–3 separators per column.

## Footer caption

A column may have a centered italic caption at the bottom summarising its theme. Use for the column header's mental complement ("script-based · deterministic" beneath the PRODUCERS column, "FIX · SUPPRESS · ACCEPT · ASK" beneath CONSUMERS). Caption position: 30 px above the column box's bottom edge. Class: `col-sub`.

## Annotated template

The skeleton template at [`../templates/block-diagram-skeleton.svg`](../templates/block-diagram-skeleton.svg) contains a three-column structure with the standard style block, marker definition, and placeholder content. Copy it to start a new block diagram and replace the placeholders.

## Reference implementation

`doc/resources/diagrams/findings-pipeline.svg` is the canonical block diagram in the user-facing docs. It demonstrates:

- Three-column 900 × 500 layout.
- Centered header + subtitle for the middle column.
- Left-aligned hierarchical content in PRODUCERS and CONSUMERS columns.
- Center-aligned flat-list content in the middle column (deliberate alignment contrast).
- Dashed group separators in the middle column.
- Bi-directional gutter arrows between store and consumers.
- Footer captions in two of the three columns.
- Theme-neutral palette (Strategy A from [`theme-handling.md`](theme-handling.md)).

Use it as the template for any producer / store / consumer diagram.
