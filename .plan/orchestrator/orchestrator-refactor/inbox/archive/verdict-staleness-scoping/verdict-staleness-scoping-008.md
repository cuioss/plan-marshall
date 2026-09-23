envelope_version=1
sender_type=plan
sender_id=verdict-staleness-scoping
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T21:28:46Z

# Phase Dispatch Boundaries section can never render - no producer for its key

## Metadata

- component: `plan-marshall:plan-retrospective`
- category: bug
- confidence: high
- observed_in_plan: verdict-staleness-scoping

## Context

`SECTION_SPEC` registers a `Phase Dispatch Boundaries` section on the fragment key
`dispatch_boundaries`, gated by `_dispatch_boundaries_has_present_phase`. On this plan
`analyze-logs` produced boundary data for all three dispatching phases — 1 row for `4-plan`,
3 for `5-execute`, 6 for `6-finalize`, each with `present: true` — and the section was still
reported under `sections_omitted`, the partition's BENIGN half. Two independent compile runs
over the same bundle reproduced it.

## Root cause

The key is never populated at the level the consumer reads it. `compile-report.load_fragments`
returns "a top-level dict whose keys are aspect names and whose values are the aspect fragment
dicts", so a section lookup resolves a top-level ASPECT key. `analyze-logs` emits
`dispatch_boundaries` NESTED inside its own `log-analysis` fragment, and SKILL.md row 17 states
that no `collect-fragments add --aspect dispatch_boundaries` command is issued for this key —
while `collect-fragments.py` references the key nowhere at all. So no producer can put it at the
top level, and the documented claim that "`compile-report` renders it from the bundle under the
same key" describes a hop that nothing performs.

This is the dead-registry-row shape SKILL.md row 17 explicitly reasoned about and decided to
document rather than rename. The documentation choice was recorded; the fact that the row is not
merely unregistered but structurally unrenderable was not.

## Proposed action

Pick one and make it real. Either (a) have `compile-report` read `dispatch_boundaries` from
inside the `log-analysis` fragment, matching where the producer actually emits it, or (b) hoist
the block to a top-level bundle key during `collect-fragments add` for `log-analysis`. Add a
test that fails when a plan carrying `present: true` boundary rows omits the section — the
current omission is indistinguishable from the benign case, which is why it survived.

## Evidence

- observed: `sections_omitted` contains `Phase Dispatch Boundaries` on both compile runs, while the `log-analysis` fragment carries `dispatch_boundaries` with `present: true` for `4-plan`, `5-execute` and `6-finalize` and 10 boundary rows in total
- source: `compile-report.load_fragments` docstring — bundle keys are aspect names, values are fragment dicts
- source: `plan-retrospective/SKILL.md` row 17 — "no `collect-fragments add --aspect` command is issued for this key"
- source: `architecture search --content --pattern dispatch_boundaries --category script` matches `analyze-logs.py`, `check-dispatch-audit.py`, `compile-report.py`, `retro_sections.py` — and NOT `collect-fragments.py`
