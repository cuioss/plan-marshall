# Visual QA for hand-authored SVG

The SVG verification surface the skill's Step 4 checklist alone does not cover. The Step 4 list catches gross failures — illegible text, clipping at the viewBox edge, missing arrow markers, broken font fallback. The defects this standard catches are subtler: text that fits the page but not its container, intra-diagram drift in stylistic choices, curves whose geometry was set by accident, label collisions that the eye notices but the markup does not flag. Most are correctness-by-eye problems; the SVG parses, the renderer succeeds, and the diagram still ships a glitch.

Visual QA is therefore a distinct discipline from "the SVG renders." A new or modified diagram passes only when *both* the Step 4 checklist and the expanded checklist below succeed on both themes.

## Expanded checklist

Every item below must be visually confirmed against the rasterised PNGs (light and dark backgrounds), not against the SVG source. Each item names a defect class the Step 4 list does not catch.

- **Text fits within its container.** Every text run that lives inside a box, slab, or labelled region stays inside that container's bounding rect. Long monospace identifiers, multi-line labels, and titles set in larger sizes are the usual culprits. Step 4 catches clipping at the *viewBox* edge; this item catches clipping at any *internal* box edge.
- **Intra-diagram stylistic consistency.** A stylistic choice that applies to one element of a kind in a diagram applies to every element of that kind in the same diagram. If three of four "stage" boxes are filled with the neutral tint and the fourth is empty, the fourth is a defect — not a deliberate variation. Stroke weight, marker style, corner radius, fill convention, label position relative to the connector: all must be uniform per element class within a single diagram.
- **Curve smoothness.** Bézier paths and arcs read as intentional curves, not as artefacts of misplaced control points. A loop should look like an arc a designer chose; a Y-junction should look like a junction. If a curve has a visible kink, an asymmetric belly, or a control-point bulge that does not serve the geometry, the path needs to be rewritten.
- **Cross-diagram parity.** Two diagrams in the same corpus depicting the same kind of element use the same conventions for that element. A "consumer" node in one diagram and a "consumer" node in another should be the same shape, same fill, same label position. Spot-check by opening two related rendered PNGs side by side.
- **Label collisions.** No label visually collides with the line, marker, or other label it relates to. Stricter than Step 4's "captions don't collide": this applies to *every* label in the diagram — connector labels, stage labels, sub-labels under a primitive — not just captions at the bottom.
- **Connector endpoint discipline.** A connector terminates either at the centre of an arrow marker, flush with a container edge, or at a defined anchor point — never mid-stroke in whitespace. Same for the start of a connector: it begins at a defined edge or anchor, not adrift in a column.
- **The smell test.** After the checklist passes, pause and ask: *"Does any element here read as accidental?"* Examples of accidental: a stage box larger than its peers without semantic reason; an arrowhead misaligned by a few pixels; a connector that starts mid-stroke at one end but flush at the other; a curve that looks like the author gave up partway through. If the smell test triggers anywhere, return to the checklist with that area in mind.

## Repair workflow

When the checklist surfaces a defect:

1. Fix the defect in the SVG source.
2. Re-rasterise both themes (the Step 4 commands).
3. Re-read both PNGs (the `Read` tool, both files).
4. Re-walk the full checklist (Step 4 + this standard).

Repeat until both renderings pass clean. Never approve a fix from the SVG source alone — coordinate arithmetic in `path` and `transform` attributes is too easy to get wrong without seeing the result.

## Common defect classes

A short catalogue of patterns this QA pass has caught historically. The list is not exhaustive; new patterns are added when they are encountered more than once.

- **Empty-vs-filled inconsistency.** Half the boxes of a kind are filled, half are not. Almost always the empty ones are wrong (a fill attribute was forgotten when the box was copied). Fix by aligning to the filled convention.
- **Text overflow inside a container.** A box was sized for short labels; a longer label was substituted later without resizing. Fix by widening the box (and, if needed, the column) — never by shortening the label below clarity.
- **Awkward loop arc.** A return-to-start connector was drawn with a single Bézier whose control points are far enough apart that the curve reads as wobbly. Fix by either tightening the control points or splitting the loop into two arcs joined at a midpoint.
- **Mid-stroke connector start.** A connector visibly starts a few pixels inside the source box rather than at its edge. Usually a forgotten coordinate update after the box was repositioned. Fix by snapping the connector endpoint to the container's edge.
- **Misaligned arrowhead.** The arrow marker is rotated correctly but the path it terminates is off-axis from where the eye expects. Fix by recomputing the path's final segment so it ends square to the target.
- **Inconsistent label position.** Most labels above their connector, one below — or most labels left-aligned to their node, one centred. Fix by aligning to the majority convention.
- **Stylistic surface bleed.** A diagram-type-specific convention (e.g., dashed dividers from a `stack` diagram) appears in a diagram of a different type without justification. Fix by removing the surface bleed.

## Pre-commit gate

The QA pass is non-skippable for any diagram about to be committed or referenced from a documentation page. This includes:

- New diagrams.
- Existing diagrams modified in any way — content edits, layout changes, single-text adjustments. Even a one-word label change triggers a fresh rasterise + re-read of the affected diagram.
- Diagrams indirectly affected — when a stylistic choice in one diagram (e.g., a node shape, a stroke weight) is updated, every other diagram in the corpus that depicts the same element class is re-checked for parity.

When the gate triggers a repair on a diagram outside the immediate scope of a change, the repair lands in the same commit. A corpus is either consistent or it is not; lingering parity drift is itself a defect class.
