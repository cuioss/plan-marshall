envelope_version=1
sender_type=plan
sender_id=fold-pm-code-intelligence-into-core
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-25T21:12:59Z

# Three separate count claims in one run were asserted and each was wrong

## Context

This plan was, in substance, a counting exercise: retiring one of eleven bundles and correcting every count claim that named the old total. Three separate count assertions made *during* the run were themselves wrong, and each was caught only because something independently re-derived it:

1. `CLAUDE.md` claimed 153 skills; the re-derivation against the post-deletion tree found 154. The outline had already anticipated this, requiring the component counts be "re-derived against the post-deletion tree, not decremented by guess".
2. The clarified request said "eight surfaces" and then enumerated nine. The outline caught it ("The D4 count is wrong, the enumeration is right"), but the operator gate that widened D4 then restated the same wrong figure — "Should D4 widen to cover all 8 surfaces" — so the miscount survived into the decision record even after being identified.
3. `phase-5-execute` claimed the deleted manifest had an empty `skills[]`; it had one entry.

## Root cause

In each case a count was carried forward from prose rather than derived from the population it describes. The second instance is the instructive one: the miscount was explicitly identified in the outline and *still* propagated into the gate question, because the gate was authored from the narrative rather than from the enumeration the outline had just derived.

## Proposed action

Where a gate question or a document states a set size, derive it at authoring time from the enumeration it summarizes rather than restating a figure from upstream prose — and prefer stating the enumeration instead of its cardinality when the list is short enough to name. This is the same discipline the outline's own "Coverage derivation" section applies (a union of three independent sweeps, with a stated closure argument) and it worked: the derived surface set was right where the narrative count was wrong.

## Evidence

- aspect: chat_history_analysis — the widening gate at turn_index 4 asserts "all 8 surfaces"; D4 + D5 close over nine
- solution_outline.md § Discovery findings: "The D4 count is wrong, the enumeration is right ... The enumeration is authoritative; the label was a miscount of a list the operator fully wrote out"
- solution_outline.md § Coverage derivation — the sweep-union method that produced the correct set
- aspect: request_result_alignment — the declared 22-file surface also under-recorded the realized footprint by one real source file
