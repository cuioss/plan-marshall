envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:16:25Z

component=plan-marshall:phase-6-finalize
category=bug
disposition=new
severity=high
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369
source_finding=ff2174

# affected_files is re-derived only on an admitted loop-back, so a mid-execute scope expansion silently under-scopes every affected_files-derived finalize gate

## Provenance

This is Q-Gate finding `ff2174` (6-finalize, severity `error`), resolved
`taken_into_account` with the disposition **"OUT OF THIS PLAN'S FOOTPRINT — routed to the
truthful-signals epic rather than fixed here."** No inbox message carried it. The plan-scoped
findings store is the only place it exists, and that store dies with the plan, so the routing
the plan performed had no delivery. This message is that delivery.

## Observed live

`references.affected_files` held **13** entries when `project:finalize-step-plugin-doctor` ran.
The live footprint (`manage-references compute-footprint`) held **33**. The 20-file gap was
deliverable 3, added mid-execute by an operator-directed scope expansion *after* the phase-3 and
phase-4 `sync-affected-files` calls had already run.

plugin-doctor consequently computed `scoped_paths` as exactly **2** skill directories
(`manage-findings`, `tools-file-ops`) and returned **"pass, 0 findings, 37 rules"** without ever
linting `marketplace/bundles/plan-marshall/skills/manage-tasks` — the skill deliverable 3 changed
most substantively (SKILL.md plus `_cmd_pre_commit_verify_freshness.py` and
`_freshness_crosscheck.py`).

Running `sync-affected-files` manually at that point moved 13 → 19, and the 6 added paths were
exactly deliverable 3's.

## The defect is the refresh POINT, not the verb

`phase-6-finalize/SKILL.md` item 7b sub-item (i-b) re-derives the declared footprint on an
**admitted loop-back only**. A plan whose scope moves during `5-execute` and never loops back
reaches finalize with a stale declaration, and every `affected_files`-derived gate under-scopes
against it while reporting a confident green.

A faithful read of a stale value cannot detect its own staleness — only a re-derivation can. That
is the same archetype this plan closed for the findings store, sitting one layer up in the
finalize lifecycle.

## Recurrence

This is at least the second recorded instance. The `content-search-seam` plan recorded the same
under-recording at 19-vs-37 paths. Both instances share the trigger (scope moved during execute,
no loop-back) and the consequence (an `affected_files`-derived gate passes over a surface it never
read). Treat it as recurring, not incidental.

## Relationship to sibling message L3

L3 (`plan-marshall:plan-retrospective`) reports that `check-artifact-consistency` scored
`affected_files_recall: 100%` over `declared 19 / realized 44`, and that its precision half was
forwarded to an aspect that never looked. That is the **measurement** defect — the retrospective
cannot detect an under-declaration. This message is the **cause** defect — why the declaration was
under-scoped in the first place, and which production gate silently skipped a skill because of it.
Different component, different mechanism, different remedy. Filed separately, and the two are
worth scoping together.

## Remedy (for the epic to scope)

Re-derive the declared footprint at **finalize ENTRY** as well, not only on an admitted loop-back.
A gate whose scope comes from a declaration must either re-derive that declaration or publish the
instant it was last derived, so a reader can tell a fresh scope from a stale one.
