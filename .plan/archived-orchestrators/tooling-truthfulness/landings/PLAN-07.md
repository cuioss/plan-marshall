# Landing Analysis: PLAN-07 — OpenCode install docs

epic: tooling-truthfulness
workstream: WS-06
pr: 1484 (https://github.com/cuioss/plan-marshall/pull/1484, merged as 14fe203c869f)

> Landing record for one shipped plan. Claims verified against ground truth
> (PR state via CI abstraction, HEAD, merge stat, worktree list, working tree,
> tree-wide reference search) — the paste (inbox landing message) was a lead, never a fact.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — pin consumption path on live install | shipped-as-specified | PR body: manual config-dir deploy via generator + sync pipeline pinned OBSERVED on live opencode 1.18.30; marketplace-add + npm-plugin tried-and-rejected; no fourth path invented; no consumer script (existing sync pipeline is the path) |
| D1 — README Installation (OpenCode) | shipped-as-specified | `README.md` +25 in merge stat |
| D2 — split guide + retarget all references (folded 2026-09-13) | shipped-as-specified | `installation.adoc → install-claude.adoc` rename, new `install-opencode.adoc` (+53); tree-wide search for `installation.adoc` returns ZERO hits at HEAD |
| D3 — consistent multi-assistant framing | shipped-as-specified | `distribution.adoc`, `build-server.adoc` in stat |

Corroboration: PR state `merged`, `merge_commit_sha 14fe203c86…` == main HEAD (`git log`);
`git status` clean on main; PLAN-07 worktree removed. Landing-check `complete: true`
(+ live `surface_delta` block, unmeasured). Realized-vs-declared delta: +1
(`manage-locks/SKILL.md` — disclosed scope deviation, operator-accepted fix-in-branch for a
pre-existing whole-tree gate defect, no behavior change) and −1 (`marketplace/targets/opencode/**`
untouched — the conditional HYPOTHESIS never fired). The +1 was disclosed in the PR body
"Scope Deviation Accepted" section, so per this epic's own doctrine it is
disclosed-but-undeclared rather than silent — recorded here, not hidden.

## Metrics and Anomalies

- Tokens: 0 (unmeasured — recorded as absent, not as zero)
- Duration: `total_wall_seconds=28609.0` (~7h57m) per landing-facts
- Steps: 23 listed (all done except `archive-plan:n/a` — same step-fact timing imprecision as
  prior landings; archive observably completed)
- No review/CI anomalies reported

## Routing and Merge Behavior

- CI/merge: merged (queue path per message); no rebase conflicts; no concurrent-plan
  collision (only PLAN-05 was running, orchestrator surfaces vs docs — disjoint)

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-07 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-07 --field pr --value 1484`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-07 --field landing --value landings/PLAN-07.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-07 --field plan_marshall_plan_id --value implement-plan-07-opencode-install-docs`
- [x] epic.md queue reconciled from status.json
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] inbox drained: 1 message (landing reconciled), archived

## Follow-Ups

- PLAN-07's `corpus_spec` rows remain true of the declaration but no longer gate concurrency —
  landed plans leave the live set
- The disclosed `manage-locks/SKILL.md` (+ build-queue prose) expansion is owned by its own
  defect's remediation trail (pre-existing upstream defect, fixed in-branch by operator choice);
  no follow-up owed here

## Post-Landing Supplement (operator paste, 2026-09-13 — corroborated where stated)

- Phase trail: deep lane (S2 scope + S7 risk), refine 99.5% with no operator questions, outline
  4 deliverables with 3 Q-gate triage findings, operator approval at the review gate
  (`plan_without_asking=false`), 5 tasks executed in one envelope — paste-supported,
  consistent with the archived plan trail.
- Fix commit `e956c11` ("correct SKILL prose to exposed build-server and lock verbs") exists
  as a dangling feature-branch object, NOT an ancestor of HEAD (`merge-base --is-ancestor`
  exit=1; contained by no branch) — expected after squash-merge + branch prune. Its content
  rides HEAD's tree via squash `14fe203c8`. No contradiction.
- Rebase conflict in `build-architecture.adoc` resolved keep-both — paste-supported (file in
  squash stat; not re-derived line-by-line).
- Verification figures: whole-tree verify 21152 tests + 727s daemon-routed job after push
  freshness went stale (re-attached, success); module-scope coverage fallback after daemon
  `executor_mismatch` refusal, logged degradation — paste-supported.
- Operator approvals confirmed on record: session_id-less finalize (this epic's logged question
  outcome), fix-in-branch scope expansion (PR-body "Scope Deviation Accepted", recorded above).
- Unverified lead (not a finding): two sibling plans in other epics still in 6-finalize "may be
  hitting the same session_id wall." No epic, plan, or log cited — recorded as a lead for the
  plan-marshall core owner, not as ledger fact. The proceed-with-recorded-omission precedent
  from this landing is reusable wherever it lands.
- With PLAN-07 shipped, this epic's queue holds only staged PLAN-08 — emit next
