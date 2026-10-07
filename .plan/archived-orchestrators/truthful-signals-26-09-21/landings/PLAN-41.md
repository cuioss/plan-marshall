# Landing Analysis: PLAN-41 — phase-1-init single-source spec ingestion

epic: truthful-signals
workstream: WS-01
pr: #991 (https://github.com/cuioss/plan-marshall/pull/991) — squash-merged, f7c4130cb

> Landing record for one shipped plan. Written by the `analyze` verb after
> corroborating the operator's pasted landing narrative against ground truth
> (the merged diff at f7c4130cb, PR CI state).

## Deliverable Fidelity vs Spec

Spec staged 6 deliverables (5 planned + 1 loop-back). All 6 shipped; corroborated
against the merged file set.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 gate — ingestion seam decided (phase-1-init only) | shipped-as-specified | phase-1-init/SKILL.md +54, standards/workflow.md +19 |
| D2 — two-branch file-pointer ingestion + narrative rebind + workflow.md Boy-Scout | shipped-as-specified | manage-plan-documents/scripts/_cmd_request.py (+19 via `--body-file` seam); narrative rebind so recipe-match/aspect-classify score the brief |
| D3 — fail-loud abort (spec_pointer_unreadable) + body_file_unreadable decode guard | shipped-as-specified | _cmd_request.py decode guard; SKILL.md abort path |
| D4 — 4-case regression at --body-file seam (+ invalid-UTF-8) | shipped-as-specified | test_request_body_file_ingestion.py +214 |
| D5 — orchestrate.md + analyze.md spec_body inline retired (5 sites → 0) | shipped-as-specified | analyze.md −/+6, orchestrate.md ±11 in the merged diff |
| TASK-006 — CodeRabbit-caught D3 gap: classify-by-syntax-before-existence | shipped-as-specified (loop-back) | pointer predicate no longer requires file to exist before classifying; folded into test_request_body_file_ingestion.py |

## Metrics and Anomalies

- Tokens: 2.6M total (operator report)
- Duration: 2h12m worked
- Anomalies: two fix cycles at Q-Gate (outline hardened twice); one finalize loop-back
  (TASK-006) after CodeRabbit found a genuine D3 defect that both the Q-Gate and
  pre-submission-self-review missed — the pointer predicate required the file to *exist*,
  so a missing spec silently fell through to the plain-text branch, defeating fail-loud.
  Two tooling frictions, both non-blocking and operator-documented: (1) build wrapper
  stamped `worktree_sha` over the main-checkout root (post-move-back bookkeeping mismatch,
  not drift) → overridden via push.md `--force` after confirming 12384 tests genuinely
  green; (2) marshalld mis-resolved the worktree → handled via `--project-dir` +
  stop→in-process→restart.

## Routing and Merge Behavior

- Review: CodeRabbit — 3 actionable, all fixed (75% resolved-as-fixed, 1 reviewer);
  earned its keep (caught the D3 fail-loud gap the internal gates missed).
- CI/merge: 11 checks green (verify/gate/verify·conclusion, Sourcery, CodeRabbit,
  dependency-review, OpenCode generation gate, CLA); squash-merged via merge queue.
  No rebase conflicts. Disjoint as predicted from PLAN-42/43/44 (all already shipped).

## Reconciliation Actions

- [x] status.json `plans[]` entry updated → shipped, pr 991, landing landings/PLAN-41.md
- [x] epic.md queue reconciled from status.json
- [x] Watch/candidate updates: PLAN-41 unblocks PLAN-53 (needs D4 re-ground now), PLAN-55/56 (after PLAN-41), and is a coordination dependency for PLAN-57
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- Cross-link confirmed (spec D-note): phase-1-init reading the spec also feeds the lane
  router the TRUE footprint — the `implement <spec-file>` LIGHT-route scope mis-estimate
  (lesson 2026-07-21-17-003) is now addressable; PLAN-57 (lane-router scale-blind) remains
  necessary-not-sufficient on top of this.
- Two new lessons recorded (2026-07-23-10-002, -003) — CodeRabbit-caught fail-loud gap +
  non-UTF-8 read guard.
- PLAN-49 drain-gate: 6 of 8 gating plans now shipped (41/42/43/44/45/46); still gated on
  47 + 48.
