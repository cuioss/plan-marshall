envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:07:36Z

component=plan-marshall:phase-4-plan
category=bug
confidence=high
source_aspects=manifest-decisions,invariant-summary

# compose received a deliverable-level change_type and narrowed phase-5 for the whole plan

## Context

`manage-execution-manifest compose` takes `--change-type` as a required caller-supplied flag and does not reconcile it against `status.metadata.change_type`. On this plan the caller passed `verification` while the plan's settled classification is `bug_fix`.

The plan's own `detect-change-type` run had already decided this: decision.log `eafc53` records `Detected: bug_fix (confidence 85) ... Overrides prior heuristic value feature`, and `status.metadata.change_type` is `bug_fix`. At finalize, `architecture-refresh` read it back correctly (`Tier 1 skipped - change_type = bug_fix`). Only the compose call disagreed.

The likely source of `verification` is Deliverable 1: decision.log `241d24` records D0 being given its own owner "as Deliverable 1, change_type verification, verification profile, zero affected_files". The caller appears to have forwarded the FIRST deliverable's change_type as the PLAN's change_type.

## Root cause

`change_type` is meaningful at two different scopes — per-deliverable and per-plan — and the compose contract accepts the value without naming which scope it wants or checking it against the plan's own record. A plan whose first deliverable is a measurement/verification step therefore gets its whole phase-5 verification narrowed.

## Proposed action

Have `compose` read `status.metadata.change_type` as the authority and treat an explicit `--change-type` that contradicts it as an error (or at minimum log a `[STATUS]` divergence line naming both values). The composer already reads `status.metadata` for `plan_source` / `recipe_key` via `_read_recipe_source`, so the seam exists.

Separately, name the scope in the flag help: `--change-type` currently reads `Change type (one of VALID_CHANGE_TYPES)` with no indication that it is the plan-level value.

## Evidence

- decision.log `c818ce` — `finalize-step-simplify omitted — change_type=verification affected_files_count=9`
- `status.metadata.change_type: bug_fix`; decision.log `eafc53` and `9c2cef` both read `bug_fix`
- decision.log `06a943` / `243b2d` — Rule `tests_only` dropped `verify:quality-gate` AND `verify:coverage` from phase-5 as a direct consequence
- The shipped diff contains two production source files, so the tests-only assumption the narrowing rests on was false
- Mitigation that actually held was unrelated: decision.log `c11f4a` kept `pre-push-quality-gate` on an unknown build verdict
