envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:18Z

component=plan-marshall:phase-6-finalize
category=bug

# pre-commit-verify-freshness certifies a plan from an unrelated build's ledger row (matches on worktree_sha alone)

## Observation

On PLAN-TRUTH-001 (a **Python-only** plan), the `pre-commit-verify-freshness` gate was satisfied by a change-ledger row produced by **`plan-marshall:build-npm:js_coverage`** — a JavaScript coverage build that exercised none of the plan's changed surface.

## Mechanism

The freshness match is keyed on **`worktree_sha` alone**. There is no relevance check binding the ledger row to the plan's footprint:

- no check that the row's producing command covers the plan's changed modules;
- no check that the row's build kind is a *verifying* kind for those modules;
- no check that the row's producer is even in the plan's build map.

Consequence: **any** build that ran against the same worktree SHA — including an unrelated language's coverage run, a partial compile, or a sibling plan's build in the same tree — certifies the plan as verify-fresh.

## Why this belongs to `truthful-signals`

This is the epic's theme in its purest form: the gate reports a **confident green** whose caveat ("green for a different build") is not representable in its output. The operator sees "verify fresh" and cannot distinguish "this plan's code was verified" from "some code was built here recently".

The failure is silent and *directional* — it only ever produces false green, never false red — so it can never be caught by a failing run.

## Suggested shape of the fix

Freshness must be a **two-key** match, not one: `worktree_sha` **AND** relevance of the row to the plan's footprint. Minimum viable relevance predicate: the ledger row's producing notation must appear in the plan's resolved build map, and the row's scope must cover the plan's changed modules. A row that fails the relevance check should yield "unknown", not "fresh" — an unrelated build is not evidence of anything, and "unknown" is the honest representation.

## Not actioned

Observed during PLAN-TRUTH-001's finalize; out of that plan's scope. Handed to the epic.
