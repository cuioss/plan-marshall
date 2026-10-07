envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:01:22Z

component=plan-marshall:manage-metrics
category=improvement
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Reconcile the two token ledgers, or state what each counts one-of

## Context

Two on-disk ledgers report token spend over an **identically declared** population
and disagree by a factor of 2.09.

| Ledger | Declared population | Tokens |
|---|---|---:|
| `execution_log[]` (written by `manage-execution-manifest record-step`, summed by `check-routing-decisions`) | `5-execute,6-finalize` | 2,518,734 |
| `work/metrics-dispatch-boundaries-{phase}.toon` | `5-execute` (2,497,910) + `6-finalize` (2,761,584) | 5,259,494 |

Neither figure is mislabelled. `check-routing-decisions` is scrupulous about this —
its reference doc explains at length that `execution_log_tokens` is emitted under
that name and never as `actual_tokens`, precisely because "actual" is the one word a
reader accepts without checking its scope. The dispatch ledger is equally careful,
publishing its excluded dispatch classes by declaration.

And yet a consumer handed both has no way to choose, and nothing in the pipeline
compares them.

## Root cause

Honest per-figure labelling was treated as sufficient. It is necessary and it is not
sufficient: two figures can each carry a truthful population label, declare the
*same* population, and still contradict each other — because the label names the
phases, not the counting unit.

The direction is consistent with `execution_log` counting **steps** while the
boundary ledger counts **firings**. This run re-fired heavily —
`pre-submission-self-review` 8 times, `pre-push-quality-gate` 4,
`automatic-review` 3, `plugin-doctor` / `simplify` / `push` / `ci-verify` twice each —
which would inflate a per-firing ledger relative to a per-step one. That mechanism is
a hypothesis consistent with the direction and magnitude; it is not established here.

## Proposed action

Either:

- add an explicit **one-of** statement to each ledger's contract (`execution_log`
  counts one row per step; the boundary ledger counts one row per dispatch firing),
  so the disagreement becomes arithmetic rather than contradiction; or
- publish a reconciliation, so a consumer reading either figure is told what the
  other says.

The generalisable rule: when two artifacts declare the same population, the
population label alone does not make them comparable. State the counting unit, or
reconcile.

## Evidence

- aspect routing_decisions: `cost_preview.execution_log_tokens: 2518734`,
  `execution_log_population: 5-execute,6-finalize`
- aspect log_analysis: `dispatch_boundaries` — 10 rows (5-execute) + 17 rows (6-finalize)
- `status.metadata.phase_steps` `prior_firings[]` / `firing_count` for the re-firing counts
