envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:25:11Z

component=plan-marshall:phase-3-outline
category=improvement
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# Give a sweep deliverable a declaration form its execution can actually satisfy

## Context

Deliverables 7 (migrate hand-rolled sys.path preambles onto the shared loader) and 8 (convert non-enabled-rule suppressions, close the gate with RUF100) are tree-wide SWEEPS. Both declared their mutation scope as an enumerated outline-time snapshot of the tree. Execution reached 300 files beyond that snapshot: the realized footprint is 521 paths against 221 declared-and-hit, so 57% of what shipped sits outside every deliverable's declared surface.

## Root cause

The outline offers only a path list. A sweep's real scope is a PREDICATE ("every test module carrying a hand-rolled sys.path preamble"), and the set that predicate selects moves between outline time and execute time. Enumerating it produces a declaration that is wrong the moment anything else lands, and the retrospective then reads the difference as scope creep even though no unplanned work occurred.

## Proposed action

Add a predicate-shaped mutation-scope form to the deliverable schema — a glob or a named detector plus the command that enumerates it — so a sweep declares the rule rather than a snapshot of its output. The coverage comparison then re-evaluates the predicate against the realized footprint instead of differencing two lists taken at different times.

## Evidence

- aspect: request_result_alignment — scope_creep 300 files, far above the <5-file acceptable band; recall on declared modification-intent files is 99.1%, so the drift is entirely in the other direction
- aspect: artifact_consistency — references_only[300], affected_files_exact_match status warn
- aspect: outline_vs_shipped — touched_but_unassessed 521 of 521 realized_footprint_paths
- Downstream consequence: the 515-file diff is exactly what both size-capped review bots then refused, so the declaration style and the lost review coverage are causally linked on this plan
