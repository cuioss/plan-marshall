envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=candidate-lesson
created=2026-09-21T09:26:15Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
title=Phase Dispatch Boundaries never renders - the key is nested, the lookup is top-level

# Phase Dispatch Boundaries never renders - the key is nested, the lookup is top-level

## Context

This plan's retrospective produced a rich dispatch-boundary dataset: 103 rows across
three phases (4-plan 2, 5-execute 10, 6-finalize 91), every phase marked
`present: true`. The compiled report's `Phase Dispatch Boundaries` section was
nonetheless reported under `sections_omitted` — the BENIGN half of the non-emit
partition, defined as "the section's trigger fragment was absent or carried nothing
renderable, so there was nothing to lose".

Something was lost. 103 rows of termination-cause and token data did not reach the
report, and the report classified that as nothing-to-lose.

## Root cause

Two statements in SKILL.md row 17 are jointly unsatisfiable given the code:

- "**injected, never dispatched**: no `collect-fragments add` command is issued for this key"
- "`compile-report` renders it from the bundle under the same key"

`analyze-logs` emits `dispatch_boundaries` as a block NESTED INSIDE its own
`log-analysis` result. The bundle stores fragments keyed by aspect, so the block lives at
`bundle['log-analysis']['dispatch_boundaries']`. `should_emit` looks it up at
`fragments.get('dispatch_boundaries')` — the top level — and finds nothing. Nothing in
the collection path hoists it (a content sweep for the key returns no hit in
`collect-fragments.py`).

So the key is registerable (`valid_aspect_keys()` admits it — no leading underscore),
no producer registers it, the doc forbids registering it, and the consumer looks for it
somewhere it never is.

## Proposed action

Pick one of the two dispositions and make the code and the doc agree:

1. Have `compile-report` read the block from inside the `log-analysis` fragment (a
   nested-source row in `SECTION_SPEC`, mirroring how `_footprint-derivation` is
   injected by the consumer itself); or
2. Have the orchestrator register it explicitly, and delete the "never dispatched"
   sentence.

Either way add a test that asserts the section RENDERS when `analyze-logs` reports at
least one phase `present: true` — the current tests evidently exercise `should_emit`
with a synthetic top-level key, which is why this ships dead.

Note for the orchestrator: SKILL.md row 17 records that the injected-row disposition
"was taken" over a structural `_`-prefix rename, and asks that the rename be revisited
only as its own deliverable. This lesson is that deliverable's trigger.

## Evidence

- compile-report run: `sections_omitted` contains `Phase Dispatch Boundaries`
- aspect: log_analysis — `dispatch_boundaries` carries 3 phases, all `present: true`, 103 rows total
- source: `scripts/compile-report.py` `_dispatch_boundaries_has_present_phase` reads `fragments.get('dispatch_boundaries')`
- source: `scripts/retro_sections.py` `SECTION_SPEC` row `('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries')`
