envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:30Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Fix the dispatch-boundaries section and the skipped-aspect drop

## Context

Two section-rendering defects surfaced in this run's compiled report.

1. `Phase Dispatch Boundaries` was omitted although its data was present. The log-analysis fragment carried `dispatch_boundaries` with `present: true` for 4-plan, 5-execute and 6-finalize. `compile-report` gates that section on a TOP-LEVEL bundle key `dispatch_boundaries` (`fragments.get('dispatch_boundaries')`), but `load_fragments` keys the bundle by aspect name, and row 17 of the aspect table is explicitly "injected, never dispatched — no `collect-fragments add` command is issued for this key". Nothing lifts the nested block to the top level, so the section is structurally unreachable: the per-phase termination-cause table can never render.

2. `Permission Prompt Analysis` landed in `sections_dropped` (the loud half) rather than `sections_omitted` (the benign half). The aspect is declared Claude-only and this run is OpenCode, so a `status: skipped` fragment was registered to keep the skip visible. `compile-report`'s non-emit branch only special-cases `chat-history-analysis` for a skipped-status fragment carrying findings; every other aspect with `status: skipped` plus payload is classified as a DROP and the run returns `status: warning`. A legitimate platform skip therefore reports as content loss.

Neither defect loses data today — the boundary facts are still visible in the Log Analysis JSON dump, and the permission skip is reported — but both mis-signal: one hides a section that exists, the other raises an alarm for a skip that was by design.

## Root cause

The injection contract for `dispatch_boundaries` names a bundle key that no producer writes, and the skipped-fragment carve-out was added for one aspect instead of for the status itself.

## Proposed action

For (1), lift the nested block in `load_fragments` (or in `collect-fragments finalize`) into a synthetic top-level `dispatch_boundaries` key when the log-analysis fragment carries one, so the renderer's existing gate finds it. For (2), widen the pre-status-guard branch from `trigger_key == 'chat-history-analysis'` to any fragment whose `status == 'skipped'` and which carries a findings list, so a declared skip renders (or is classified omitted) instead of dropped.

## Evidence

- aspect: logging_gap_analysis / log-analysis — `dispatch_boundaries` present with `present: true` for three phases.
- compile-report return: `sections_omitted` contains `Phase Dispatch Boundaries`; `sections_dropped` contains `Permission Prompt Analysis`; `status: warning`, message "Dropped non-empty sections from the compiled report: Permission Prompt Analysis".
- compile-report.py `load_fragments` (bundle keyed by aspect name) vs `_section_should_emit` (`fragments.get('dispatch_boundaries')`) and the `chat-history-analysis`-only skipped-status branch.
