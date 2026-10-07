# Landing Analysis: PLAN-TRUTH-168 — sync-defaults preserves removals, asks before back-filling

epic: truthful-signals
workstream: WS-01
pr: 1674 (https://github.com/cuioss/plan-marshall/pull/1674)

> Landing record. Corroborated against ground truth
> (`ci pr view --pr-number 1674`: state merged, merge commit
> 4d92fb7490e0890bb78eb02f74f768efe0aa4616; head branch
> feature/truth-168-sync-defaults-reverting-remove; landing-check
> `complete: true` on message 005; steps split on last colon, namespaced ids
> `project:*` / `plan-marshall:plan-retrospective` recovered correctly).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — enumerate seeded keyed maps + removing verbs | shipped-as-specified | PR body; `verification_steps` + finalize `steps` |
| D1 — removal survives sync; curated maps never silently expanded; new defaults via ask | shipped-as-specified | atomic-once-present `held_for_ask`, `removed_steps` intent records, legacy `qgate` deferral, removal canonicalization through retired-key renames |
| D2 — report distinguishes new default from re-add | shipped-as-specified | `added` vs `re_added` (crossed decision named); sync report contract documented |
| D3 — regression + positive controls, both step maps | shipped-as-specified | real `remove-step` flow; review-caught membership cases covered |

Changed surface stayed inside the declared `## Expected Surface`
(manage-config merge/intent/report, steward Stage-2 `review-held-defaults` ask
step, Stage-2 order test, D3 controls). No under-declaration found — no
collision-consequence correction owed.

## Metrics and Anomalies

- Tokens: `total_tokens=0` in facts with `total_wall_seconds=88585`; sender
  reports dispatch boundaries with zeroed usage. Complete landing
  (`complete: true`), figures taken as stated.
- Verification (sender-reported, CI-corroborated by merge): full suite green on
  CI (28,820 passed locally too); quality-gate / plugin-doctor / security /
  self-review clean; 6 review findings fixed and responded.
- Anomaly: 251-failure swarm mid-run traced to #1677's committed
  `runtime.target=antigravity` (fixed upstream in #1679; local duplicate dropped
  on rebase) — foreign cause, not this plan's surface.
- Merge-barrier gap covered by explicit operator authorization
  (barrier-ask-override, head-bound, recorded in status metadata) after
  loop-backs could not converge (single-review bot + incremental-only
  reviewer). Sender-reported; taken as the recorded authorization.

## Routing and Merge Behavior

- Review: 6 findings, all fixed + responded. No actionable residue.
- CI/merge: squash-merged via queue (merge commit 4d92fb7). No rebase
  conflicts, no re-verify collision signals.
- `cleanup_owed=false`; branch worktree removed, branches pruned, merge lock
  released per sender (operator-observed via sanctioned verbs).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-168 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-TRUTH-168 --field pr --value 1674`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-TRUTH-168 --field landing --value landings/PLAN-TRUTH-168.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-TRUTH-168 --field plan_marshall_plan_id --value truth-168-sync-defaults-reverting-remove`
- [x] epic.md narrative reconciled (W-2026-10-01-a retired; W-2026-10-02-a opened for #1681)
- [x] resume anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] `queue-view.md` regenerated and committed with the row change — `orchestrator regenerate-view`

## Follow-Ups

- PR #1681 (sync-guard scope fix, drive-by from this run) needs CI + merge —
  tracked as W-2026-10-02-a, not this landing's cleanup.
- Process-rule frictions (4 messages) went to the process-compliance inbox —
  other epic's scope, no action here.
- Operator note: local main 3 commits behind origin after the merge — checkout
  hygiene, no ledger action.
