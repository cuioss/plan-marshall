envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:49:57Z

component=plan-marshall:phase-3-outline
category=anti-pattern
confidence=medium
source_plan=documented-invocations-cannot-succeed-as-written
source_pr=1386

# A file assessed CERTAIN_EXCLUDE and declared read-only was written to anyway

## Context

`marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md`
carried two independent scope declarations, both saying it would not be modified:

- outline assessment `CERTAIN_EXCLUDE` — 1 of only 3
  `certain_exclude_assessed_paths` on the whole plan
- deliverable 1 declared it under `Files to survey:` with `intent: read`

It appears in the realized footprint. `check-outline-vs-shipped` reports it as
`exclude_violated: 1 of 3`, described in that aspect's own words as "the one
unambiguously bad outcome".

## Root cause

Neither declaration is enforced at write time, and — the reason this is easy to
miss — the *third* check, the one that does run, PASSES. Scope creep is measured
against the full declared surface including read-intent entries, so a file
declared read-only is by construction never scope creep. The declared-surface
check therefore reports the file as in-scope and expected, while the intent
annotation and the assessment both say it should not have been touched.

The failure is not that a check was absent; it is that the check that fired
answers a different question from the two that were violated, and its green
result is the one a reader sees first.

## Proposed action

When a path carries a `read` intent or a `CERTAIN_EXCLUDE` assessment and appears
in the realized footprint, surface it as a distinct outcome class rather than
letting the declared-surface pass absorb it. `check-outline-vs-shipped` already
computes `exclude_violated` correctly; the gap is that no gate consumes it and
the sibling scope-creep verdict reads clean over the same file.

## Evidence

- aspect: outline_vs_shipped — `exclude_violated: count 1, denominator 3,
  population certain_exclude_assessed_paths`, member `task-contract.md`
- aspect: request_result_alignment — the same path listed under
  `scope_creep_excluded_as_declared` with covering declaration "deliverable 1
  survey scope, read intent"
- aspect: artifact_consistency — `read_intent_excluded: 4`, confirming the file
  was excluded from the modification-intent denominator
