envelope_version=1
sender_type=plan
sender_id=prompt-standard-and-doctor-rule
epic=operator-ux
kind=candidate-lesson
created=2026-09-02T13:41:26Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=prompt-standard-and-doctor-rule
recurrence_of=none

# RE_ENTRY_COVERAGE precondition is coupled to the very signal it polices

## Context

`references/logging-gap-analysis.md` defines the RE_ENTRY_COVERAGE rule to detect a phase-5 dispatch cluster that re-entered without emitting a `[STATUS] ... Re-entering execute phase` marker. Its stated precondition is:

> **Precondition**: at least one `[STATUS] (plan-marshall:phase-5-execute) Re-entering execute phase` entry exists in `work.log`. ... Plans without any `Re-entering` line skip this rule entirely.

This plan re-entered `5-execute` and emitted **zero** `Re-entering` markers, so the rule skipped and the retrospective would otherwise have reported nothing.

The re-entry is independently established from two sources that do not depend on the marker:

- `work/metrics.toon` records `close_count: 2` for `5-execute`, with `value_scope: mixed_cumulative_and_last_close` and `5-execute` listed under `re_entered_phases`.
- Decision `35b0d6` (2026-09-01T22:12:35Z): *"Orchestrator-tier yield: verify:coverage live-resolves to execution_tier=orchestrator with bash_timeout_seconds=881 and exceeds_bash_ceiling=true after an inline attempt was killed at 388s ... Returning for the orchestrator to run coverage via await-long-running."* The leaf correctly refused, returned, and execution resumed afterwards.

`analyze-logs` observed `starting_markers: 1`, `re_entering_markers: 0`, `inferred_dispatches: 1`.

## Root cause

The precondition tests for the presence of the same marker whose absence is the defect. A phase that re-entered and emitted **no** marker is therefore exactly the case the guard suppresses; the rule can only ever fire on a plan that emits *some* markers and misses one. A total-absence regression — the more serious failure — is structurally undetectable.

This is the same shape the surrounding aspect documentation warns about elsewhere: a check that cannot fire is not a clean check.

## Proposed action

Key the precondition on a signal independent of the marker channel. Both are already available offline:

- `work/metrics.toon` `close_count > 1` for the phase (authoritative — written at the write site), or its `re_entered_phases` list;
- `manage-metrics reconcile-ledgers`, which already emits a `phase_re_entered` finding for exactly this condition.

Then: `close_count - 1` is the expected `Re-entering` count, and `0` observed against `1` expected is a finding rather than a skip. Precondition-guarding on a *different* channel keeps the original intent (do not false-positive on plans predating the marker) without disabling the total-absence case — those plans have no `metrics.toon` `close_count` either, or a `close_count` of 1.

## Evidence

- aspect: logging_gap_analysis — `RE_ENTRY_COVERAGE, precondition_unmet, 0`
- aspect: log_analysis — `dispatch_clustering: starting_markers 1, re_entering_markers 0, inferred_dispatches 1`
- `work/metrics.toon` — `[5-execute] close_count: 2`; top-level `re_entered_phases: 5-execute`
- decision `35b0d6` — the orchestrator-tier `verify:coverage` yield that caused the re-entry
- `reconcile-ledgers` — `phase_re_entered` finding on `5-execute`
