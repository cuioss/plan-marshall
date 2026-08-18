# Diagram Type — Deployment / Topology

Covers deployment diagrams: what runs where, what it talks to, over which protocol and port, and
where trust changes. The structural unit is the **enclosure** — a box that contains other boxes —
rather than the column, the lifeline or the stage.

Reference implementation: none in this repository. No diagram of this type is authored here; the
specification and the skeleton template stand on their own.

This type layers on top of the shared visual language. Palette, typography, stroke widths, corner
radii, arrow-marker geometry and the 8-pixel grid are defined once in
[`visual-language.md`](visual-language.md) and are **not** restated here. Theme
handling follows [`theme-handling.md`](theme-handling.md); every diagram of this
type uses **Strategy A (theme-neutral)**, the single `#6e7681` token, because a deployment diagram
carries more strokes per unit area than any other type and the theme-aware variants diverge visibly
under dense nesting.

## When to use this type

Use a deployment diagram when the question the reader is asking is **where does this run, and what
can reach it**. Specifically:

- **Runtime topology** — hosts, networks, containers, processes and the links between them.
- **Cluster topology** — cluster, namespace, pod, container, and the services fronting them.
- **Trust geometry** — where an untrusted caller becomes a trusted one, and which component performs
  the change.
- **Deployment variants** — the same artifact deployed several times with different configuration,
  where the differences are what the reader needs.

Use a different diagram type when:

- The structure is **flow through stages** → use the flow type
  ([`diagram-type-flow.md`](diagram-type-flow.md)).
- The structure is a **time-ordered exchange** → use the sequence type
  ([`diagram-type-sequence.md`](diagram-type-sequence.md)).
- The structure is **producer / store / consumer** or a **side-by-side comparison** → use the block
  type ([`diagram-type-block.md`](diagram-type-block.md)).
- The structure is **layers stacked on a substrate** → use the stack type
  ([`diagram-type-stack.md`](diagram-type-stack.md)).
- The structure is **hub-and-spoke relationships without containment** → use the graph type
  ([`diagram-type-graph.md`](diagram-type-graph.md)).

The discriminator is containment. If nothing in the picture is *inside* anything else, this is the
wrong type.

## Layout grid

### Standard configurations

| Shape | viewBox | Use |
|-------|---------|-----|
| Single host | `0 0 1000 620` | One host or one network, three to six contained components. The default. |
| Multi-host | `0 0 1200 760` | Two or more peer hosts / networks, or a cluster with two namespaces. |
| Wide strip | `0 0 1200 520` | A single network with many peer containers and shallow nesting. |
| Dense stack | `0 0 1200 900` | One network carrying eight or more components at full nesting depth. The tallest shape; reach for a second diagram before reaching past it. |

Positions and sizes snap to multiples of 8, per the shared grid rule.

| Spacing | Value | Notes |
|---------|-------|-------|
| Outer margin (`viewBox` edge → outermost enclosure) | 24 px | Larger than the shared 20 px minimum: the outermost element here is itself a bordered box, so it needs visible air around its stroke. |
| Gutter between sibling enclosures | 32 px | Horizontal or vertical. Cross-container edges run in these gutters. |
| Gutter between sibling leaf boxes inside one enclosure | 24 px | |
| Legend block inset | 24 px from the bottom-left `viewBox` corner | Only when the numbered-leg convention is in use. |

### Containment nesting

Enclosures nest. The canonical ladders are:

```text
host ─▶ network ─▶ container                    (compose / plain-runtime form)
cluster ─▶ namespace ─▶ pod ─▶ container        (orchestrated form)
```

| Rule | Value |
|------|-------|
| Maximum nesting depth | **4 boxes**, counting the outermost enclosure as depth 1. |
| Inset — child box edge to parent box inner edge | **At least 16 px** on every side, at every level — a floor, not a target. A larger clearance is not a defect. |
| Label band — reserved strip at the top of every enclosure | **28 px** for a label-only enclosure, **44 px** when the enclosure carries an `encl-sub` sub-label. No child box may start above `parent_top +` the effective band. |
| Minimum legible inner box | **120 × 48 px**. |

Corner radius steps down as the enclosure role gets more concrete, so nested corners read as
concentric rather than parallel. The radius is keyed to the **role**, not to the raw depth number,
because the two canonical ladders put different roles at the same depth — the compose ladder has a
container at depth 3 where the orchestrated ladder has a pod:

| Enclosure role | `rx` / `ry` |
|----------------|-------------|
| Outermost enclosure — host, cluster | 8 |
| Network, namespace | 6 |
| Nested workload roles — pod, container group, container, process | 4 |

A leaf container therefore takes `rx="4"` whatever its depth: depth 3 in the compose ladder, depth 4
in the orchestrated one. The innermost tier is flat at 4 rather than continuing to decrease because
4 px is the smallest radius that still reads as a rounded corner at raster scale — a pod at 4 and its
contained container at 4 are the one place two nested corners share a radius, and the 16 px inset
keeps them from reading as parallel.

Depth 4 is the nesting floor, and the reason is legibility rather than geometry. Space is not the
constraint: in the smallest `viewBox` (`0 0 1000 620`) a depth-5 box still has roughly 820 × 330 px
after the 24 px outer margin, four 16 px insets and four 44 px label bands, so it clears the
120 × 48 px minimum with room to spare. What runs out is the reader's ability to track containment
and the radius ladder that signals it: the ladder has only three steps (8 / 6 / 4), so depth 4
already shares its radius with depth 3's leaves, and a fifth level would carry no distinguishing
radius at all — five nested strokes in one neutral colour read as a pattern rather than a hierarchy.
**When the topology needs a fifth level, split it into a second diagram** rather than shrinking the
type or the inset.

The 120 × 48 px minimum is what a box needs to hold a 13 px label plus one 11 px sub-label with the
standard 12 px left inset and the 44 px label band that a sub-label requires. **A box that would
fall below the minimum is not drawn smaller — it is collapsed**: replace the group of undersized
boxes with one box carrying a count and an annotation naming what was collapsed (see § Collapsed
groups).

### Enclosure labels

Enclosure labels sit **top-left inside the box**, never centered. Centering a container label puts
it directly above the first nested child, where the two collide as soon as the child is added.

```svg
<rect class="stroke" x="40" y="72" width="920" height="480" rx="8"/>
<text x="52" y="96" class="encl">host</text>
<text x="52" y="112" class="encl-sub">docker bridge network</text>
```

| Element | Class | Position | Type |
|---------|-------|----------|------|
| Enclosure label | `encl` | `x = box_left + 12`, baseline `y = box_top + 24` | sans 13 px / 600, upright |
| Enclosure sub-label (optional, one line) | `encl-sub` | same `x`, baseline `y = box_top + 40` | sans 11 px, italic |

An enclosure carrying a sub-label uses a **44 px** label band instead of 28 px.

Leaf-component labels — the innermost boxes that represent an actual running thing — follow the same
top-left rule, so a reader's eye tracks a single left edge down the whole nest.

## Content positioning

### First-party versus external components

A deployment diagram almost always mixes components the reader's team owns with components it merely
talks to. The distinction is carried by a **left-edge accent bar**, not by hue:

```svg
<!-- first-party component -->
<rect class="stroke" x="96" y="160" width="240" height="120" rx="4"/>
<line class="own-bar" x1="96" y1="168" x2="96" y2="272"/>

<!-- external component: same box, no bar -->
<rect class="stroke" x="400" y="160" width="240" height="120" rx="4"/>
```

`.own-bar` is a 3 px stroke in the same token, drawn on the box's left face and inset 8 px from each
corner so it does not fight the corner radius. First-party boxes carry it; external boxes do not.

The bar is deliberately **not** a border-weight change: a heavier border would collide with the
trust-boundary language below, which owns stroke weight. It is deliberately not a fill: fills are
reserved for activation-style translucency and would darken a nested box past legibility.

When a diagram is entirely first-party or entirely external, omit the bar everywhere — a distinction
drawn against nothing is noise. State the fact in the `<desc>` instead.

### Mounted material

Certificates, configuration files and secrets are **material**, not components. They do not run,
they do not receive traffic, and they must not be drawn as another box in the nest — a box implies a
peer, and an arrow into it implies a flow.

Mounted material is drawn as a **tag pill attached to the consuming box's bottom edge**:

```svg
<line class="mount-stem" x1="140" y1="280" x2="140" y2="292"/>
<rect class="stroke" x="96" y="292" width="128" height="18" rx="4"/>
<text x="104" y="305" class="mount">certificates/</text>
```

| Element | Class | Geometry |
|---------|-------|----------|
| Stem | `mount-stem` | 1.0 px, `stroke-dasharray: 2 2`, 12 px long, vertical, from the box's bottom edge |
| Pill | `stroke` | height 18, `rx="4"`, width = label width + 16 |
| Label | `mount` | mono 10 px, upright, `x = pill_left + 8`, baseline `y = pill_top + 13` |

The stem is deliberately heavier than the 0.6 px `3 3` divider dash. A 12 px run of 0.6 px dashes
is effectively invisible in the rasterised light-background render — it survives inspection of the
markup and disappears on the PNG, which is exactly the defect class the mandatory read-back exists to
catch. 1.0 px with a `2 2` pattern stays visibly dashed at raster scale while remaining obviously
lighter than the 1.5 px arrow stroke.

Rules:

- **No arrow marker on a mount stem.** A mount is inert material present at start-up, not traffic.
  The dashed stem with no arrowhead is the whole point of the notation.
- Multiple mounts stack **horizontally** along the bottom edge with 8 px between pills, left-aligned
  with the consuming box.
- When the pills exceed the consuming box's width, wrap to a second row 22 px lower. Three rows is
  the practical limit; past that, collapse to one pill carrying the mount root.
- A mount pill's label is the **mount path as written in the deployment source**, in monospace,
  trailing slash retained for directories.

### Collapsed groups

When several components are structurally identical and differ only in configuration, drawing each in
full buries the affordances the diagram exists to show. Collapse them:

```svg
<rect class="stroke" x="640" y="160" width="264" height="120" rx="4"/>
<line class="own-bar" x1="640" y1="168" x2="640" y2="272"/>
<text x="652" y="184" class="encl">variant instances (4)</text>
<text x="652" y="202" class="encl-sub">same image, overlaid configuration</text>
```

- The count goes in the label, in parentheses. A collapsed group without a count is an omission.
- One `encl-sub` line names **what varies**, so the reader knows what the collapse hid.
- The members are enumerated in the `<desc>` element, always. The raster hides them; assistive tech
  and full-text search must not.
- A collapsed group is a **legibility choice, and it is falsifiable**: if the rendered result shows
  the collapse hiding an affordance the diagram is meant to demonstrate, add a second diagram rather
  than expanding the group back into the first.

## Arrows and labels

### Protocol and port edge labels

Every edge between components carries what protocol runs over it and, where the port is meaningful,
which port it lands on.

**Format:** `PROTOCOL :port` — protocol in upper case, single space, colon immediately followed by
the port number with no intervening space.

```text
HTTPS :8443      HTTP :80      gRPC :9000      TCP :5432      WS :8443
mTLS :8444       mTLS          HTTPS
```

- Omit `:port` when the port carries no information for the reader — an in-process call, an L4 relay
  leg that inherits its listener's port, or a leg whose port is an implementation detail.
- `mTLS` is written as a protocol in its own right when mutual authentication is the fact the reader
  needs; otherwise write `HTTPS` and record the client-certificate requirement in the `<desc>`.
- Never abbreviate to a bare port number. `:8443` alone tells the reader nothing about the wire.

**Type and placement.** Edge labels are **monospace 11 px, upright** (class `edge-lbl`) — they are
identifiers, and the shared typography rule puts identifiers in monospace. This also separates them
at a glance from prose annotations, which stay sans-serif italic.

| Edge orientation | Label placement |
|------------------|-----------------|
| Horizontal | Centered on the edge, baseline 8 px above the line, `text-anchor: middle` |
| Vertical | 8 px to the right of the line at its midpoint, `text-anchor: start` |
| Orthogonal (multi-segment) | On the **longest** segment of the run, using that segment's rule |

**Crowded diagrams.** When two edge labels would come within 14 px of each other:

1. Move the second label to the **opposite side** of its own edge — below a horizontal edge, left of
   a vertical one. Never shrink the type; 11 px monospace is the floor at which the rasterised
   result stays legible on both backgrounds.
2. If that is still not enough — three or more edges sharing one corridor — switch that corridor to
   the **numbered-leg convention**: replace each label with a leg number in a 9 px-radius open circle
   at the edge midpoint, monospace 10 px centered, and put the expansion in a legend block at the
   bottom-left of the diagram. Number legs in reading order, top-to-bottom then left-to-right.
3. Use the numbered-leg convention for **the whole corridor or none of it**. Mixing inline labels and
   leg numbers in one corridor is worse than either.

**Cross-container edges.** An edge whose endpoints sit in different enclosures:

- is drawn **orthogonally** — horizontal and vertical segments only, no diagonals;
- **exits its source box through the nearest face**, and enters its target the same way, so the
  reader can see which boundary was crossed;
- carries its label in the **widest gutter segment** of its run, never inside an enclosure box where
  it would read as belonging to that enclosure's contents;
- switches to the numbered-leg convention when no gutter segment on its run is at least 90 px long.

### Trust boundaries

A trust boundary is where an untrusted caller becomes a trusted one. It must be distinguishable from
ordinary containment **at a glance in the rendered raster**, not merely on inspection of the markup.
The palette is a single neutral token and decorative colour is forbidden, so the distinction is
carried by stroke pattern, stroke weight, and a crossing glyph.

| Element | Class | Style |
|---------|-------|-------|
| Containment border | `stroke` | solid, 1.2 px |
| **Trust boundary** | `trust` | **dashed `8 4`, 2.0 px** |
| Trust-boundary label | `trust-lbl` | sans 11 px / 600, **upright** |
| Trust crossing glyph | `trust-cross` | open circle, `r="3.5"`, 1.2 px, `fill="none"` |

```svg
<rect class="trust" x="72" y="120" width="560" height="380" rx="8"/>
<text x="84" y="112" class="trust-lbl">trust boundary — authenticated</text>
<circle class="trust-cross" cx="632" cy="220" r="3.5"/>
```

Rules:

- The dash pattern `8 4` at 2.0 px is deliberately far from the `3 3` at 0.6 px used for dividers and
  mount stems. The two must never be confusable at raster scale.
- The trust-boundary label sits **outside** the boundary, 8 px above its top-left corner, and is
  **upright** — every other 11 px annotation in the visual language is italic, so upright weight-600
  reads as a different class of statement.
- **Every arrow that crosses a trust boundary carries a `trust-cross` glyph at the intersection
  point.** This is the affordance that makes the boundary readable even when the boundary line itself
  is partly occluded by nested content. An arrow crossing two boundaries carries two glyphs.
- A trust boundary may cut **across** containment — it is not required to align with any enclosure
  edge, and the interesting cases are exactly the ones where it does not. When a boundary cuts
  through the middle of an enclosure, draw it as an open path rather than a closed rect, and label
  both sides.
- Name what changes, not the mechanism: `trust boundary — authenticated`, not `trust boundary — JWT`.

## Naming and file conventions

| Element | Convention |
|---------|-----------|
| File name | `kebab-case.svg` naming the topology depicted. Suffix `-topology` when the diagram's subject is the topology itself (`{subject}-topology.svg`). |
| Location | `doc/resources/diagrams/`, flat. |
| `<title>` | One sentence naming **which** topology, including its environment. A deployment diagram that does not say which environment it depicts will be mistaken for a production recommendation. |
| `<desc>` | One paragraph. Must enumerate the members of every collapsed group and name every trust boundary. |
| Theme strategy | Strategy A (theme-neutral), recorded in the top-of-file comment. |

## Render verification

The shared Step 4 render check ([`../SKILL.md`](../SKILL.md) § Step 4) is mandatory and
blocking for this type as for every other: rasterise against both GitHub backgrounds and **read the
resulting PNGs back**. Deployment diagrams carry the highest stroke density of any type, so the
clipping, collision and legibility items on that checklist fail here more often than anywhere else.

When no rasteriser is installed on the host, run one in a container. No host package, project
dependency or CI step is required:

```bash
docker run --rm -v "/abs/path/to/repo:/w" -v "/abs/path/to/scratch:/out" -w /w alpine:3.20 sh -c \
  "apk add --no-cache rsvg-convert font-dejavu font-liberation && \
   rsvg-convert -b '#ffffff' -w 1200 -o /out/diagram-light.png doc/resources/diagrams/NAME.svg && \
   rsvg-convert -b '#0d1117' -w 1200 -o /out/diagram-dark.png  doc/resources/diagrams/NAME.svg"
```

Two details in that invocation are load-bearing and are the two ways this recipe is most often got
wrong:

1. **The package is `rsvg-convert`, not `librsvg`.** On Alpine the `librsvg` package ships only the
   shared library; the CLI lives in its own package. `apk add librsvg` succeeds and the subsequent
   `rsvg-convert` call then fails with `sh: rsvg-convert: not found`.
2. **The font packages are not optional.** A bare container has no fonts. `rsvg-convert` still exits
   0 and still writes a structurally valid PNG, but every glyph rasterises as a tofu box — and the
   wider tofu glyphs overflow the `viewBox`, which reads as a clipping defect that is not there.
   Without fonts the legibility, clipping and font-fallback items on the checklist cannot be
   evaluated at all, while the command reports success.

Verification runs **locally**. A rendered PNG is a verification artifact, not a deliverable: write it
under a scratch directory and do not commit it.

## Annotated template

The skeleton template at [`../templates/deployment-diagram-skeleton.svg`](../templates/deployment-diagram-skeleton.svg) carries the
canonical `<style>` block, the `arrow` marker, the theme-neutral token, and placeholder content laid
out on this type's geometry. Copy it, rename it, and replace the placeholders.

Every affordance specified above has a worked placeholder in the skeleton, so copy-rename-fill is the
whole workflow — an author does not need to read this document to produce a structurally valid
diagram:

| Affordance | Placeholder in the skeleton |
|------------|-----------------------------|
| Containment nesting | `host` (depth 1, `rx="8"`, 44 px label band) containing `network` (depth 2, `rx="6"`, 28 px band) containing the components (depth 3, `rx="4"`), at or above the standard 16 px inset |
| Enclosure labels | Top-left on every box, with one optional `encl-sub` line |
| Trust boundary | Dashed `8 4` at 2.0 px running the full height of the network, with its upright weight-600 label above the top of the line |
| Trust crossings | Two `trust-cross` glyphs, one on each edge that crosses the boundary |
| Protocol + port edge labels | `HTTPS :8443` and `gRPC :9000` on single-segment edges, `TCP :5432` on an orthogonal cross-container edge, labelled on its longest segment |
| First-party vs external | Three boxes carry the `own-bar` left accent; the external component is the same box without it |
| Mounted material | Two pills on dashed stems under the first-party component, `certificates/` and `config/` |
| Collapsed group | `variant instances (N)` with the count in the label and the varying dimension in the sub-label |

Placeholders the author does not need are **deleted, not left in place**. A skeleton affordance that
survives into a real diagram unedited is worse than an absent one: it reads as a claim about the
topology.

The skeleton lives under `templates/` rather than `diagrams/` because `asciidoc-embedding.md`
requires `diagrams/` to remain a flat catalogue of actual diagrams, and a skeleton is not a diagram.
