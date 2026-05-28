# Diagram Type — Flow

Covers diagrams whose structure is **directed movement through stages over time** — pipelines, shipping flows, lifecycle progressions, multi-track parallel processes that converge. Distinguished from the block type by the priority of *time / direction* over *content per box*.

Reference implementation: `doc/resources/diagrams/post-execute-shipping-flow.svg`.

## When to use this type

Use a flow diagram when the relationship between stages is **directional and temporal**:

- **Single-track pipeline** — left-to-right progression where each stage's output is the next stage's input.
- **Multi-track / branching flow** — two or more parallel tracks that diverge, run in parallel, and converge at a junction (the canonical git-history-graph shape).
- **Lifecycle with loops** — a forward path that includes an iteration loop (review feedback, rework cycles).

Use a different diagram type when:

- The structure is **side-by-side comparison without directional flow** → `diagram-type-block`.
- The structure is **a network of structural relationships** → `diagram-type-graph`.
- The structure is **stacked layers** with no time dimension → `diagram-type-stack`.
- The structure is **states and transitions over time, with branching by condition** → the (future) state-machine type.

The block type can express a flow as a left-to-right chain of equal-weighted columns; the flow type is for when the *geometry* of the flow (track variance, junctions, loops) carries information that columns cannot.

## Composition

The load-bearing visual element is the **track line** — a thin horizontal line that the reader's eye follows from origin to destination. Stages are *waypoints* on the track, not parallel containers. Multiple tracks run as parallel horizontal lines at different y-coordinates; they converge at a Y-junction or diverge at an inverted-Y.

### Canonical multi-track layout

```
  feature-branch track  ─────[A]──[B]──[loop↻]──[C]──┐
                                                      ├──[merge]──
  main-branch track     ──────────────────────────────┘             ────[D]────►
```

The feature-branch track starts at the left, hits its stages (A / B / loop / C), then drops down to merge into the main-branch track. The main-branch track runs the full width; everything after the merge happens on it.

### Track lines

| Element | Style |
|---------|-------|
| Track line (active path) | `stroke: #6e7681; stroke-width: 1.5;` (matches arrow stroke) |
| Junction / divergence point | a small unfilled circle on the track, radius `4` |
| Loop arc (iteration inside a track) | a single quadratic Bézier curve with the arrow marker pointing back to the loop's start; label `loop` or `iterate` near the curve's apex |
| Arrowhead | only at the destination of the flow (end of main track), not at every stage waypoint |

### Stage waypoints

Each stage is a small rounded rectangle on the track. Stages share a uniform size (the standard `120 × 60` waypoint dimensions) — variance in stage box size signals "different kind of stage" and should be used deliberately.

The stage label is **above** the track line; the optional sub-detail is **below** the track line. The track line passes *through* the stage box (visually entering one side and exiting the other), reinforcing "this stage is part of the flow, not a separate thing flow visits."

### Shape variation per stage type (the elevating technique)

Within the same flow, vary the stage shape by role:

- **Event stage** (something happens, instantaneous) — rounded rectangle, `rx: 6`.
- **Process stage** (work that takes time) — taller rounded rectangle, `rx: 6`, taller `height`.
- **Decision / junction** — diamond or circle, no `rx`.
- **Loop indicator** — no box, just the Bézier arc with a `↻` or `loop` label.

This is the design technique that elevates a flow diagram beyond a generic "boxes connected by arrows" layout. Same palette, same stroke widths, different shapes — the geometry tells the reader which stage is a moment vs which is a process.

### Standard `viewBox` for flow diagrams

| Pattern | viewBox | Notes |
|---------|---------|-------|
| Single-track flow, 3-5 stages | `0 0 1000 280` | Wide-and-shallow. Track at y=140 (centred vertically). |
| Multi-track flow with merge | `0 0 1100 360` | Two tracks: feature at y=130, main at y=240. Y-junction zone in the right third. |
| Single-track with loop | `0 0 1000 320` | Track at y=180 with loop arc above. |

## Content positioning

### Stage labels

- **Header (event / process name)** — above the stage box, `15 px / 600 weight / sans-serif`, centred on the stage's x-coordinate.
- **Sub-detail (concrete content)** — below the stage box, `11 px italic`, centred. Use sparingly — only when the stage's label alone doesn't communicate the role.

### Track labels

When a flow has multiple tracks, label each track at the left edge of the canvas. Use the standard column-header typography (`15 px / 600 weight`).

### Junction labels

At a Y-junction (merge), place the junction label *above* the convergence point in italic — `merge`, `join`, `converge`. Single word, italic, no box.

## Anti-patterns

- **Equally-spaced boxes with horizontal arrows between them**: that's a block diagram in disguise, not a flow. If every stage is the same shape and the only differentiator is the arrow, the flow type isn't pulling its weight; use `diagram-type-block` instead.
- **Track lines that don't visually pass through stages**: the flow nature is lost if stage boxes float disconnected from the line. Always route the track line *through* the stages.
- **Decorative bends and zigzags**: a flow track is a straight horizontal line plus optional Y-junctions and Bézier loops. No serpentine paths. The geometry should be readable in one glance.
- **Arrowheads at every stage**: the flow direction is established by the track line plus the single terminal arrowhead. Intermediate arrows add visual noise without clarity.

## Worked example

`doc/resources/diagrams/post-execute-shipping-flow.svg` is the canonical multi-track flow diagram. It demonstrates:

- Two horizontal tracks: feature branch (top) and main branch (bottom).
- Four stage waypoints on the feature track (in-flight plan, push, PR cycle with loop, approved-and-merged junction).
- Bézier loop on the feature track for the PR review iteration.
- Y-junction where the feature track drops into the main track.
- One stage on the main track after the junction (back-on-main + clean tree).
- Terminal arrowhead only at the right edge of the main track.
- Footer caption naming the load-bearing idea ("A fixed shipping arc — PR review and merge are first-class steps").

## Annotated template

The skeleton template at [`../templates/flow-diagram-skeleton.svg`](../templates/flow-diagram-skeleton.svg) carries the standard `<style>` block, the arrow marker, a two-track scaffold with a Y-junction and a Bézier loop, and placeholder stage waypoints. Copy it to start a new flow diagram and replace the placeholders.
