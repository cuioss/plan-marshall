# Diagram Type — State

Third per-diagram-type standard. Covers state machines and lifecycles — discrete states of one entity over time, with transitions between them. The vertical or horizontal axis carries time / control flow, not actor identity.

Reference implementation: `doc/resources/diagrams/phase-lifecycle.svg`.

## When to use this type

Use a state diagram when:

- The structure is **states + transitions of one entity** — e.g. a plan moving through `phase-1-init → … → phase-6-finalize`, a finding moving through `pending → fixed`, a worktree moving through `created → active → archived`.
- Transitions carry **named conditions** (gates, predicates, outcomes).
- Loop-back / cycle structure matters — a forward-only progression doesn't need this type, but anything with a back-edge usually does.

Use a different diagram type when:

- Multiple entities interact across time → sequence diagram ([`diagram-type-sequence.md`](diagram-type-sequence.md)).
- The structure is "X depends on Y" or "X produces Y" with no temporal axis → block diagram ([`diagram-type-block.md`](diagram-type-block.md)).
- The structure is a fan-out tree (one node, many children) without states or transitions → graph diagram (`diagram-type-graph.md`, when authored).

## Layout

### `viewBox`

| Topology | viewBox | Notes |
|----------|---------|-------|
| Linear 4-state | `0 0 900 400` | Four nodes in a row + optional back-edge below. |
| Linear 6-state | `0 0 1100 400` | Six nodes in a row + optional back-edge below. The plan-lifecycle reference. |
| Branching (2-3 states with multiple transitions) | `0 0 700 500` | Vertical layout works well. |
| Hub-and-spoke (one central, ≤5 satellites) | `0 0 900 600` | Centred hub, satellites at angles. |

Linear layouts are the default. Pick a non-linear topology only when the state graph is genuinely non-linear (multiple back-edges, branching, self-transitions).

### Node positioning

In a linear N-state layout:

```
node-x[i] = (viewBox_width / (N + 1)) * (i + 1)
```

So for N=6 with viewBox 1100: nodes at x = 157, 314, 471, 628, 785, 942 (round to 160, 315, 470, 625, 780, 940 for the 8-px grid).

Node `y` is the canvas vertical midline minus half the node height, biased upward by ~20 px so back-edges have room below.

### Node shape

State nodes are **rounded rectangles**, 120 × 60 px by default. Use the existing `.stroke` class for the border and standard font classes for the content:

```svg
<rect class="stroke" x="100" y="170" width="120" height="60" rx="8" ry="8"/>
<text x="160" y="195" class="col-header">1 · init</text>
<text x="160" y="215" class="col-sub">phase-1</text>
```

The corner radius for states is **8 px** (slightly more rounded than the default 6 px for container boxes) — this visual cue distinguishes "states" from "containers".

For initial / final states (when relevant), follow UML convention:

```svg
<!-- initial state: filled circle -->
<circle class="stroke" cx="40" cy="200" r="6" fill="#6e7681"/>

<!-- final state: ringed circle -->
<circle class="stroke" cx="1060" cy="200" r="10"/>
<circle cx="1060" cy="200" r="6" fill="#6e7681"/>
```

These are optional. Many plan-marshall state machines don't have a "final" state in the UML sense (e.g. plans are archived, not terminated); omit them when they don't add meaning.

## Transitions

Transitions are arrows between state nodes. Use the standard `.arrow` class.

### Forward transition (linear)

A simple horizontal arrow between two adjacent state nodes:

```svg
<line class="arrow" x1="220" y1="200" x2="316" y2="200" marker-end="url(#arrow)"/>
<text x="268" y="192" class="arrow-lbl">condition / gate</text>
```

The label above the arrow names the transition's condition or guard (e.g. `init_without_asking`, `execute_without_asking`, `loop_back outcome`).

### Back-edge / loop-back

A curved arrow that returns from a downstream state to an upstream state. Use a quadratic Bezier path that dips below the state row:

```svg
<path class="arrow"
      d="M 940 230 Q 940 320, 850 320 Q 760 320, 760 230 Q 760 280, 780 270"
      marker-end="url(#arrow)"/>
<text x="850" y="335" class="arrow-lbl">loop_back outcome</text>
```

The dip y-distance is ~80 px below the node bottom — enough that the arrow visibly leaves the linear row and returns.

### Self-transition

A small loop arrow attached to one side of a state node:

```svg
<path class="arrow"
      d="M 220 185 Q 270 165, 270 200 Q 270 235, 220 215"
      marker-end="url(#arrow)"/>
<text x="290" y="200" class="arrow-lbl">self-condition</text>
```

Self-transitions are common for the `refine` loop and the `verify` loop. Place the loop on whichever side of the node has free space.

### Conditional fork (one source, multiple targets)

When a state branches to multiple successors, draw multiple arrows from the same source node, each with its own condition label. Position the targets above / below / right of the source as the layout allows.

```svg
<!-- success path -->
<line class="arrow" x1="220" y1="190" x2="316" y2="170" marker-end="url(#arrow)"/>
<text x="265" y="175" class="arrow-lbl">success</text>

<!-- failure path -->
<line class="arrow" x1="220" y1="210" x2="316" y2="230" marker-end="url(#arrow)"/>
<text x="265" y="240" class="arrow-lbl">failure</text>
```

## CSS additions for this diagram type

State diagrams use the existing standard classes — no new classes required beyond what `visual-language.md` defines. The 8-px corner radius for state nodes is an attribute on the `<rect>` (`rx="8" ry="8"`), not a class.

## Naming conventions

| Element | Convention |
|---------|-----------|
| State name | The implementation identifier — e.g. `phase-1-init`, not "Initialisation Phase". Use the kebab-case form developers recognise. |
| State subtitle | A one-word qualifier under the state name if needed (e.g. "phase-1" under "init"). Optional. |
| Transition label | The condition name in the implementation — e.g. `init_without_asking`, `loop_back outcome`, `confidence_threshold`. Use the actual marshal.json key or workflow-return field, not a paraphrase. |
| Diagram title | "{Entity} lifecycle — {key feature}". The reference's title is "Plan lifecycle — six-phase forward flow with finalize → execute loop-back". |

## Anti-patterns specific to state diagrams

In addition to the anti-patterns in `visual-language.md`:

- **Implicit transitions** — every arrow must carry a label naming its condition. An unlabelled transition reads as "it just happens"; the reader cannot reproduce the decision.
- **Mixing event-driven and outcome-driven transitions on the same diagram** without distinguishing them visually. Pick one model. The plan lifecycle is outcome-driven (each phase's return TOON sets the next transition), so all labels are outcome / gate names.
- **Hiding the back-edges** off-screen or in a footnote. If the cycle structure is the diagram's main message, the back-edge needs prominent visual treatment, not a corner cameo.

## Reference implementation

`doc/resources/diagrams/phase-lifecycle.svg` — the canonical state diagram for plan-marshall's six-phase plan lifecycle. Linear forward flow `phase-1-init → phase-2-refine → … → phase-6-finalize` with a prominent curved back-edge from `phase-6-finalize` to `phase-5-execute` for the loop-back outcome. Review-gate names labelled on each forward edge.

Use it as the template for any sequential-with-back-edge lifecycle diagram.
