envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:18:07Z

# Phase boundary inverted in metrics.toon while boundary_monotonicity reports zero violations

component: plan-marshall:manage-metrics
category: bug
confidence: high

## Context

The persisted `work/metrics.toon` for this plan records the `6-finalize` phase as:

- `start_time: 2026-09-19T14:00:01Z`
- `end_time: 2026-09-19T12:24:27Z`
- `duration_seconds: 80944.0`

The end precedes the start by 1h 35m 34s. The recorded `end_time` is byte-identical to `5-execute`'s `start_time`, and `6-finalize`'s `start_time` is byte-identical to `5-execute`'s `end_time` — the two phases' boundaries are crossed, not merely wrong.

Running `manage-metrics generate --plan-id ...` over this store returned `boundary_monotonicity[0]:` (empty), `any_phase_missing_end_time: false`, `phases_missing_end_time[0]:`. The guard whose whole job is to catch a non-monotonic boundary published an empty violation list over a store that holds one.

## Root cause

Not established from the retrospective's vantage point; two candidates are visible in the data.

First, the value itself: `5-execute` carries `close_count: 3` and is listed in `re_entered_phases`, and the plan looped back from `6-finalize` to `5-execute` once via `verification-feedback`. A re-entry that stamps the *incoming* phase's start onto the *outgoing* phase's end would produce exactly this crossed pair.

Second, the guard: `boundary_monotonicity` reported clean over a store containing the violation. Either it compares a different pair of fields than the two above, or it skips a phase whose `close_count`/`value_scope` marks it re-entered, or it does not run when `any_phase_missing_end_time` is false. Whichever it is, a monotonicity check that cannot fire on a 1h36m inversion is not measuring monotonicity.

A third field corroborates that nothing reconciles these: `duration_seconds: 80944.0` (22h29m) is not derivable from the recorded interval at all, which would be negative. Three fields describe the same phase and disagree pairwise, and no instrument says so.

## Proposed action

1. Make `boundary_monotonicity` derive its population from every phase block that carries **both** a `start_time` and an `end_time`, publish that population size beside the violation count, and assert `end_time >= start_time` per row. A zero violation count over an unpublished population is the failure mode here.
2. Add the cross-field consistency check the store currently lacks: when a phase carries `start_time`, `end_time` and `duration_seconds`, assert the three are mutually consistent (within the cumulative-close allowance that `value_scope` declares), and report the disagreement rather than silently keeping all three.
3. Audit the phase-transition write path for the crossed-stamp pattern, using the re-entry sequence on this plan as the reproduction case.

## Evidence

- artifact: `.plan/local/plans/truth-143-orchestrator-inbox-delivery-path/work/metrics.toon` — `[6-finalize]` block, `start_time` 14:00:01Z vs `end_time` 12:24:27Z
- command: `manage-metrics generate --plan-id truth-143-orchestrator-inbox-delivery-path` returned `boundary_monotonicity[0]:` and `any_phase_missing_end_time: false`
- corroboration: `[5-execute]` carries `close_count: 3`, `value_scope: mixed_cumulative_and_last_close`, and the exact reciprocal timestamps
- aspect: plan_efficiency — the inverted interval is what the phase_breakdown renders as `22h29m`
