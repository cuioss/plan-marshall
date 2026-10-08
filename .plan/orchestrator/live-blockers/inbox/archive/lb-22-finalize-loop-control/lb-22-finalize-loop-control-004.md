envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T20:57:00Z

component=plan-marshall:manage-references
category=bug
source_plan=lb-22-finalize-loop-control
confidence=high

# Carry fix-task files into references.affected_files on loop-back

## Context

`references.affected_files` held 48 entries for the whole finalize phase. Fix task TASK-22 (commit `fdb74d1cf`) changed `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md` and `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py`; neither joined the list.

`project:finalize-step-plugin-doctor` selects whole-tree mode when an `affected_files` entry sits under `plugin-doctor/**`. It read the list on all 7 firings, found no such entry, and ran scoped over 11 skill directories each time. The whole-tree run that trigger exists for never happened, on a branch that had changed plugin-doctor's own rule catalog.

## Root cause

`sync-affected-files` derives the list from the outline's deliverables. A fix task created by triage declares its files on the task, not in the outline, so the list has nothing to grow from: it stayed at 48 entries through seven fix tasks. Whether a re-sync ran on each loop-back was not checked here; with the outline unchanged it could not have added anything.

## Proposed action

One of:

- when triage creates a fix task, union its step targets into `references.affected_files`; or
- make consumers that gate on "what did this plan change" read the realized footprint (`compute-footprint`) instead of the declared list. For plugin-doctor mode selection the realized footprint is the correct input in any case.

## Evidence

- aspect: chat_history_analysis - every plugin-doctor hand-back states "affected_files read succeeded (48 entries); no entry under plugin-doctor"; the first one flags that the dispatcher's note named the two plugin-doctor files and that the recorded list looked stale.
- aspect: artifact_consistency - `references_only[9]` lists nine realized-but-undeclared paths, `rule-catalog.md` and `test_analyze_shim_marker.py` among them.
- aspect: manifest_decisions - check `declared_vs_realized_set` failed: 1 declared-but-unrealized and 9 realized-but-undeclared paths.
