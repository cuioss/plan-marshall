envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:24:23Z

component=project:finalize-step-plugin-doctor
category=bug
title=Scope-source indeterminacy is detected by LLM judgement, so the same read passed scoped once and escalated to whole-tree once

# A gate whose coverage depends on whether the leaf remembered to cross-check is not a gate

## Context

`finalize-step-plugin-doctor` fired twice in this plan, against the same `references.affected_files` value (14 entries) and the same real footprint.

**Firing 1** (2026-08-24T18:14:53Z): ran **scoped** over 2 skill directories. Its only warning was about cross-skill divergence in general:

> "scoped plugin-doctor cannot detect cross-skill divergence — scoped mode gated skill-local rules over 2 skill dir(s) only."

**Firing 2** (2026-08-25T05:48:27Z): the same read, now classified indeterminate:

> "affected_files read indeterminate as a scope source: returned success with 14 entries against a 19-file git footprint, omitting `phase-6-finalize/standards/branch-cleanup.md` and 4 automatic-review/test files. A scoped run would leave the phase-6-finalize skill dir ungated. Falling back to whole-tree plugin-doctor quality-gate."

Identical inputs, opposite coverage decision. The second leaf cross-checked `affected_files` against the git footprint; the first did not.

## Root cause

The step's documented escalation rule — whole-tree when "the scope read is indeterminate" — has no mechanical indeterminacy test. Indeterminacy is whatever the dispatched leaf notices. The whole plan's structural lint coverage therefore rested on one leaf independently deciding to do a comparison the contract does not require.

Outcome in this instance: no escape. Firing 2 ran whole-tree at HEAD `7dd6f1cd4` — 37 rules, 0 findings, cross-skill class gated. But firing 1's scoped pass over 2 of the 5 touched skill directories reported clean while `phase-6-finalize/standards/branch-cleanup.md` — a file this plan modified and one of the two files carrying its behavioural defects — was never gated.

## Proposed action

Make the indeterminacy test deterministic: compare the declared set against the live footprint in the step's own preamble and escalate on any disagreement, rather than relying on the leaf to notice. This is the consumer-side half of the `manage-references` corroboration proposal — either fix removes the judgement from the path; doing both is defence in depth.

## Evidence

- `logs/work.log` 18:14:53 and 05:48:27 — the two verdicts, verbatim
- `status.metadata.phase_steps["6-finalize"]["project:finalize-step-plugin-doctor"]`: `firing_count: 2`, final `display_detail` "plugin-doctor clean whole-tree: 37 rules, 0 findings"
