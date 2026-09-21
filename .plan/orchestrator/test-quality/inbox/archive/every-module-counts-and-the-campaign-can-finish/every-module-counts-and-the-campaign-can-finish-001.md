envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:25:04Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# Give finalize steps a verdict_inputs surface so currency compares instead of invalidating

## Context

Finalize on this plan cost 1,924,734 tokens — within 5% of the entire execute phase (2,017,648) — and the dominant driver was gate re-firing, not gate work. Five head-dependent steps fired 20 times between them: pre-submission-self-review 5, finalize-step-simplify 5, pre-push-quality-gate 4, project:finalize-step-plugin-doctor 3, project:finalize-step-lessons-housekeeping 3. HEAD advanced repeatedly for reasons unrelated to what those gates read — operator fix commits, a simplify commit, then two rebases onto a moving origin/main.

## Root cause

The verdict-currency classifier returns `invalidated` on any HEAD advance because no finalize step declares a `verdict_inputs` surface. With nothing to compare the head delta against, the classifier has only one safe answer, and it gives it every time. A rebase that brings in two unrelated upstream commits invalidates a quality-gate verdict that depended on none of them.

## Proposed action

Add a declared per-step `verdict_inputs` path surface (a glob set, resolvable from the step's manifest entry) and have `verdict_currency.py` intersect the HEAD delta against it: return `current` when the delta is disjoint from the step's declared inputs, `invalidated` only when it intersects. Steps that decline to declare a surface keep today's unconditional-invalidate behaviour, so the change is opt-in and cannot silently weaken a gate.

## Evidence

- aspect: plan_efficiency — 6-finalize 1,924,734 tokens against 5-execute 2,017,648; max_phase_token_share 0.37, so cost is unusually flat rather than execute-dominated
- aspect: llm_to_script_opportunities — repetition_count 20 across five steps, complexity medium
- status.metadata.phase_steps.6-finalize — firing_count 5, 5, 4, 3, 3 on the five head-dependent steps
