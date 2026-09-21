# Landing Analysis: PLAN-02 — Make argparse rejections name their own fix

epic: finalize-machinery
workstream: WS-02
pr: 1507 (https://github.com/cuioss/plan-marshall/pull/1507, merged as e2e745c70)

> Landing record for one shipped plan. Lives at `landings/PLAN-02.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Corroborated against `ci pr view --pr-number 1507` (state merged, merge_commit
e2e745c70), `git log` (e2e745c70 on main, HEAD since advanced to 0a456b840 by #1504),
and the archived plan at `.plan/local/archived-plans/2026-09-17-invocation-surfaces/`
(14 entries incl. retrofitted solution_outline.md, execution.toon, review-retrospective.md).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Rejection-message remedy (flag + sibling verb at exit 2) | shipped-as-specified | execute-script.py.template + test_dispatch_boundary_error.py in #1507 diff |
| Router-vs-verb splits repaired (prepare-body, github_pr --plan-id, measured-diff-size) | shipped-as-specified | ci.py, github_pr.py in #1507 diff; review_completeness bare scalar + SKILL.md contract verified already-correct at HEAD, not re-broken |
| Doc-contract repair (measured-diff-size safe-when-empty) | shipped-as-specified | automatic-review SKILL.md wording corrected per PR body |
| Regression evidence (3 recorded sites reproduce + demonstrate) | shipped-as-specified | manage-plan-documents read redirect live; manage-status SKILL.md clarified |

Realized-vs-declared variance (for gate calibration, no action — spec is terminal):
realized 7 files; declared 6 entries. `manage-status/SKILL.md` and
`manage-plan-documents/SKILL.md` shipped without declaration (doc-clarification
adjuncts); `execute-script.py.template` shipped where `generate_executor.py` was
declared (generator vs its template — same surface family); `automatic-review/SKILL.md`
declared but untouched (already correct at HEAD). No collision with co-running PLAN-01
resulted — the pair was genuinely file-disjoint where it mattered.

## Metrics and Anomalies

- Tokens: 0 recorded — floor, not a measurement. Phase boundaries for
  2-refine/3-outline/4-plan were never stamped and no session identity exists on this
  target (opencode); both recorded in record-metrics detail and work log.
- Duration: 37299.0 wall seconds per landing-facts.
- Anomalies: 25 manifest steps (22 done, 2 skipped — lane-off adr-propose,
  lessons-capture — 1 loop-back consumed and converged: CodeRabbit triage → 3 fix
  tasks → fix commit → re-review clean). Mid-run process failure (implementation began
  on main, worktree unmaterialized) remediated via snapshot relocation + Step 2.5
  materialization before any commit — see inbox finding invocation-surfaces-001.
  Phases 2-refine/3-outline/4-plan collapsed with bare transitions; solution_outline.md
  retrofitted post-landing via resolve-path → Write (validation passed, 4 deliverables,
  multi_module) with provenance note — deliberately not re-stamping phase
  boundaries/metrics, which would falsify the record.

## Routing and Merge Behavior

- Review: CodeRabbit 3 actionable (all fixed, re-reviewed fix HEAD clean); sourcery
  Approved; cuioss-review-bot re-reviewed after staleness. Participation complete at
  merge; barrier clean on all three predicates.
- CI/merge: merge-queue path — enqueued → landed → post-merge CI green → footprint
  captured → move-back → worktree removed → base pulled → branch pruned → mutex
  released. Terminal mutex release observed already-free (logged, no action).
  cleanup_owed=false — no Watch needed.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-02 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-02 --field pr --value 1507`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-02 --field landing --value landings/PLAN-02.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-02 --field plan_marshall_plan_id --value invocation-surfaces`
- [x] epic.md queue reconciled from status.json
- [x] Open Defect opened: incomplete landing-facts (deliverables_total/done n/a) on invocation-surfaces-003 — manual paste may still surface a required fact the inbox did not
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator compact` (in-place; invariants ok)

## Follow-Ups

- Inbox invocation-surfaces-001 (finding, remediated mid-run process failure):
  absorbed as Watch — no ship semantics.
- Inbox invocation-surfaces-002 (candidate-lesson, argparse naming discipline):
  discarded — remedy already shipped by this landing and corpus-held (19-004); no duplicate entry.
- Inbox plan-01-head-rearm-001 (finding, PLAN-01 outside-lifecycle implementation + PR #1505 open + verification-sufficiency question): absorbed as Watch; verification question escalated to operator.
- Refill emit per orchestrate.md selection (N=2, R=1 → 1 slot): see analyze output block.
