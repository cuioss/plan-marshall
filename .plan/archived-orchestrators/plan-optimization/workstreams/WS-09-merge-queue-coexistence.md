# WS-09: Merge-Queue Coexistence

epic: plan-optimization

> Charter document for one workstream. Tracked in the epic `status.json` `workstreams[]` field.

## Charter

Make marshall-steward's merge-queue provisioning coexist with an externally / org-managed merge
queue, and stop it from creating release-breaking bypass-less mandatory queues. Consumer-surfaced
(cuioss org): steward's `enforcement=active` + no-`bypass_actors` ruleset made the queue mandatory on
`main` without exempting the release GitHub App, so the release workflow's direct push to `main` was
rejected (GH013) — artifacts published, tag/GitHub release stranded. Closes when steward is a good
citizen alongside an org-owned queue: never creates a mandatory bypass-less queue, honors a foreign
queue by aligning local config, never mutates a ruleset it didn't create, and finalize enqueues
correctly on a queue-enforced branch.

## Scope

- In scope: steward merge-queue provisioning (create-with-bypass-actors, detect-external, defer-to-
  external config signal); the finalize branch-cleanup merge mechanics on a queue-enforced branch.
- Out of scope: the merge_group CI-trigger guard (PLAN-09, shipped); the `ci pr safe-merge` verb
  itself (PLAN-06, shipped) except as PLAN-19 changes which merge call branch-cleanup makes.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-18-merge-queue-coexistence | staged | A bypass-actors on create + B detect-external-and-align + C `merge_queue_managed_externally` signal + never-mutate-foreign invariant |
| PLAN-19-finalize-queue-enforced-enqueue | staged | D: branch-cleanup w/ `use_merge_queue=true` enqueues via `gh pr merge --auto`, NO `--delete-branch`, NO direct-merge/admin fallback |

## Sequencing and Surface Notes

- Surface-disjoint pair: PLAN-18 (steward/ci/config provisioning) ∥ PLAN-19 (phase-6 branch-cleanup).
  D is independent of A/B/C (D = "when use_merge_queue=true, merge correctly"; A/B/C = "set it
  correctly"). Startable in parallel.
- **Adjacent to staged PLAN-13** (steward-provisioning-fail-closed): the bypass-less-mandatory-queue
  is a concrete instance of PLAN-13's "provisioning must fail closed / never create dangerous state"
  invariant — coordinate so PLAN-13's sweep and PLAN-18's fix don't diverge.
- PLAN-19 adjacent to in-flight PLAN-14 (both phase-6, different steps) — rebase if both touch
  branch-cleanup/phase-6 SKILL.
