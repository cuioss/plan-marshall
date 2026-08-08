# Diagram Type — Sequence

Second per-diagram-type standard. Covers sequence diagrams: time-ordered exchanges between actors, where the spatial axis is actor identity and the vertical axis is time.

Reference implementation: `doc/resources/diagrams/build-dispatch-sequence.svg`.

## When to use this type

Use a sequence diagram when:

- The **message ordering between actors is the meaning** — request/response, dispatch, return.
- **Time matters more than topology** — "X happens, then Y".
- You need to show a **synchronous call shape with explicit wait periods** (e.g. the build dispatch's "LLM suspends while the build runs").
- You need to show **producer/consumer interactions across multiple actors over time** that a block diagram would flatten.

Use a different diagram type when:

- The relationship is static ("X depends on Y") → block diagram ([`diagram-type-block.md`](diagram-type-block.md)).
- The structure is states + transitions of one entity → state diagram (`diagram-type-state.md`, when authored).
- The structure is a fan-out tree (one caller, many callees) → graph diagram (`diagram-type-graph.md`, when authored).

## Layout

### `viewBox`

| Actor count | viewBox | Actor x positions |
|-------------|---------|--------------------|
| 2 actors | `0 0 700 540` | 175, 525 |
| 3 actors | `0 0 900 540` | 150, 450, 750 |
| 4 actors | `0 0 900 560` | 110, 360, 600, 830 |
| 5 actors | `0 0 1100 560` | 100, 320, 540, 760, 990 |

Pick the smallest viewBox that fits the message count comfortably. Sequence diagrams scale vertically with message count; budget ~35 px per message row.

### Actor headers

Each actor sits at a fixed `x`. The header is a small rounded box at the top, centered on the actor's `x`:

```svg
<text x="110" y="30" class="col-header">LLM workflow</text>
<rect class="stroke" x="50" y="42" width="120" height="36" rx="6"/>
```

Width is 120 px by default; widen only if the header label cannot fit. Header text uses `class="col-header"`.

### Lifelines

A dashed vertical line drops from each actor's header to the bottom of the diagram, marking the actor's existence over time. Uses the existing `.sep` class (dashed):

```svg
<line class="sep" x1="110" y1="80" x2="110" y2="500"/>
```

Lifelines start at `y=80` (just below the actor headers) and extend to a `y` that covers all messages plus a footer caption.

## Messages

Horizontal arrows between two lifelines. Time flows downward — each successive message sits below the previous.

### Request / call (solid arrow)

Uses the standard `.arrow` class:

```svg
<line class="arrow" x1="110" y1="120" x2="360" y2="120" marker-end="url(#arrow)"/>
<text x="235" y="112" class="arrow-lbl">resolve --command verify --module X</text>
```

Label sits 8 px above the arrow line, centered on the midpoint between the source and target lifelines.

### Response / return (dashed arrow)

Returns use a **dashed arrow** to visually distinguish them from forward requests. This requires the `.arrow-return` class (declared below in § CSS additions):

```svg
<line class="arrow-return" x1="360" y1="150" x2="110" y2="150" marker-end="url(#arrow)"/>
<text x="235" y="142" class="arrow-lbl">executable: ./mvnw verify -pl X</text>
```

### Self-message (loop on one lifeline)

Rare; when an actor calls itself, draw a horizontal arrow that loops out and back. Use a small curved path:

```svg
<path class="arrow" d="M 110 200 Q 160 200 160 215 Q 160 230 110 230" marker-end="url(#arrow)"/>
```

Self-messages should be the exception. If an actor self-calls more than once in a diagram, consider whether a state-machine diagram fits better.

## Activation bars

A **thin rectangle on a lifeline** marks the period when that actor is actively doing work (holding the synchronous flow of control). For a typical synchronous request the activation bar covers the period from the inbound request to the outbound response.

Uses the `.activation` class (declared below):

```svg
<rect class="activation" x="595" y="225" width="10" height="120"/>
```

Width is 10 px (5 px on each side of the lifeline). Height = activation duration in y-coordinate space.

Activation bars are **optional but strongly recommended** — they make the "who is doing work right now" and "who is waiting" relationship visually explicit. The synchronous-wait shape of the build dispatch story is unreadable without them.

## Notes / annotations

Italic text labels attached to (or near) a lifeline, communicating side information. Use `class="col-sub"` for centered notes, or `class="arrow-lbl"` for short inline annotations.

A common pattern is a **"⏳ waiting"** annotation centered between two columns during the long activation period of one of them. Position the text at the midpoint and use a muted style.

## CSS additions for this diagram type

In addition to the standard classes documented in [`visual-language.md`](visual-language.md), sequence diagrams require two new classes:

```css
.arrow-return {
  stroke: #6e7681; stroke-width: 1.5; fill: none;
  stroke-dasharray: 5 4;
}
.activation {
  stroke: #6e7681; stroke-width: 0.8; fill: #6e7681; opacity: 0.15;
}
```

For Strategy B (theme-aware) diagrams, the same swap pattern applies — both colors travel via `@media (prefers-color-scheme: dark)` per [`theme-handling.md`](theme-handling.md).

These classes are sequence-diagram-specific. Other diagram types should not use them.

## Naming conventions

| Element | Convention |
|---------|-----------|
| Actor names | Match the real implementation: skill notation (`build-maven`), agent name (`execution-context`), system name (`build process`). |
| Message labels | The actual command or operation, abbreviated only when necessary for fit. `run --command-args "verify"` is better than "run build". |
| Diagram title | `<title>` element: "{Caller} dispatches {operation} — synchronous flow". |

## Reference implementation

`doc/resources/diagrams/build-dispatch-sequence.svg` — the canonical sequence diagram for the synchronous build dispatch shape. Four actors (LLM caller, architecture resolver, build-{tool} skill, build process subprocess), six messages, activation bars showing the long-running build subprocess and the short log-parse period, a "⏳ LLM suspended" annotation in the middle gutter during the wait.

Use it as the template for any synchronous call-shape diagram in the user-facing docs.
