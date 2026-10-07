# Landing Analysis: PLAN-11 — `corpus cross-check` false candidates (dated-archive self-collision, `NO_PLAN` sentinel)

epic: orchestrator-refactor
workstream: WS-04
pr: #1676 (https://github.com/cuioss/plan-marshall/pull/1676)

> Landing record for one shipped plan. Lives at `landings/PLAN-11.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `cross-check-dated-archive-self-collision-010.md` (`kind: landing`, `landing-check`
`complete: true`, no missing key). Corroborated on 2026-10-02 against `ci pr view --pr-number 1676`
(`state: merged`, `merge_commit_sha: 8665ddacf`), `git show --stat 8665ddacf`, and two live
`corpus cross-check` runs on the landed tree.

## Deliverable Fidelity vs Spec

The plan executed the spec's five deliverables as two plan deliverables (`deliverables_total=2`,
`deliverables_done=2`); the table keeps the spec's numbering.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — derive the affected population first-party | shipped-as-specified | The exclusion is derived per query and published as `excluded_self_snapshots[]`; live run on `review-apparatus` names `review-apparatus-26-09-21`. |
| D1 — exclude a live epic's own dated archive snapshot | shipped-modified | `orchestrator.py` (+154 lines). Prefix/date-suffix discriminator as specified, plus an unplanned **symmetric claimant rule** added in finalize from self-review findings: a name is excluded only when no OTHER epic directory in either store root could also claim it. |
| D2 — regression test with a negative control | shipped-as-specified | `test_orchestrator_corpus.py` (+364 lines): self-snapshot collision, distinct-sibling control, parametrized predicate test for both directions of the claimant rule. |
| D3 — `candidates_indeterminate` measurably drops on the real corpus | shipped-as-specified, **spec estimate refuted** | Live at `8665ddacf`, `review-apparatus`: `sibling_epic_spec indeterminate` 94 → 92, `candidate_comparison_determinate` still `false`. The spec's "roughly half" estimate was wrong: the snapshot contributed 2 indeterminate candidates, not ~47. D3's own criterion (a drop, remainder accounted for) is met. |
| D4 — exclude the `NO_PLAN` sentinel from `live_plan` candidates | shipped-as-specified | Keyed on `NO_PLAN_SENTINEL`; sited at the orchestrator consumer, the shared walk untouched (the outline-time choice the spec left open). Named in the payload as `excluded_sentinel_plan_count`. Tests include the real-plan-with-empty-footprint control. **Observed live after landing** — the plan's own report could not: this store reports `excluded_sentinel_plan_count: 1`, `NO_PLAN` gone from `live_indeterminate_plans[]`. |

Declared versus realized surface (`inbox landing-check`, `state: expansion_detected`): declared 7, realized 8.

- Added, never declared (3): `.plan/project-architecture/_project.json` and the `plan-marshall-antigravity` /
  `plan-marshall-opencode` `enriched.json` descriptors. Not plan work: the finalize `architecture-refresh`
  step committed a catch-up for modules #1670 introduced on `main`.
- Declared, untouched (2): `manage-status/scripts/_cmd_sibling_collision.py` and
  `test/plan-marshall/manage-status/**` — both conditional on D4 choosing the shared walk, which it did not.

## Metrics and Anomalies

- Tokens: `total_tokens` 6,893,138 (dispatched plus one inline phase, main-context spend on five phases
  excluded); billing-weighted total 128,552,698. Finalize alone 3,487,447, of which 1,438,223 re-bought
  three unchanged verdicts across four loop-backs (lesson `2026-10-02-10-005`).
- Duration: 100,575 s wall (about 27 h 56 min), of which about 18 h was stall on a red `main`.
- Anomalies:
  - `main` went red three times from `.plan/marshal.json`-only PRs (#1666, #1669, #1677), each pausing the
    plan. **#1666 is this epic's own `use_worktree` change**: it failed
    `test_committed_marshal_json_surfaces_every_orchestrator_knob` and was repaired by #1668.
  - `pre-submission-self-review` closed by operator override after 4 rounds; four steps the currency
    classifier marked invalid were not re-fired on the last re-entry (operator ruling, in the plan's log).
  - `project:finalize-step-sync-plugin-cache` FAILED (staleness guard expects two harness bundles the claude
    target never emits). Plugin cache not synced, executor not regenerated, build daemon not reconciled.
  - `scope_creep_check` exited 1 on all three calls; its finding reached no store.

## Routing and Merge Behavior

- Review: zero pending review comments; the unified triage was not dispatched and the review retrospective
  graded `indeterminate` on its zero-findings exit.
- CI/merge: merge queue. The first enqueue was ejected when its merge-group run failed 248 tests on a base
  broken by #1677; the landing gate could not tell "ejected" from "still queued", spent its 1800 s budget and
  consumed a loop-back iteration. Re-enqueued after #1679 repaired `main`; squash-landed as `8665ddacf`.
  `cleanup_owed=false`.
- Collisions: none with another plan of this epic (PLAN-10 was held behind it).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-11 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-11 --field pr --value "#1676"`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-11 --field landing --value landings/PLAN-11.md`
- [x] row `plan_marshall_plan_id` stamped — already `cross-check-dated-archive-self-collision` (set at launch)
- [x] epic.md narrative reconciled against the queue rows (PLAN-11 annotation, gate Open Defect re-measured)
- [x] Open Defect added: `main` reddened by this epic's own config-only PR; Watches added for the stale
      plugin cache and the component-keyed `drain-dedup`
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **The gate is still closed for every epic in this repository.** After the landing this epic reads
  `sibling_epic_spec indeterminate: 95, live_plan indeterminate: 1` (`antigravity`). PLAN-11 removed the two
  false populations; what remains is honest indeterminacy, so only the scope decision (whole-population
  versus per-candidate fail-closed) or declarative surfaces on 95 sibling specs opens it. Stays the Open
  Defect of 2026-09-22 — operator decision.
- Nine candidate lessons promoted (`2026-10-02-10-001` … `-009`); none is this epic's to implement.
- Plugin cache is stale relative to `8665ddacf` — recorded as a Watch; `/sync-plugin-cache` is outside the
  orchestrator's carve-out.
- Accepted limitation, stated in `SKILL.md`: a four-group archive name whose other possible owner has no
  directory in either store root is read as the queried epic's own snapshot.
