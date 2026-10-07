envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=candidate-lesson
created=2026-10-03T23:21:14Z

component=plan-marshall:phase-6-finalize
category=improvement

# Skip re-firing pre-push steps whose verdict a docs-only loop-back delta cannot change

## Context

Plan cross-repo-telemetry-archive-and-analyze looped back from pre-submission-self-review five times, and every loop-back re-fired project:finalize-step-lessons-housekeeping, finalize-step-simplify and project:finalize-step-plugin-doctor (firing_count 6 each). Every re-fire made zero edits: lessons-housekeeping retained all 38 lessons six times, simplify applied 0 edits six times, plugin-doctor reported 0 issues six times. The HEAD deltas were 2-line prose fixes (e.g. "HEAD advanced cc7177b74 -> 6c9ae01d2, 2-line docs fix", "ADR-020 wording fix only").

## Root cause

The re-fire rule keys on HEAD movement alone; it does not ask whether the delta touches anything the step's verdict depends on, so a docs-only fix pays the full cost of three dispatches per round.

## Proposed action

Give these steps a declared input set (the verdict-currency mechanism already supports verdict_inputs) or a delta classifier: when the delta since head_at_completion touches no file the step's verdict reads (no lesson component, no new structure, no plugin-doctor-gated skill file), carry the prior verdict forward instead of re-dispatching.

## Evidence

- aspect: plan_efficiency - 6-finalize holds 51% of 13.0M tokens; per-re-fire costs 92K-154K (housekeeping), 56K-134K (simplify), ~90K (plugin-doctor)
- aspect: llm_to_script_opportunities - lessons-housekeeping re-fired 6 times with 0 changes
- status.json phase_steps: firing_count 6 for all three steps, every prior firing outcome done
