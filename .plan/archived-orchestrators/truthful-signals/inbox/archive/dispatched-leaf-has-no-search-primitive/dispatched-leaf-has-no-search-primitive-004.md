envelope_version=1
sender_type=plan
sender_id=dispatched-leaf-has-no-search-primitive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:19:31Z

component=plan-marshall:manage-solution-outline
category=bug
bundle=plan-marshall

# manage-solution-outline get-module-context is structurally unusable in phase-3 — it demands a worktree phase-5 has not created yet

## Observation

`manage-solution-outline get-module-context` is invoked by the phase-3-outline workflow, but it resolves a worktree path as a precondition. At phase-3 the plan's worktree **does not exist** — `git worktree add` runs at phase-5-execute Step 2.5, and until then `status.metadata.worktree_path` is unset (`worktree_state: pending`).

Consequence: the call **always** fails with `worktree_resolution_failed` when invoked from its own documented caller. It has no reachable success path in phase-3.

## Impact observed in this run

The **Architecture Hints** section of the solution outline was silently dropped. The failure did not surface as a blocking error at the outline gate — the outline simply proceeded without the hints, so the loss was invisible until noticed by hand.

This is a *silent degradation*: a structurally-broken dependency producing a quietly smaller artifact rather than a loud failure.

## Corrective rule

A verb whose precondition is materialised later in the lifecycle than its documented caller runs is not "flaky" — it is **unreachable by construction**, and 100% broken at that call site. Either:

- the verb must tolerate the pre-materialisation state (fall back to the main checkout, mirroring `get-worktree-path`'s tri-state `pending` contract), or
- the caller must not invoke it before materialisation.

Separately: a dropped optional artifact section should be recorded, not silently omitted. A caller that swallows a dependency failure and emits a smaller artifact is the "unchecked persist" archetype in a different costume.

## Status

**NOT FIXED** — out of scope for PR #1046, carried to the epic.
