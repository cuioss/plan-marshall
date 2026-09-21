envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:18:46Z

component=plan-marshall:plan-retrospective
category=improvement

# check-outline-vs-shipped should apply the read-intent exclusion its siblings apply

## Context

The `outline-vs-shipped` aspect reported `include_unrealised: 8` of 12 `certain_include_assessed_paths` — paths assessed CERTAIN_INCLUDE at outline time but absent from the realized footprint, flagged as "may be a silent descope, or a forecast a later decision abandoned". On this plan not one of the eight is a descope. They are exactly the eight paths the plan declared it would only READ: `references.json` records `read_intent_files: 8 items`, and the sibling aspect `check-artifact-consistency` independently excluded the same eight as `read_intent_excluded: 8` before computing its 100% recall. Three surfaces agree to the unit, and only one of them treats the eight as a problem.

## Root cause

`check-outline-vs-shipped` compares assessed paths against the realized footprint without subtracting declared read-intent. A path declared read-only can never appear in `affected_files` (which is a diff), so counting it as an unrealized inclusion is structurally guaranteed to fire on every plan that declares reference reading — it grades the declaration style rather than the execution. `check-artifact-consistency` already implements exactly this exclusion for its own coverage denominator, so the plan carries the needed data and one aspect uses it while its sibling does not.

## Proposed action

Have `check-outline-vs-shipped` read `references.json`'s `read_intent_files` (or re-derive intent from the outline's declared-file bullets, as `check-artifact-consistency` does) and subtract it from `include_unrealised`, reporting the excluded count alongside — mirroring the `read_intent_excluded` field its sibling already publishes. On this plan that would have taken the finding from 8 members to 0 with no loss of signal.

## Evidence

- aspect: outline_vs_shipped — `include_unrealised: {count: 8, denominator: 12, population: certain_include_assessed_paths}`, `llm_judgement_required: true`
- aspect: artifact_consistency — `details.affected_files_recall`: `declared: 4, found: 4, recall_pct: 100.0, read_intent_excluded: 8`
- references.json — `read_intent_files: 8 items`
- The eight members of `include_unrealised` are path-for-path the eight read-intent declarations across deliverables 1, 2 and 3
