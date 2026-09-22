# Landing Analysis: PLAN-CIS-029 — Architecture store concept model

epic: code-intelligence-substrate
workstream: WS-01
pr: 1216
merge_commit: `bc8639843`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/150-architecture-store-concept-model/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**partial** — 2 of 4 deliverables confirmed; 2 refuted on the shipped tree. Independent post-run audit verdict: **PARTIALLY REFUTED**.

**The only plan in this ingest with Done-when clauses proven false by live probe, not merely gapped.** D1 ("every persisted key resolves to a path") is false because the dotted-to-path migration is read-only and never written back. D4 ("stale reported for a document generated against a different tree") is false because `architecture info` derives freshness from a denormalised index snapshot and **fails open** — reporting `fresh` both for a diverged-tree document and for a missing one.

## Premise verdict

**Partially refuted.** D2 (closed type vocabulary) and D3 (index descriptions) are cleanly confirmed with mutation-proven guards. But D4's flagship claim — *the tree identifier is the stronger primitive than mtime* — is undermined in practice: the only shipped consumer reads the wrong header (index, not document) and fails open on both divergence and absence.

## Gaps carried out of this landing

**20 total — 2 high, 11 medium, 7 low.** High: G1, G2.

- ⛔ **This plan's refuted clauses are load-bearing for the three plans that sit on top of it.** PLAN-CIS-033 explicitly builds its `minimal` marker on this plan's fail-closed posture and cites it by name.
- **`key_packages` migration is broken end to end** (G3/G4/G5/G9): one consumer (`manage-solution-outline.py`, feeding phase-3-outline) reads unmigrated dotted keys straight from disk.
- A second, undisclosed writer (`_cmd_manage.py:717`) bypasses `save_module_enriched` entirely, refuting the plan's own hypothesis that the named accessors are the only writers (G8).

## Inconsistencies found, and what was verified

- PR body claimed the false "index is source of truth" claim was corrected "across every document that restated it" | verified by a content sweep for the literal phrases against the commit's 17-file list | **verdict: false — nine files still teach the retired semantic, one of them in MUST form.** The most consequential single misstatement found in this ingest.
- Report's D4 row claimed freshness surfaces "without reading any concept body" | verified by direct probes against the real `get_project_info`, re-run at adversarial review with byte-identical results | **verdict: the primitive is correct and body-free, but its only consumer fails open.**

## Residue

No provenance back-fill exists for pre-field legacy documents (permanently `unknown`). "At what point" was never recorded despite being named in D4's own required text.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-029 --status shipped`
- [x] row `pr` stamped `1216` — `orchestrator queue --set-row PLAN-CIS-029 --field pr --value 1216`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-029 --field landing --value landings/PLAN-CIS-029.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

**Highest-priority remediation target in WS-01.** G1/G2 route to **PLAN-CIS-049** (`510`); the nine surviving retired-semantic documents route to **PLAN-CIS-054** (`560`). ⛔ When G1/G2 are fixed, re-check whether PLAN-CIS-033's `skills_by_profile` freshness inherits the same document-vs-index divergence — **no plan tested that interaction.**
