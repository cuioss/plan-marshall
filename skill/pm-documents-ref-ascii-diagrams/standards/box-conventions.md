# ASCII Box-Diagram Conventions

Authoring conventions for ASCII / monospace box diagrams in skill and doc
source. These conventions are what the `ascii_diagrams` validator's `check` /
`fix` modes enforce.

## Box-drawing character set

Use exactly this set — do not substitute ASCII `+ - |`, and do not mix
single-line glyphs with heavy or double-line variants:

| Glyph | Name | Role |
|-------|------|------|
| `┌` | top-left corner | start of the top rule |
| `┐` | top-right corner | end of the top rule |
| `└` | bottom-left corner | start of the bottom rule |
| `┘` | bottom-right corner | end of the bottom rule |
| `─` | horizontal | fills the top and bottom rules |
| `│` | vertical | left and right border of every interior line |

## Box structure

A box is a run of lines, all at the same indent:

- a **top rule** `┌─…─┐`,
- one or more **interior lines** `│ … │`,
- a **bottom rule** `└─…─┘`.

```text
┌─────────────┐
│ producer    │
│ store       │
│ consumer    │
└─────────────┘
```

A blank line breaks a box run. A same-indent line that is neither an interior
line nor the bottom rule terminates the run (it is not a well-formed box).

## The alignment rule

Every line of a box MUST be the same total width, so the right borders all sit
in the same column. The inner width is the maximum, over the box's own lines, of
the span between the left and right borders. The top and bottom rules span that
same inner width.

Misaligned — the right borders are ragged because the interior was hand-padded
inconsistently and the rules are too short:

```text
┌────┐
│ short │
│ a longer line │
└────┘
```

Aligned — every right border lands in the same column and the rules match the
widest interior line:

```text
┌───────────────┐
│ short         │
│ a longer line │
└───────────────┘
```

Author the content first, then run `fix` to re-pad rather than counting columns
by hand.

## Legends, flow-lines, and nested boxes

ASCII-box detection is heuristic. The validator deliberately leaves three
patterns alone — author them as described so they are not mistaken for
misaligned boxes.

### Flow-lines

A bare `│` connector that is NOT `│`-bounded on both sides is a flow-line, not a
box interior line. It is left verbatim:

```text
┌──────────┐
│ phase 1  │
└──────────┘
     │
     ▼
┌──────────┐
│ phase 2  │
└──────────┘
```

The single `│` between the two boxes is a connector, not box content — it has no
closing `│`, so the validator does not treat it as an interior line.

### Nested boxes

A box drawn inside another box (at a deeper indent) is interior content of the
enclosing box, not a separately re-ruled box. The enclosing box's borders are
aligned to its own widest line; the nested box's lines are preserved verbatim:

```text
┌────────────────────┐
│ outer               │
│   ┌────────────┐    │
│   │ inner      │    │
│   └────────────┘    │
└────────────────────┘
```

### Legends

A short legend block (prose or a legend mini-box) placed inside the same
code/literal block but not part of the diagram's box run is left verbatim.
Separate it from the diagram with a blank line so the box run ends cleanly
before the legend begins.

## Where boxes are validated

The validator scans only inside code/literal blocks:

- `.md` files — fenced (` ``` `) blocks.
- `.adoc` files — both fenced (` ``` `) blocks and literal (`----`) blocks.

A box in running prose (outside any block) is neither validated nor repaired.
