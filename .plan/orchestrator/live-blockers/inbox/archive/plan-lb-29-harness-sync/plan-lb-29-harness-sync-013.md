envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:42Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-09

# Document sanctioned forms of the finalize steps the orchestrator improvised

## Context

In the finalize phase of plan `plan-lb-29-harness-sync` the main session departed from the documented steps in seven places and disclosed each one. None caused a wrong result here. Each marks a place where the documented path was missing, slower, or wrong for the situation:

1. Two independent dispatched steps (plugin-doctor and lessons-housekeeping) ran at the same time; their dispatch records end five seconds apart.
2. Fix tasks were given to agents running at the same time on separate files, and the main session committed for them. Those three tasks (026, 027, 028) carry no per-task artifact lines.
3. Re-review trigger comments were posted by the main session, not through the automatic-review step's own trigger path, because that path would have spent another attempt inside an open quota window.
4. One finding that was only a bot's acknowledgement of a trigger (5dc1a8) was closed by the main session without a triage dispatch.
5. The merge-queue landing was awaited with `pr wait-for-queue-settle`, not the documented view-and-sleep poll.
6. The recorded merge commit is the pull request's true merge commit (35b5589b5), not the head of main, which had already advanced.
7. The registry repin was applied once at the operator's explicit direction although the machine setting that enables it is off.

## Root cause

The finalize workflow documents one sequential path per step. It has no stated rule for which steps may overlap, who commits when several agents work on one tree, how a trigger is posted when the step that owns it must not fire, or which commit identifies a queue merge. The main session filled each gap with judgement and a log line.

## Proposed action

For each of the seven, either make it the documented path or forbid it with a reason:

- state which dispatched finalize steps are independent and may overlap, and that their completion marks are still written one at a time;
- give concurrent fix agents a documented contract (separate files, no commit, no formatter run, the dispatcher commits and writes the per-task artifact lines);
- give automatic-review a verify-only entry that neither posts a trigger nor claims a window, and a way to record a trigger the dispatcher posted;
- let the dispatcher close a finding whose class triage has already ruled noise on the same pull request, with one decision-log line;
- replace the view-and-sleep poll in branch-cleanup with `pr wait-for-queue-settle`;
- record the merge commit from the pull request, never from the head of main;
- say that a one-off operator instruction through a question may apply the repin without changing the stored setting, and how it is logged.

## Evidence

- aspect: chat_history_analysis — automatic-review report: "Both triggers had already been posted by the orchestrator for this head"; plugin-doctor report noting "the concurrent lessons-housekeeping step"; three implementer reports with `committed: false` and "the other agent's files".
- aspect: log_analysis — 6-finalize dispatch rows at 2026-10-08T22:07:34Z and 22:07:39Z; tasks 026 to 028 listed without artifacts.
- decision and work log — 0a689a (5dc1a8 closed without a triage dispatch); queue-landing entry "merged by the platform merge queue after about 1470s (budget 1800s), merge commit 35b5589b5"; 46b79b "opt-in disabled; applied once at the operator's explicit direction".
- not verified from the plan's logs: that `pr wait-for-queue-settle` was the verb used for the queue wait (the log names the outcome, not the verb); this item rests on the dispatcher's own statement.
