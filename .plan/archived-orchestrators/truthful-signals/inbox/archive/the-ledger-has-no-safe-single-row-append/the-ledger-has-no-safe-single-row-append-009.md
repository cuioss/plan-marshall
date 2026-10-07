envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:21Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high

# Derive re-entry coverage from dispatch rows, not from the markers it checks

## Context

The RE_ENTRY_COVERAGE rule clusters `[STATUS] (plan-marshall:phase-5-execute) {Starting, Re-entering} execute phase` lines with a 30-second gap threshold, then expects one `Re-entering` line per cluster after the first. On this plan it reported `inferred_dispatches: 2`, `starting_markers: 1`, `re_entering_markers: 1` - a clean pass.

The phase was actually entered three times. Two independent sources say so:

1. `work.log` carries two `[MANAGE-STATUS] Phase: 6-finalize -> 5-execute` transitions (2026-09-06T07:40:16Z and 2026-09-07T03:31:44Z) in addition to the original entry.
2. `work/metrics-dispatch-boundaries-5-execute.toon` carries six rows: three `voluntary_checkpoint` and three `clean_exit_queue_empty` - three dispatch pairs.

Only two entry markers were emitted. The 2026-09-07 re-entry emitted none, and is therefore invisible to a detector whose population is built from those markers.

## Root cause

The check's population is derived from the very lines whose absence it exists to detect. A missing marker removes a cluster rather than creating a gap, so the arithmetic stays self-consistent and the check reports clean. This is the set-guarding-detector archetype: a detector that can return zero from a population it derived from the thing it is checking.

## Proposed action

Derive the expected entry count from a source independent of the markers - the `[MANAGE-STATUS] Phase: X -> 5-execute` transitions, or the dispatch-boundary row pairs - and compare the marker count against THAT. Publish both numbers so the population is visible, per the standing rule that a set-guarding detector must publish the size of the population it evaluated.

## Evidence

- fragment-log-analysis.toon `phase5_logging_gaps.dispatch_clustering`: `inferred_dispatches: 2`, `starting_markers: 1`, `re_entering_markers: 1` - reported clean.
- work.log lines carrying `[MANAGE-STATUS] Phase: 6-finalize -> 5-execute` at 2026-09-06T07:40:16Z and 2026-09-07T03:31:44Z.
- work.log 2026-09-06T07:44:33Z carries `Re-entering execute phase - 3 tasks pending`; no corresponding line exists after the 2026-09-07T03:31:44Z transition.
- work/metrics-dispatch-boundaries-5-execute.toon: 6 rows = 3 voluntary_checkpoint + 3 clean_exit_queue_empty.
