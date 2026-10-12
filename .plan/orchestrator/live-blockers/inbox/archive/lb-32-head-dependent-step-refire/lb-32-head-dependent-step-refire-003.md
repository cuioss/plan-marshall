envelope_version=1
sender_type=plan
sender_id=lb-32-head-dependent-step-refire
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T03:27:52Z

component=plan-marshall:phase-6-finalize
category=improvement
source_plan=lb-32-head-dependent-step-refire
confidence=high

# Check for an empty lessons corpus before dispatching lessons-housekeeping

## Context

Plan `lb-32-head-dependent-step-refire` exists to make head-dependent finalize steps cheaper to re-fire. On its own run, `project:finalize-step-lessons-housekeeping` fired 11 times and `project:finalize-step-plugin-doctor` 10 times, once per fix commit. Every housekeeping firing took the Step 2 empty-corpus exit ("0 lessons in main_anchored corpus"), which returns before the delta rule the plan ships. Each firing was still a full dispatched envelope.

Finalize held 9498815 of 13500984 recorded tokens (70 percent) across 46 dispatches. The housekeeping firings are the roughly 100K to 125K `step_complete` rows; 11 of them is on the order of 1.2M tokens spent to learn eleven times that there was nothing to judge. That per-step figure is read from row shape, not measured: the boundary rows carry no step key.

## Root cause

The emptiness of the corpus is a deterministic fact a script can establish in well under a second, but it is established inside the dispatched step, after the envelope has loaded its skills and read the footprint and request. The delta rule saves judging work only once the step is already running; it cannot save the dispatch.

## Proposed action

Give the finalize dispatcher a script pre-check for this step: enumerate active lessons through the same store resolution the step uses, and when the count is zero record the empty-corpus `done` inline (same `display_detail`, same `work_performed=false`, same `head_at_completion`) without dispatching. Dispatch only when at least one active lesson exists.

This is distinct from a dispatcher-side skip predicate over changed paths, which this plan's own step document rules out for the delta rule. Whether an inline record for a project-local step fits the external-step contract was not checked in this pass.

## Evidence

- aspect: plan_efficiency — `max_phase_token_share=0.70`, dominant phase `6-finalize=9498815`; status record shows `firing_count: 11` for housekeeping, every recorded firing `work_performed: false`
- aspect: llm_to_script_opportunities — "lessons-housekeeping empty-corpus check dispatched as a full envelope", 11 repetitions
- aspect: chat_history_analysis — all housekeeping returns report `exit: empty_corpus`, `affected_lessons resolve` not called
