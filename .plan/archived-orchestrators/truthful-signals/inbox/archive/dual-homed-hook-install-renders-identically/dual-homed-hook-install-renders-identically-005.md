envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T09:49:27Z

component=plan-marshall:phase-3-outline
category=bug
confidence=high
source_plan=dual-homed-hook-install-renders-identically
source_aspects=outline_vs_shipped,artifact_consistency,request_result_alignment

# Outline assessments are never re-derived when the outline is widened

## Context

`check-outline-vs-shipped` reports for this plan:

```
exclude_violated:
  count: 1
  denominator: 6
  population: certain_exclude_assessed_paths
  members[1]:
    - marketplace/bundles/plan-marshall/skills/platform-runtime/SKILL.md
```

and labels it, in its own finding text, "the one unambiguously bad outcome". It is not a bad outcome. It is a stale assessment, and the timeline shows it:

- **15:34:32Z** — assessment gate writes 12 assessments (6 `CERTAIN_INCLUDE`, 6 `CERTAIN_EXCLUDE`, 0 `UNCERTAIN`). `platform-runtime/SKILL.md` is assessed `CERTAIN_EXCLUDE`.
- **15:50:17Z** — the Q-Gate **fails** deliverable 2, naming `platform-runtime/SKILL.md` (L62, L179) as still asserting the two-value domain the plan widens, so the deliverable's success criterion is unsatisfiable with the declared file list.
- **16:00:16Z / 16:00:22Z** — the outline is revised, D2 widened from 3 files to 5, and `platform-runtime/SKILL.md` becomes a declared `write-replace` file.
- The assessment is never rewritten.

The plan then correctly modified the file, and a first-party report now grades that correct action as the worst class of scope violation it can report.

## Root cause

Assessments are written once, at the assessment gate, and are treated by `check-outline-vs-shipped` as "scope inputs consumed by the decision they informed" — which is right for a static outline. The review-gate re-entry path (`Step 3c`) rewrites the deliverable's declared file set without re-running or invalidating the assessments that scored those files. Nothing in the store records that an assessment predates the widening.

## Proposed action

On any outline re-entry that changes a deliverable's declared file set, re-derive the assessments for the changed paths — or, at minimum, mark superseded assessments so `check-outline-vs-shipped` can partition `exclude_violated` into *violated a live exclusion* and *contradicted by a later approved widening*. The second is not a violation and must not be reported as one.

## Evidence

- decision.log 15:34:32Z `Assessment gate: 12 assessments written (6 CERTAIN_INCLUDE, 6 CERTAIN_EXCLUDE) ... 0 UNCERTAIN`
- decision.log 15:50:17Z `Deliverable 2: fail - 2 under_coverage findings ... platform-runtime/SKILL.md (L62,L179)`
- decision.log 16:00:22Z `Review-gate re-entry complete ... D2 now carries 5 files`
- aspect: outline_vs_shipped — `exclude_violated.members[0] = marketplace/bundles/plan-marshall/skills/platform-runtime/SKILL.md`
- `manage-solution-outline list-deliverables`: D2 declares that path with `intent: write-replace`
