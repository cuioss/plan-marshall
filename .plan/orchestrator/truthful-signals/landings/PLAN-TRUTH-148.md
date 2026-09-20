# Landing Analysis: PLAN-TRUTH-148 — The finalize-step contract, declared surfaces, the dispatch seam, and a self-review that decides its own close

epic: truthful-signals
workstream: WS-01
pr: #1488 (https://github.com/cuioss/plan-marshall/pull/1488)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against
> ground truth — a pasted or inbox claim is a lead, never a fact.

## Verification performed

- PR #1488 corroborated first-party via `ci pr view`: `state=merged`, `merge_commit_sha=db0ae63464f1…`
  (found via `ci pr list --head feature/plan-truth-148` since the landing message's own `pr=#1488` claim
  was not trusted on its own).
- Inbox landing message `plan-truth-148-064.md` cross-checked: `landing-check` reports `complete: true`.

## Deliverable Fidelity vs Spec

11/11 deliverables landed per the landing-facts block. This plan's own subject — declared surfaces, the
dispatch seam, and a self-review that decides its own close — was executed as an 11-round, 62-finding
self-review sweep against its own prior work (rounds 2-10), essentially the plan auditing itself against
its own thesis while it built the fix. Every one of the 54 self-review findings this landing generated
(candidate-lessons 008-053) carries a `resolution` of `fixed`, `taken_into_account`, or `rejected` — none
reached this landing as open work; the plan closed its own loop before shipping.

## Metrics and Anomalies

- Tokens: 7,491,732 (landing-facts `total_tokens`).
- Wall time: 173,096s (~48h5m) elapsed (landing-facts `total_wall_seconds`).
- Anomaly, on-theme and severe: `pre-submission-self-review` fired 15 times, 11 `loop_back`, reaching
  `loop_back_iteration: 13` — 85% of `6-finalize`'s measured token cost, 29% of the plan's total. No
  operator turn fell inside any of the 13 loop-back iterations. Explicit recurrence of PLAN-TRUTH-089's
  already-recorded archetype (81% of a 13.9M run, self-review firing 19×). This plan's own deliverables 8
  and 9 shipped a partial fix (verifier independence, stop-question-of-the-verifier) but "neither could
  govern the finalize run that shipped them" — the fix is unobserved under its own load. Folded into
  PLAN-TRUTH-147.
- Anomaly: the build-time oracle recorded 0 builds (`analyze-logs build_time.build_count: 0`) while the
  plan made 96 `pyproject_build` calls totalling 41,041,370ms — 73.97% of all script time, the largest
  cost-rollup entry by 7×. Same archetype as the historically-recorded "build-recording surfaces blind"
  defect. Folded into PLAN-TRUTH-150 with a freshness-gate consequence noted (an empty ledger is
  indistinguishable from `default:push`'s `worktree_mutated` stale route).
- Anomaly: 17 script invocation failures logged (10 unique, 8 components) — a strong, well-evidenced
  instance of the epic's already-standing verb-paraphrase Watch (W-1483-b). Corroborated independently the
  same day by PLAN-TRUTH-157's own landing (6 more) and by a review-apparatus transfer from PLAN-PR-065
  (10 more + a distinct executor-registration defect). Population is now well past the threshold the Watch
  named as its blocker — **staged as PLAN-TRUTH-162.**

## Routing and Merge Behavior

- Merge: squash-merged via the merge queue at `db0ae6346`.
- No rebase conflicts or re-verify signals reported.

## Candidate-Lesson Dispositions (Step 5b) — 63 messages, summary

Given the volume, dispositions are grouped by pattern rather than enumerated per message (each still
carries its own decision-log line):

| Cluster | Messages | Disposition |
|---|---|---|
| Self-review loop-cost / no convergence signal | 001 | Fold → PLAN-TRUTH-147 |
| Post-merge empty-diff false FAIL | 002 | Fold → PLAN-TRUTH-152 |
| Build-time oracle blind to 96 real builds | 003 | Fold → PLAN-TRUTH-150 (surface += manage-change-ledger) |
| Outline declared-intent vocabulary gap (gate-dependent files) | 004 | Fold → PLAN-TRUTH-151 |
| Per-step token record gap (13 of 16 `no_evidence`) | 005 | Fold → PLAN-TRUTH-149 |
| Finalize dispatcher composes plan-retrospective's prompt body wrong (`--iteration`, `WORKTREE`) | 006 | Fold → PLAN-TRUTH-149 |
| Verb-paraphrase / invented-flag population (17 failures) | 007, 055–061, 063 | **Staged → PLAN-TRUTH-162** (evidence) |
| Self-review misreads a coarse roster label as blocking every sub-step | 008 (dup: 013) | **Promoted** — new lesson `2026-09-15-06-001` |
| Stale-doc-pointer / already-fixed self-review artifacts (all `resolution: fixed`/`rejected`) | 009,010,011,012,014–053 (except 048) | Discarded — recurrences of already-tracked archetypes (`2026-09-05-16-001` pointer-not-restatement; WS-10 doc-contract-divergence; derive-completeness-never-assert-it), all self-resolved within this plan's own run, nothing owed |
| Hardcoded roster mirroring a live dispatcher set | 048 | **Promoted** — new lesson `2026-09-15-06-003` (combined with `plan-truth-157-027`) |
| Build wrapper misclassifies a 15s timeout as `argparse_rejection` | 062 | Fold → PLAN-TRUTH-150 |
| `automatic-review` closed `done` with a refused-structural reviewer un-triaged | 054 | Forwarded → `review-apparatus` |

## Reconciliation Actions

- [x] row `status` → `shipped`, `pr` → `1488`, `landing` → `landings/PLAN-TRUTH-148.md`
- [x] `plan_marshall_plan_id` already `plan-truth-148`
- [x] epic.md queue reconciled from status.json
- [x] 3 corpus lessons promoted (2 shared with PLAN-TRUTH-157's landing, see that report), 1 new spec
      staged (PLAN-TRUTH-162, shared), 6 folds, 1 finding forwarded to review-apparatus
- [x] resume_anchor updated; both derivable blocks regenerated via `compact`

## Follow-Ups

- PLAN-TRUTH-147 gains fresh evidence that its own D6/convergence-signal fix needs observation under a
  real loop-back-heavy run — not yet exercised.
- PLAN-TRUTH-162 (new): the verb-paraphrase/invented-flag fix (uniform canonical-verb hint) is now
  population-backed across three independent landings in a single day.
