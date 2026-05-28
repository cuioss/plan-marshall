# Diagram Type — Graph / Topology

Covers diagrams whose structure is a network of nodes connected by relationships — hub-and-spoke topologies, dependency graphs, radial relationships, any "central thing surrounded by related things" composition.

Reference implementation: `doc/resources/diagrams/plan-worktree-topology.svg`.

## When to use this type

Use a graph diagram when the relationship between things is **structural / topological**, not flow-directed:

- **Hub-and-spoke** — one central element with N peripheral elements that share a relationship to the hub (a shared resource feeding many consumers, a registry with many entries, a coordinator with many workers).
- **Radial / star** — a focal concept with categorised relationships radiating outward.
- **Asymmetric pairing** — a single primary element paired with a stack of related elements, where the primary is visually distinguished and the related elements share a uniform shape.
- **Dependency graphs** (acyclic) — where the topology is the message and the direction of edges is secondary to the connection pattern.

Use a different diagram type when:

- The relationship is **flow over stages** → `diagram-type-flow`.
- The relationship is **side-by-side comparison** → `diagram-type-block`.
- The relationship is **states and transitions over time** → the (future) sequence / state-machine types.
- The relationship is **layers stacked on top of each other** → `diagram-type-stack`.

## Composition

A graph diagram is a **single dominant visual idea**, not a grid of equally-weighted columns. The hub is visually heavier than the spokes. The reader's eye lands on the hub first; the spokes are the periphery.

### Hub-and-spoke layout (canonical)

```
                  ┌──────────┐
                  │   spoke  │
                  └────┬─────┘
                       │
                       │
   ┌──────────┐    ┌───┴───┐    ┌──────────┐
   │  spoke   │────│  HUB  │────│   spoke  │
   └──────────┘    └───┬───┘    └──────────┘
                       │
                       │
                  ┌────┴─────┐
                  │   spoke  │
                  └──────────┘
```

For an asymmetric variant (one primary node + a stack of secondary nodes on one side), place the primary to the left of the hub and the stack to the right. The reader's eye still lands on the hub; the asymmetry communicates "different kinds of relationship."

### Weight differentiation — the load-bearing technique

The graph type avoids visual sameness through **stroke and size weight**, not color:

- **Hub stroke**: `1.6 px` (thicker than the standard `1.2 px`). Slightly larger overall bounding box. Optional inset content (commits, refs, fields) listed in monospace to communicate "data store."
- **Spoke stroke**: standard `1.2 px`. Uniform size across all spokes — they're peers.
- **Connector lines**: thin `1 px` (lighter than the standard `1.5 px` arrows). No arrowheads — the topology is structural, not directional. If direction matters, add small `read` / `write` labels along the line.

### Standard `viewBox` for graph diagrams

| Pattern | viewBox | Notes |
|---------|---------|-------|
| Asymmetric hub (1 primary + hub + stack) | `0 0 900 540` | Hub centred, primary node left, stacked nodes right. The reference. |
| Symmetric radial (hub + 4 peers) | `0 0 700 700` | Square canvas; hub centred; peers at 12/3/6/9 o'clock. |
| Symmetric radial (hub + 6 peers) | `0 0 800 800` | Hub centred; peers at 12/2/4/6/8/10 o'clock. |

## Content positioning

### The hub

Centred on the canvas (or slightly offset for asymmetric layouts). Bounding box stroke `1.6 px`. Header inside the hub uses the standard column-header typography (`15 px / 600 weight / sans-serif`). Optional inset list of contents uses monospace, centred or left-aligned per content nature.

### The spokes

Each spoke is a smaller bounding box (typically half the hub's area or less). Stroke `1.2 px`. Label inside the spoke uses the standard `12 px monospace` for identifiers, `15 px sans-serif` for category names. Spokes share a uniform size *within a group* — if one spoke is bigger than its peers, it reads as the wrong type.

For the asymmetric hub variant: stack the secondary nodes on one side with consistent inter-node spacing (`22 px` is the standard intra-column spacing from `visual-language.md`).

### Connectors

Hub-to-spoke connector: a single straight line with stroke `1 px`. No arrowhead (use the standard `arrow` marker only when direction is load-bearing). Optional label centred along the line in `11 px italic`.

For asymmetric layouts where direction matters (the hub *reads from* one side and *writes to* another), use the standard `1.5 px` arrow with marker, and a one-word label (`reads`, `writes`).

## Naming and accessibility

Same conventions as `visual-language.md`:

- File: `kebab-case.svg`, matching the concept it depicts (`plan-worktree-topology.svg`, `extension-topology.svg`).
- `<title>`: one-sentence accessible name.
- `<desc>`: paragraph describing the topology's meaning — what the hub is, what the spokes are, what the relationship between them is.
- `role="img"`, `aria-labelledby="title desc"`.

## Anti-patterns

- **All-nodes-equal-weight**: every box the same size, same stroke. The graph type's power is the weight differentiation between hub and spokes; losing that turns the diagram into a generic block layout in disguise.
- **Arrowheads everywhere**: graph relationships are structural, not directional. Reserve arrows for the explicit `reads`/`writes` case.
- **Over-decoration of the hub**: the hub already wins by being centred and thicker-stroked; don't add additional visual weight via background fills, shadows, or accent colours. Flat aesthetic.
- **Symmetric layouts that aren't symmetric**: if you have 3 spokes, don't pretend it's a 4-arm radial with one empty arm. Use the asymmetric hub variant instead.

## Worked example

`doc/resources/diagrams/plan-worktree-topology.svg` is the canonical asymmetric hub diagram in the user-facing docs. It demonstrates:

- Central `.git` hub with `1.6 px` stroke, monospace-listed contents (commits / refs / objects / hooks).
- Single primary node (developer's main checkout) on the left.
- Stack of three secondary nodes (plan worktrees) on the right.
- Unlabelled `1 px` connector lines from hub to every node (the topology is the message).
- `read` / `write` annotations on two of the connectors where direction is load-bearing.
- Footer caption naming the load-bearing idea ("Many working trees, one repository").

Use it as the template for any hub-and-spoke or asymmetric-pairing diagram.

## Annotated template

The skeleton template at [`../templates/graph-diagram-skeleton.svg`](../templates/graph-diagram-skeleton.svg) carries the standard `<style>` block, the arrow marker definition, an asymmetric hub-and-spoke scaffold (hub centred, primary node left, stacked secondary nodes right), and placeholder content. Copy it to start a new graph diagram and replace the placeholders.
