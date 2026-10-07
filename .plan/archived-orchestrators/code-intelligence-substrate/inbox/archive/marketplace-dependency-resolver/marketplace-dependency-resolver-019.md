envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T23:19:12Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Emit a DISPATCH line per settle iteration, not per settle entry

# Emit a DISPATCH line per settle iteration, not per settle entry

## Context

`pre-submission-self-review` ran a three-iteration settle in this plan:

| Event | Timestamp |
|-------|-----------|
| `[DISPATCH]` line emitted | 17:42:51Z |
| Candidate-count gate DISPATCH decision (155 candidates) | 17:44:39Z |
| `execution-context.pre-submission-self-review` Complete | 17:49:25Z |
| Complete — iteration 2, 156 candidates examined, 0 findings | 18:03:00Z |
| Candidate-count gate DISPATCH decision (154 candidates) | 18:29:34Z |
| `execution-context.pre-submission-self-review` Complete | 18:30:17Z |

Three distinct envelope completions, two candidate-gate dispatch decisions —
and exactly one `[DISPATCH]` work-log line, emitted before the first iteration.

## Root cause

The `[DISPATCH]` emission is placed at settle *entry* rather than at each
iteration's dispatch. The execution-context dispatch audit pairs
`effort resolve-target` decision entries against `[DISPATCH]` work-log lines, so
a settle that runs N iterations is indistinguishable in the audit trail from one
that runs once.

The practical cost is measurement, not correctness: the settle is one of the
larger token consumers in finalize (218,690 tokens recorded for this step) and
its per-iteration cost is invisible. It also means the audit's `shape_violation`
category cannot distinguish "resolve with no dispatch" from "dispatch not
logged" for this step.

## Proposed action

1. Move the `[DISPATCH]` emission inside the settle loop so each iteration emits
   its own line, carrying an iteration ordinal.
2. Apply the same treatment to any other loop-shaped finalize step that
   re-dispatches into the same envelope.
3. Extend the dispatch audit to assert iteration-count agreement: the number of
   `execution-context.{step}` Complete lines should equal the number of
   `[DISPATCH]` lines for that step.

## Evidence

- aspect: execution_context_dispatch_audit — the single `shape_violation` finding
  for this plan.
- work.log — one `[DISPATCH]` at 17:42:51Z; Complete lines at 17:49:25Z,
  18:03:00Z and 18:30:17Z.
- decision.log `75f8f6` and `41b93a` — the two Candidate-count gate DISPATCH
  decisions, at 17:44:39Z and 18:29:34Z.
- decision.log `ac5e41` (18:32:14Z) — the settle-convergence decision, which
  documents that iteration 3 was a real pass over the same surface.
