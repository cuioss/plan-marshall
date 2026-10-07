envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T13:17:31Z

# Zero resolve-target intent records make the dispatch audit shape check vacuous

component: plan-marshall:ref-workflow-architecture
category: bug
confidence: high

## Context

The execution-context dispatch audit's primary check, `shape_violation`, detects a spawn that happened
but emitted no `[DISPATCH]` line. Its documented pairing rule needs two surfaces:

- **Surface A** — `logs/work.log` `[DISPATCH]` lines (the observable)
- **Surface B** — `logs/decision.log` `(plan-marshall:manage-config)` `effort resolve-target` entries (the intent)

A `shape_violation` is an unmatched Surface-B entry. This plan emitted **18** Surface-A lines and
**zero** Surface-B entries across 80 decision-log entries. With no left-hand side, the check cannot fire.
It reported clean — for the same reason it would report clean if every dispatch were perfectly logged.

That the check is vacuous rather than passing is provable within this same plan: `pre-submission-self-review`
demonstrably ran three envelopes against one `[DISPATCH]` line, which is precisely the failure
`shape_violation` exists to catch, and it was not caught.

## Root cause

Dispatch sites emit the `[DISPATCH]` observable but no caller invokes `effort resolve-target` in a way
that writes the intent record — either the resolver is not being called, or it is called without logging.
The audit's standard documents Surface B as though it were reliably present; nothing asserts that it is.

## Proposed action

Either (a) make the dispatch sites emit the resolve-target intent record so Surface B is populated, or
(b) if the resolver is intentionally silent, re-found the `shape_violation` check on a surface that
actually exists — for example pairing `[DISPATCH]` lines against `execution-context.{role} Complete`
markers, which WOULD have caught the self-review re-fire. In either case add a precondition guard: when
Surface B is empty, the aspect must report the check as `skipped — surface absent`, never as clean.

**Generalizable rule:** a set-guarding detector whose population is empty must say so. Reporting "no
violations" from an empty population is indistinguishable from reporting it from a clean one.

## Evidence

- aspect: execution_context_dispatch_audit — `surface_b_resolve_target_entries: 0` against `surface_a_dispatch_lines: 18`
- aspect: execution_context_dispatch_audit — `surface_absent` finding, and the `caveat` on `direction_1_verdict`
- aspect: logging_gap_analysis — `plan-wide,DECISION` gap, severity `error`
- The uncaught instance: work.log 08:43:44 single `[DISPATCH]`, three `execution-context.pre-submission-self-review Complete` markers
