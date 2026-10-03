# Diagram Type — Stack

Covers diagrams whose structure is **layers stacked on top of each other** — telemetry layers, abstraction layers, enforcement layers, any "stacked-cake" composition where the vertical position carries semantic weight.

Reference implementation: `doc/resources/diagrams/audit-trail-layers.svg`.

## When to use this type

Use a stack diagram when the relationship is **vertical layering with shared context**:

- **Telemetry / artefact layers** — multiple recording surfaces stacked, each thinner or denser than the next, all feeding one consumer.
- **Abstraction layers** — top layer is the highest abstraction, bottom is the implementation surface. Each layer's interior shows what it owns.
- **Enforcement / responsibility layers** — soft to hard, top to bottom (or the inverse).

Use a different diagram type when:

- The layers are **side-by-side instead of stacked** → `diagram-type-block`.
- The layers have **directional flow between them over time** → `diagram-type-flow`.
- The relationship is **a network of structural connections**, not stacked → `diagram-type-graph`.

The block type with vertical columns can express layers as columns, but the *literal stacking* of the stack type — where each layer is a horizontal slab and the reader's eye travels top-to-bottom — is what makes the layering legible. If your concept page says "three layers," draw three slabs, not three columns.

## Composition

The load-bearing visual element is the **horizontal slab**. Each layer is a slab spanning most of the canvas width. Slabs are separated by thin dashed dividers (the "cake-layer" feel) — they're related but distinct.

### Canonical layered stack

```text
  ┌─────────────────────────────────────────────────┐
  │ LAYER 1   │ contents — what the layer holds      │
  └─────────────────────────────────────────────────┘
   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  ┌─────────────────────────────────────────────────┐
  │ LAYER 2   │ contents                             │
  └─────────────────────────────────────────────────┘
   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  ┌─────────────────────────────────────────────────┐
  │ LAYER 3   │ contents                             │
  └─────────────────────────────────────────────────┘
```

### Slab structure

Each slab has two regions:

- **Left region (~25%)** — the layer's name in display weight (`15 px / 600 weight / sans-serif`), with an optional one-line italic sub-label. Acts as a label gutter — the reader's eye scans down the left edge to enumerate the layers.
- **Right region (~75%)** — the layer's contents, listed in monospace for code-identifier rows or sans-serif for prose rows. Left-aligned, generous intra-row spacing.

A vertical dashed separator between the two regions reinforces the label-vs-content distinction.

### Inter-slab dividers

Between slabs, a single horizontal dashed line spans the full slab width (`stroke-dasharray: 3 3`, `stroke-width: 0.6`, neutral `#6e7681`). The divider says "different layer, same medium" — distinct but related.

### Asymmetric slab heights — the elevating technique

Slabs in a stack should NOT all be the same height. The slab's height reflects the density of its contents: a layer with two items is shorter than a layer with eight. This asymmetry communicates information density without resorting to colour or decoration. Use a minimum height (`60 px`) so a slim layer still reads as a layer.

### Convergence on a consumer (optional)

When the stack has a downstream consumer (a node that reads from every layer), place the consumer to the **right** of the stack as a single bounding box, vertically centred. Three thin connector lines (`stroke-width: 1`, no arrowhead) reach out from the right edge of each slab and converge on the consumer node's left edge. Optional `arrow` markers at the consumer end signal "all layers feed this one consumer."

### Standard `viewBox` for stack diagrams

| Pattern | viewBox | Notes |
|---------|---------|-------|
| Pure stack, no consumer | `0 0 900 480` | Slabs span `40 → 860`. Variable heights. |
| Stack with consumer on the right | `0 0 1100 480` | Slabs span `40 → 760`; consumer at `820 → 1060`, vertically centred on the stack's vertical midpoint. |

## Content positioning

### Layer labels

- Header inside the left region of the slab: `15 px / 600 weight`, left-aligned with the slab's left padding.
- Optional sub-label below the header: `11 px italic`, same left edge.

### Slab contents

Right region, left-aligned with the slab's right-region left edge. Monospace for identifiers; sans-serif italic for prose qualifiers. Rows separated by `18-22 px` per the standard intra-column spacing.

### Consumer node

- Single bounding rectangle, vertical centre aligned with the stack's vertical midpoint.
- Bold label in `14 px / 600 weight / sans-serif`, centred horizontally inside the box.
- Optional sub-label below in `11 px italic`.

## Anti-patterns

- **All slabs identical height regardless of content**: the asymmetric heights are the visual signal that the layers differ in density. Forcing identical heights makes the stack read as a grid.
- **Decorative gradients or fills inside slabs**: flat aesthetic per `visual-language.md`. Layers are differentiated by their content and label, not by colour.
- **Dividers that are solid lines**: solid lines make the slabs look like a single composed box. The dashed divider is the "layer-cake" cue — keep it dashed.
- **Connector lines that cross slabs**: when a consumer is present on the right, the connectors run *outside* the stack to the consumer, not *through* the stack. Crossing layers is visual noise.

## Worked example

`doc/resources/diagrams/audit-trail-layers.svg` is the canonical layered-stack diagram. It demonstrates:

- Three horizontal slabs of different heights (logs / structured artefacts / findings), the artefacts and findings slabs taller than the logs slab to reflect content density.
- Left-region label gutter with header + italic sub-label per layer.
- Right-region content listings in monospace.
- Dashed inter-slab dividers.
- Right-side consumer node (`plan-retrospective`) with three convergent connectors.
- Footer caption naming the load-bearing idea ("Three telemetry layers, one retrospective consumer").

## Annotated template

The skeleton template at [`../templates/stack-diagram-skeleton.svg`](../templates/stack-diagram-skeleton.svg) carries the standard `<style>` block, the arrow marker, three stacked slabs with the canonical left-gutter / right-content split, dashed inter-slab dividers, a consumer node on the right, and placeholder content. Copy it to start a new stack diagram and replace the placeholders.
