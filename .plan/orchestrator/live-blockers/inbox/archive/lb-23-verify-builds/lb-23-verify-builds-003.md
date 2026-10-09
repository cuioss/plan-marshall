envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:01:48Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Declare verdict inputs so head-dependent steps skip unrelated fix commits

## Context

On plan lb-23-verify-builds the two head-dependent project steps, `project:finalize-step-lessons-housekeeping` and `project:finalize-step-plugin-doctor`, each fired 8 times, because every self-review and review fix commit advanced HEAD. All 8 housekeeping firings returned "0 rm, 0 promo, 0 adapt, 64 keep" and all 8 plugin-doctor firings returned clean. By the orchestrator's account `verdict_currency classify` returned `invalidated: verdict_inputs_undeclared` for all of them.

## Root cause

Neither step declares which files its verdict depends on, so any HEAD movement invalidates it. A commit that deletes two sentences in a build document re-runs a 64-lesson classification and a 14-directory plugin-doctor gate.

## Proposed action

- Declare `verdict_inputs` on both steps (housekeeping: the lesson corpus plus the plan footprint by component; plugin-doctor: the touched skill directories) so a commit outside them leaves the recorded verdict current.
- Give housekeeping a delta prefilter so a re-fire re-examines only lessons whose component intersects the files changed since the recorded `head_at_completion` (firing 4 already did this by hand: 4 re-examined, 60 carried over).
- Stop writing one decision-log entry per retained lesson per firing. Firings 1 to 3 wrote 64 each; the decision log reached 710 entries and 180 KB, and three triage leaves reported they could read only part of it when checking for standing decisions.

This matches existing lesson 2026-10-08-21-003 (declare verdict inputs on head-dependent steps); treat this as a recurrence with a cost figure unless the corpus says otherwise.

## Evidence

- status record: both steps `firing_count: 8`, seven prior `done` firings each.
- aspect: plan_efficiency - at least 1,680,033 tokens across the 13 boundary rows identifiable by tool-use signature (6 housekeeping rows at 84 to 88 tool uses, 7 plugin-doctor rows at 16 to 18); rows carry no step key, so this is a floor.
- aspect: chat_history_analysis - housekeeping firing 3: "this third firing over an eight-file commit is another instance of the cost"; firing 4: "I wrote four individual entries plus one aggregate entry".
- Not independently verified: the `verdict_inputs_undeclared` classification itself (orchestrator account; not found in the work-log entries read).
