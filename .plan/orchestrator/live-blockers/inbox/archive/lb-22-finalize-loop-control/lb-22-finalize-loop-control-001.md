envelope_version=1
sender_type=plan
sender_id=lb-22-finalize-loop-control
epic=live-blockers
kind=finding
created=2026-10-08T10:49:07Z

# Two tooling gaps hit while planning PLAN-LB-22

Reported by plan `lb-22-finalize-loop-control` (PLAN-LB-22). Both were hit in the `3-outline` phase of this run, on the deep planning lane. Neither is part of this plan's own scope, and this plan changes neither.

## Gap 1 — the outline leaf has no declared signal for an ambiguous change type

**What happened.** `phase-3-outline` Step 4a ran `manage-status change-type-heuristic --persist`. It returned `ambiguous: true` (feature 1, bug_fix 1, tech_debt 1), so nothing was persisted. Step 4b prescribes a dispatch of `plan-marshall:phase-3-outline/workflow/detect-change-type.md`. The outline phase runs as a dispatched `execution-context` leaf, and a leaf cannot dispatch. The leaf returned `status: blocked` with a free-form `required_dispatch` field and wrote no `solution_outline.md`.

**Where the contract is missing.**

- `phase-3-outline/SKILL.md` and `phase-3-outline/standards/outline-workflow-detail.md` § "Step 4: Detect Change Type (Detail)" describe Step 4b as a dispatch issued by the phase body itself.
- `plan-marshall/workflow/planning-outline.md` Step 2 handles three post-return signals from the outline leaf (`domain_narrow_report`, `outline_prompt`, `qgate_validation_required`) and none for a required change-type detection.

**How this run got past it.** The orchestrator resolved the target with the documented `effort resolve-target --default --workflow plan-marshall:phase-3-outline/workflow/detect-change-type.md` call, dispatched `detect-change-type` itself (result: `enhancement`, confidence 72, persisted), then re-dispatched `phase-3-outline` with a prompt note saying the change type was already persisted. On re-entry the heuristic tied again and the leaf read the persisted value. Nothing in the workflow documents prescribes any of these three moves.

**Cost.** One wasted outline dispatch (about 198K tokens, 87s) plus one extra detection dispatch (about 41K tokens).

**Reach.** Every deep-lane, non-recipe plan whose heuristic ties. On the light lane `phase-1-init` Step 8a.5 leaves `change_type` unset the same way; whether the light-lane envelope hits the same stop was not checked.

**Shape of a fix (suggestion only).** Either declare a return signal for the outline leaf (for example `change_type_detection_required: true`) with a matching handler block in `planning-outline.md` Step 2, or move the ambiguous-case dispatch ahead of the outline dispatch into the orchestrator, so the leaf always enters with `change_type` persisted. In both cases Step 4a must read an already-persisted `change_type` before treating a tie as blocking.

## Gap 2 — two documents disagree on the skills the detect-change-type dispatch must carry

- `phase-3-outline/standards/outline-workflow-detail.md` § "Step 4: Detect Change Type (Detail)" → the dispatch block lists `skills[1]`: `plan-marshall:manage-status`.
- `phase-3-outline/workflow/detect-change-type.md` § Inputs states: "Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-plan-documents` (request read), `plan-marshall:manage-status` (metadata persist), `plan-marshall:manage-logging` (decision + work entries)."

The workflow body calls all three scripts (`request read`, `metadata --set`, `manage-logging work` / `decision`), so the one-skill dispatch block under-declares what the workflow uses.

**How this run handled it.** The orchestrator forwarded all three skills, following the workflow's own MUST. Whether a dispatch carrying only `manage-status` would have failed was not tested.

**Shape of a fix (suggestion only).** Make the dispatch block in `outline-workflow-detail.md` carry the three-skill list, or have it reference the workflow's Inputs section instead of restating the list.

## Evidence

- Plan work log and decision log of `lb-22-finalize-loop-control`, phase `3-outline`.
- Documents read at the installed bundle version 0.1.1867.
