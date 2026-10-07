envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:37:36Z

component=plan-marshall:plan-retrospective
category=bug
confidence=medium
source_plan=prq-06-a-lane-override-that-cannot-take-effect-is
source_aspects=artifact_consistency,request_result_alignment

# Declared-file parser counts the literal (none) placeholder as a path

## Context

`check-artifact-consistency` reported:

```
affected_files_recall,pass,Recall 86% meets threshold
details.affected_files_recall:
  declared: 28
  found: 24
  missing[4]:
    - (none)
    - test/plan-marshall/manage-execution-manifest/test_ceremony_finalize_selection.py
    - test/plan-marshall/plan-retrospective/_check_routing_decisions_fixtures.py
    - test/plan-marshall/plan-retrospective/test_check_routing_decisions.py
  recall_pct: 85.7
```

The first `missing[]` entry is the literal string `(none)` — a solution-outline placeholder token admitted into the declared-file set as though it were a path.

Re-deriving the same union independently from `manage-solution-outline list-deliverables` (taking each deliverable's `affected_files` entries whose `intent` is not `read`, unioned across the six deliverables, de-duplicating the two paths declared twice) gives 27 declared, 24 found, **88.9%** recall.

## Root cause

The declared-file bullet parser accepts any bullet body as a path. Where an outline section renders an empty list as the conventional `(none)` placeholder, that token becomes a phantom declared file that can never be found in any footprint.

## Proposed action

Filter the placeholder vocabulary out of the declared-file set at parse time — at minimum the literal `(none)`, and any bullet body that is wholly wrapped in parentheses and contains no path separator. Publish the filtered count so the exclusion is visible rather than silent.

This is worth fixing beyond cosmetics: 70% is a graded threshold in `request-result-alignment`, and a per-placeholder inflation of the denominator pushes borderline deliverables the wrong way. On this plan the effect was 3.2 points; on a deliverable declaring three files with one placeholder it would be 25.

## Evidence

- aspect: artifact_consistency — `missing[4]` row 1 is the literal `(none)`; `declared: 28`, `recall_pct: 85.7`
- aspect: request_result_alignment — independent re-derivation over the same two sources gives `declared 27 / found 24 / 0.889`
