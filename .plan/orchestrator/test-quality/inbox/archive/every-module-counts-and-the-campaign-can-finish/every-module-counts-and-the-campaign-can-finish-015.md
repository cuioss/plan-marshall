envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:34:39Z

component=plan-marshall:manage-findings
category=improvement
confidence=medium
source_plan=every-module-counts-and-the-campaign-can-finish

# An advisory finding that names its own discharge condition still needs someone to close it

## Context

At 2-refine, finding b47715 recorded the documented suspicious-uniformity signal: all six confidence dimensions scored 100. It was filed explicitly as advisory — "flagged for outline-phase confirmation rather than blocking" — and it named its own discharge condition in the same sentence: confirmation during the outline phase.

Outline ran. Plan ran. 5-execute executed all 12 tasks against that spec without a single spec-derived correction, which is exactly the confirmation the finding asked for. The finding stayed pending through 3-outline, 4-plan and most of 5-execute, and was closed by hand at 18:46 on the second day with the resolution text: "Left pending only because no step closed it after outline confirmed it."

Separately, `phase_handshake` reported drift twice as `script_internal_failure` (exit 1), and one of the two drifts is this same bookkeeping: re-entering 3-outline observed `qgate_open_count` 2 against a captured 2, then `pending_findings_blocking_count` 3 against 1 — counts moving because findings were being closed, not because anything about the plan changed.

## Root cause

A finding can state a machine-checkable discharge condition ("confirmed if phase 3 completes on this spec") but there is nowhere to put it. `resolution` is a field a human or a step writes AFTER the fact; there is no field saying what would settle it, and therefore no step that can be responsible for checking.

The consequence is not a wrong answer — the finding was correct and its own reasoning anticipated the outcome — but pending-count noise that outlives its subject and shows up in unrelated guards.

## Proposed action

Allow an advisory finding to carry a discharge condition at filing time (the phase whose clean completion settles it), and have that phase's transition close it automatically. A finding that names its trigger is the easy case; findings that cannot name one keep today's manual close.

Modest scope, and it removes a class of stale pending state that currently reaches the phase handshake.

## Evidence

- qgate finding b47715 (2-refine), filed 07:35 day 1, resolved 18:46 day 2, resolution text names the gap directly
- work.log line 52 — `phase_handshake` drift at 3-outline: `qgate_open_count` captured 2 observed 0, `pending_findings_blocking_count` captured 3 observed 1
- work.log line 665 — `phase_handshake` drift at 1-init re-entry, `pending_findings_blocking_count` captured 0 observed 1
- Both handshake drifts are the guard working as designed; they are cited as the downstream cost of the pending-state churn, not as defects
