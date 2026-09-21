# Landing Analysis: PLAN-05 — Repair the lessons and landing pipeline

epic: finalize-machinery
workstream: WS-04
pr: 1527 (https://github.com/cuioss/plan-marshall/pull/1527, merged as 6e239a13762514dc8e1f3fbceeb70b3d21ebac06)

> Landing record for one shipped plan. Lives at `landings/PLAN-05.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Corroborated against `ci pr view --pr-number 1527` (state merged, merge_commit
6e239a13) and inbox landing message lessons-pipeline-001 (`landing-check complete:
true`, deliverables 2/2). The new owed-landing readout already works — this drain's
own `inbox list` reported `awaiting_plans: [PLAN-05]` with the landing queued.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Owed-landing notion (awaiting vs no-news) | shipped-as-specified | _orchestrator_inbox.py + orchestrator.py; drain contract tests |
| Lessons dedup at drain + post-housekeeping counts | shipped-as-specified | _lessons_aggregate.py, manage-lessons.py, compile-report.py |
| Orchestration-context bypass fixed at dispatcher (Step 4b.a0) | shipped-as-specified | lessons-integration.md; broken+working same-run reproduction as regression test |
| Lossless retrospective inputs (order, counts, populations) | shipped-as-specified | _chat_signal_reducer.py, extract-chat-signal.py; cross-cutting regression test |

All 7 declared source files + lessons-integration.md touched, plus drain-contract and
regression tests. No refutation of staged-spec claims arrived with this landing — no
set-verdict writes owed (claims stay open for the cleanup re-grounding pass).

## Metrics and Anomalies

- Tokens: 0 floor (facts block carries total_tokens=0); wall 72259s per facts.
  Steps: 21 done, 2 skipped (plan-retrospective, lessons-capture), 1 pending
  (archive-plan — normal pre-archive state).
- Review: CodeRabbit 2 rounds, 17 responses posted, fresh on merge HEAD with no
  actionable comments.
- Lifecycle: full phased compliance init→finalize through managing skills with
  handshake/boundary captures; no ledger file hand-edited after init. Plan
  archived, worktree cleaned, main clean.
- Operator-ordered deviation on record: cuioss-review-bot demoted to optional_bots
  after 5 unanswered re-review triggers (decision logged on-plan);
  required_bots=coderabbit. Silence pattern preserved in the archived plan; the
  plan's process-rule observations went directly to the process-compliance inbox.

## Routing and Merge Behavior

- Merge: merge queue as 6e239a13. cleanup_owed=false — no Watch needed.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-05 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-05 --field pr --value 1527`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-05 --field landing --value landings/PLAN-05.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-05 --field plan_marshall_plan_id --value lessons-pipeline`
- [x] row PLAN-07 → `running` + plan id stamped (evidence: sender message describing
  executed phases + operator paste; launched without prior emit confirmation)
- [x] epic.md queue reconciled; Watch added (cuioss demotion) + Watch added (PLAN-07 hook block)
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator compact` (in-place; invariants ok)

## Follow-Ups

- Inbox lessons-pipeline-001 (landing): reconciled (this report), archived on consume.
- Inbox plan-07-session-identity-001 (finding): absorbed as Watch (PLAN-07 finalize
  aborted at session gate on a transcript-capable target — designed abort, broken hook;
  work preserved: 3 tasks done, 3 commits in plan worktree, nothing pushed;
  operator remedy: marshall-steward hook install, then re-run finalize; pre-existing
  main stash@{0} left for operator disposition).
- Emit: N=2, R=1 (PLAN-07 running) → 1 slot, zero staged candidates — nothing
  emittable; queue holds only the running row. Statement below.
