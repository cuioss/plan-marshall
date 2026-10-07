envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:50Z

component=plan-marshall:plan-marshall
category=bug
bundle=plan-marshall

# A three-site sweep left a fourth site in the SAME FILE one section below — close the CLASS by content sweep, and publish the sweep's scope

`effort-roles.md` line 39 still read "governs the epic-orchestration identity's
read-only analysis surfaces" while line 69 of THE SAME FILE had been changed by the
same diff to drop exactly that descriptor — and `orchestration-model.md` now admits
write-bound drafting dispatches onto the analyze and decompose surfaces. The
surfaces are no longer read-only, so line 39 contradicted the correction one
section below it.

The sweep that removed the descriptor fixed three sites
(`marshal-json-reference.md` twice, `effort-roles.md` line 69) and left this one.
Class survivors OUTSIDE the surfaced set, found by a worktree-scoped content sweep:
`manage-config/standards/api-reference.md` (1),
`manage-config/standards/data-model.md` (2),
`manage-config/scripts/_config_defaults.py` (1), `doc/user/configuration.adoc` (1),
and `manage-config/scripts/_cmd_effort.py` lines 89-91 ("the three / read-only
orchestrator dispatches", split across lines so a LINE-SCOPED sweep misses it).

Source record: Q-Gate finding `ef6ce6`, phase `6-finalize`, defect_class
`contract_drift`, resolution `fixed` in commit `04f12a22b`.

## Solution

- When a semantic descriptor stops being true, close the CLASS with a content
  sweep (`architecture search --content`) rather than fixing the sites the review
  happened to surface. The surfaced set is a SAMPLE.
- Search for the descriptor's VARIANTS, not one literal: here
  `read-only analysis dispatch|read-only analysis surfaces|three read-only`. A
  phrase split across source lines defeats a line-scoped pattern.
- PUBLISH the sweep's coverage scope with the claim. Here: `architecture search
  --content` over the 5466-file worktree inventory, which excludes `.plan/` and
  non-allowlisted dotfile trees — so it is explicitly NOT a whole-tree claim.
- The convergent fix is DELETION of the stale descriptor, not a new qualifying
  sentence.

## Impact

Two rules in one record: a same-file survivor one section from the edit shows the
sweep was driven by the review's hit list rather than by the file; and a
completeness claim over a sweep is only worth what its stated coverage is worth.
