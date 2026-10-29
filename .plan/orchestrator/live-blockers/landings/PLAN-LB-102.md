# Landing Analysis: PLAN-LB-102 — The runbook lane reads its spec from the ledger worktree first and falls back to the main checkout, by default

epic: live-blockers
workstream: WS-04
pr: #1882 (merge commit 6d155457052b34b26dceccb170c74d2a67e636e9)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-102.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Grade: B. All four deliverables are met and the behaviour change is proven end to end, but the landing is
incomplete (`total_tokens` unknown) and the run asked the operator a Sonar question the standing ruling says
is never asked.

## Deliverable Fidelity vs Spec

Checked against the merge commit's diff (`git show 6d1554570`, three files, +302 −126), the PR state read through
the `ci` abstraction (merged, merge-group run 40758626047 completed with success), and a live `runbook_lane resolve`
call on the merged tree.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 default read order is worktree, then main | shipped-as-specified | `_resolve_spec` now takes the ledger copy first (`if ledger_copy is not None`) and falls back to the main copy; `_staged_spec_shape` accepts a ledger-store path with no flag. Live check: `resolve --spec …PLAN-LB-101…` with no flag returns `spec_source: ledger_worktree`. |
| D2 `--spec-from-ledger` stays accepted, means the default | shipped-as-specified | The argparse flag is kept as a documented no-op (help text and `SKILL.md` L46 and L188 say so). The decision and its reason (an old emitted command must not become `unrecognized arguments`) are recorded in the landing. |
| D3 result and lane text still say which copy was read | shipped-as-specified | `spec_source` and `spec_differ` unchanged in meaning ("the copy NOT read says something else"); the old sentence "Read it from the **main checkout** by default" no longer occurs in the lane text at the merge commit (the only two `spec-from-ledger` hits are the no-op statements). |
| D4 write rule unchanged | shipped-as-specified | The diff touches no write path; `test_reading_the_ledger_copy_writes_nothing` is cited by the landing. Test bodies were not re-run here. |
| Standing constraint: containment before label | shipped-modified (improved) | Review found a same-shaped file outside both stores was labelled `main_checkout`; `_named_copy_is_contained` now refuses it. This is the standing constraint made binding, not scope creep. |

Surface: the merge touched exactly `runbook-lane/SKILL.md`, `runbook_lane.py` and `test_runbook_lane_spec_source.py` — inside the declared
Expected Surface (`test_runbook_lane.py` was declared but needed no change). No surface drift.

## Metrics and Anomalies

- Tokens: `unknown` — the OpenCode harness measured none. This is the one required key missing from the landing facts, so
  `inbox landing-check` reported `complete: false`.
- Duration: the landing message is stamped 20:20:05Z; the first trigger it records is 18:57:51Z.
- Anomalies: one routed `module-tests` job ran while the worktree was being edited and was discarded and superseded; the routed
  `verify` hit the daemon's supervisory bound once (1498 s) and the split form ran from then on; two jobs failed `execution_failed`
  on a relative `--project-dir` (see Follow-Ups).

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed head `9caa2dfe9` with one Major finding, fixed in `cafb6ca84`, thread
  resolved; the re-review after the last push was refused on quota. Sourcery (optional) approved the merge head. This is the settled
  standing-authorization case (a valid review exists, the quota blocks the re-review): moving on was correct and nothing here is raised
  as a question. The review history was taken from the landing and was not re-read from the PR threads here.
- CI/merge: merged through the merge queue, parent of the merge commit is the ledger land `c4089e29e`; the main checkout is clean.
- Sonar: the landing reports `open_issue_count=unknown`, `open_issue_rules=unknown` (never `0`, so no false clean claim). The run
  asked the operator once whether to merge despite an undecidable Sonar read and was told to merge. That question should not exist:
  Sonar is not enabled for this project, yet `runbook_lane resolve` still reports `sonar: configured` with project key
  `cuioss_plan-marshall` (read live on the merged tree), so the lane's merge gate demands a Sonar condition no run can satisfy.
  Under the operator's Sonar ruling this is a note, not a finding: it is recorded as a Watch about the lane's behaviour (the lane
  asks where the ruling says nothing is asked), not as a Sonar defect.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-102 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-102 --field pr --value 1882`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-102 --field landing --value landings/PLAN-LB-102.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-102 --field plan_marshall_plan_id --value rb-lb-102-ledger-first-spec-read`
- [x] epic.md narrative reconciled (the HIGH item "the lane cannot read a spec from the ledger worktree" retired; Open Defects added)
- [x] defect opened: incomplete landing (`total_tokens`); Watch opened: the lane still asks a Sonar question at the merge gate
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

Not verified here, and recorded as such: the per-landing session-database checks the anchor lists (restart count, guard-log lines by
session tree, read-class shell totals, edits outside the worktree, spoofed-identity prefixes). The landing's own claims on those
(guard log has no line for the run, no shell file operations, two disclosed reads outside the repository root) stand as unverified
leads.

## Follow-Ups

- Both hypotheses the spec left open were refuted by the lane and accepted: the `/plan-marshall` lifecycle already reads worktree-first
  (`phase-1-init` ingests through `request create --body-file`), and no other doc describes the old default.
- Relative `--project-dir` routing defect: already a Watch in the ledger; this landing is the second observation (every lane run pays
  two failed jobs). It now has a known trigger and a known cost, so it is a candidate to fix in the lane text (say absolute once).
- Lane text at § 4 points the run at job logs outside the repository root, which the run's own "stay inside the repository" rule
  forbids; the run disclosed it. The lane text should say which of the two wins.
- Runbook-lane size and modularization is being analysed separately.
