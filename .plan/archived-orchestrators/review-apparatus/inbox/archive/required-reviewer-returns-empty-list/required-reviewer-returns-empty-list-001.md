envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:33:15Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-09-05
bundle=plan-marshall

# Split include_unrealised by declared intent in check-outline-vs-shipped

## Context

Two aspects of a single retrospective run returned opposite verdicts on the same two
files, and the compiled report carries both without reconciling them.

On plan `required-reviewer-returns-empty-list`:

- `check-artifact-consistency` reported `affected_files_recall: 100%`, `declared: 3`,
  `found: 3`, with `read_intent_excluded: 2` — it applied the modification-intent rule
  and correctly removed the two read-only survey files from its denominator.
- `check-outline-vs-shipped` reported `include_unrealised: 2 of 5
  certain_include_assessed_paths`, naming exactly those same two files
  (`review_gate_delta.py`, `test_counting_rule_parity.py`) as "assessed CERTAIN_INCLUDE
  but absent from the realized footprint (may be a silent descope, or a forecast a later
  decision abandoned)".

Neither file was ever going to appear in the footprint. The outline's deliverable 1
declares both under `survey_scope` with `intent: read`, and `TASK-001`'s steps 2 and 3
carry `intent: read` as well. They were read, exactly as declared.

## Root cause

`check-outline-vs-shipped` compares an *in-scope* assessment against a *mutation*
footprint without consulting the declared intent that separates the two. The
`CERTAIN_INCLUDE` assessment is not wrong — a read-only survey file genuinely IS in scope
for the deliverable — but a realized footprint is a diff, so a read-intent path can never
appear in it. The comparison is therefore guaranteed to report every survey-scope
deliverable's read files as unrealised, on every plan that declares one.

The aspect's own finding text hedges between two causes it cannot distinguish ("silent
descope, or a forecast a later decision abandoned") while a third cause — declared
read-intent, expected absent — is recorded in the outline and never consulted. The sibling
aspect proves the data is reachable: it already excludes exactly these paths.

## Proposed action

Partition `include_unrealised` by declared intent rather than reporting it as one class:

- `include_unrealised_read_intent` — assessed CERTAIN_INCLUDE and declared read-only.
  Expected absent from the footprint; report as informational context, never as a possible
  descope.
- `include_unrealised_mutation_intent` — assessed CERTAIN_INCLUDE with a mutation intent
  (or no declared intent) and absent from the footprint. This is the genuine
  silent-descope signal the class was created to surface.

Resolve intent through the same path `check-artifact-consistency` already uses, so the two
aspects cannot disagree on the same file again. Keep both counts published with their own
denominators per the existing counted-outcome-class contract.

## Evidence

- aspect: outline_vs_shipped — `include_unrealised: count 2, denominator 5, members: review_gate_delta.py, test_counting_rule_parity.py`
- aspect: artifact_consistency — `affected_files_recall: recall_pct 100.0, read_intent_excluded 2`
- outline deliverable 1 `survey_scope` — both members declared `"intent": "read"`
- `TASK-001.json` steps 2 and 3 — both declared `intent: read`, both `status: done`
