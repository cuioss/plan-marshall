envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T09:47:30Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_plan=dual-homed-hook-install-renders-identically
source_aspects=plan_efficiency,invariant_summary

# Do not close self-review on the round type with a 100% residue-hit rate

## Context

`pre-submission-self-review` closed `outcome: done` after round 10 found one defect, which was fixed. No round 11 ran, so no clean round confirmed the closure. The deviation was recorded honestly in the step's own `display_detail` — "13 fixed over 10 rounds; final sibling deletion not re-reviewed" — and is a deliberate, visible departure from Branch A's clean-round precondition rather than a silent one.

What makes it worth a lesson is *where* the closure was taken. Every round from 6 to 10 had found residue of the previous round's fix: a 5-of-5 residue-hit rate. The step therefore stopped at exactly the point where the observed probability of a further residue was at its maximum, on the strength of a fix that had never been re-examined.

A post-merge check of the two menu docs at HEAD found no residual defect on the surface inspected, so this closure did not in fact leak. That is a spot check of two files, not a proof, and it does not retire the rule.

## Root cause

The clean-round precondition is stated as a step-level rule, but the decision to close is taken with the round-level history in view and no rule that reads it. A run whose recent rounds all found residue and a run whose recent rounds were all clean face the same precondition and the same override cost.

## Proposed action

Make the closure rule history-sensitive rather than uniform: when the previous K rounds each found at least one defect, the clean-round precondition is not waivable, and the step must run one more round. When recent rounds were already clean, the existing waiver is unchanged. Record the residue-hit rate alongside the round count in `display_detail`, so the closure's risk is legible in the status record instead of only in prose.

## Evidence

- `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]`: `firing_count: 4`, `prior_firings: [failed, done, done]`, `display_detail` naming the un-re-reviewed deletion
- aspect: plan_efficiency — `self_review_cost.rounds: 10`, `defects_found: 13`
- Post-merge verification at HEAD: `architecture search --content --pattern "dual-homed"` returns 8 files, all inside the plan footprint; both menu docs carry a consistent three-value domain and neither claims the dual-homed state is repairable. No residue observed on this surface.
