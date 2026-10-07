envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:32:59Z

component=plan-marshall:workflow-integration-git
category=bug
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# baseline-reconcile parses localized git prose as file paths and files spurious blocking findings

## Context

`baseline-reconcile` filed five merge-conflict Q-Gate findings at 2-refine. One was real. Four were git's own German status prose ingested as file paths:

- `automatischer Merge von marketplace/targets/generate.py`
- `automatischer Merge von test/finalize-step-deploy-target/test_deploy_target.py`
- `KONFLIKT (Inhalt): Merge-Konflikt in test/finalize-step-deploy-target/test_deploy_target.py`
- `automatischer Merge von test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py`

Each was filed with the full "re-author the affected scope OR justify in clarifications" remedy text, as though it named a real path. All four were triaged `rejected`. The real conflict (`test/finalize-step-deploy-target/test_deploy_target.py`, finding 739b0f) was a genuine textual collision in the import header and was correctly deferred to the standard rebase step.

## Root cause

The conflict list is scraped from `git merge-tree`'s human-readable output rather than taken from its structured `conflicts[]` list, and the process inherits the operator's locale. Under a non-English locale, informational lines (`automatischer Merge von …`) and the conflict marker line (`KONFLIKT (Inhalt): Merge-Konflikt in …`) both match whatever the path heuristic is, so they become findings.

Two properties make this worse than a cosmetic parse bug:

- The false findings carry the SAME severity and the same blocking remedy text as the real one, so a reader cannot tell them apart without opening each.
- One of the four (`test_refusal_recovery_arming.py`) also genuinely appears in the plan's `affected_files` and in upstream commit 87782159b's file list, so it looks plausible. It took a direct read of `merge-tree`'s real conflicts list to establish it was not a conflict at all.

## Proposed action

Take the conflict set from the structured output, not from prose. Failing that, force `LC_ALL=C` on the invocation so at least the heuristic sees the wording it was written against. A locale-dependent parser in a gate that blocks a phase is a defect regardless of which languages happen to be in use.

## Prior art

Recorded locally during the run as lesson 2026-09-03-19-001. Filed here so the epic holds it with cross-plan context; dedup against that id if it has already been carried.

## Evidence

- qgate findings 2840ab, c2929a, 4c5089, cef1cd (2-refine, `plan-marshall:workflow-integration-git:baseline-reconcile`, warning) — all four `rejected` as parsing artifacts
- qgate finding 739b0f — the single real conflict, `taken_into_account`, resolved at rebase as designed
- 4 of the 5 findings this checker produced on this plan were noise: a 20% precision rate on a phase-blocking gate
