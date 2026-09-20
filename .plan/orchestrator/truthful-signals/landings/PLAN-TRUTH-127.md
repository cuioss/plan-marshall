# Landing Analysis: PLAN-TRUTH-127 — The archived record says a phase is still running, and the closer can only close one

epic: truthful-signals
workstream: WS-01
pr: #1483 (https://github.com/cuioss/plan-marshall/pull/1483)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against
> ground truth — a pasted or inbox claim is a lead, never a fact.

## Verification performed

- PR #1483 corroborated first-party via `ci pr view`: `state=merged`, `merge_commit_sha=c38342609a1af…`
  (matches both the operator paste's `c38342609` and the inbox landing's `pr=#1483`/`merge_state=merged`).
- Inbox landing message `plan-truth-127-005.md` cross-checked: `landing-check` reports `complete: true`
  (all 9 required `landing-facts` keys present with real values).
- A fifth, independently-arrived inbox message (`review-apparatus-038.md`, a cross-epic transfer from
  `review-apparatus` bundling 5 non-charter findings from `plan-pr-046`'s own landing, PR #1477) was
  drained in the same pass — see Candidate-Lesson / Finding Dispositions below.

## Deliverable Fidelity vs Spec

The staged spec named 6 deliverables (D0–D5). The landing reports 7/7, but its own residue corrects that:
deliverable 1 (the in-progress-phase survey) grades `missed` on TASK STATUS (TASK-001 `infeasible`,
replacement TASK-012 `blocked`) while its artefact — finding `9b6297`, a full three-cohort census — exists
and was taken at finalize. The task-table and findings-store verdicts disagree, and the epic accepts the
landing's own framing: the deliverable is satisfied, the task-status grading is the defect (itself
on-theme for this epic).

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D0 — derive the condition, widen the population, honour the no-repair decision | shipped-as-specified | Population re-derived three times during the run (30/4 → 39/6 → 46/7, all `coverage: complete`); the four pre-existing records deliberately left unrepaired per the standing operator decision |
| D1 — `cmd_archive` closes every open phase or refuses, `current_phase` reaches `complete` | shipped-as-specified | This plan's own archive returned `phase_closure: complete` |
| D2 — a re-opened phase that ends without completing must not stay open silently | shipped-as-specified | Deliverable 3 in the landing ("Consume the loop-back re-entry marker at archive") |
| D3 — split the unreadable/removed-worktree refusal from the dirty one | shipped-as-specified | Deliverable 4 in the landing |
| D4 — reconcile the two ledgers | deferred, named not swept | Landing residue: "Deferred, not done: the status.json-to-metrics cross-ledger reconciliation. PLAN-TRUTH-124 has not landed" — cross-referenced to PLAN-TRUTH-146 below (see Follow-Ups) |
| D5 — population-derived tests with matched controls | shipped-as-specified, expanded | Landing deliverable 6 ("assert on an in-fixture population that no archive leaves a phase open") plus deliverable 7 (a new main-anchored per-cohort census verb — the D0(b) widened-population ask made durable) |

## Metrics and Anomalies

- Tokens: 3,537,140 across six phases (landing-facts `total_tokens`); the retrospective grades this
  against the `multi_module + bug_fix` error anchor (2.0M/150min) and attributes the overage to run SHAPE
  (three outline passes, two manifest re-composes, three review rounds), not a runaway envelope (max phase
  share 0.29).
- Wall time: 34h32m elapsed / 4h16m worked (landing-facts `total_wall_seconds=124355`).
- Anomaly (self-reported, on-theme, twice): CodeRabbit found two Majors and a Medium **inside this plan's
  own fix** for the exact defect class the plan exists to remove — a census verb that silently discarded
  unreadable entries while publishing `coverage: complete` (`af0a4d`), and an `open_phase_count` that
  counted plans instead of phases (`9e4ff2`). Neither reached the deterministic gates (`pre-push-quality-
  gate`, `plugin-doctor`, CI all green while both were live); `pre-submission-self-review` examined 109
  candidates and matched no structural check. Captured as a candidate-lesson (Promoted) proposing a
  self-application pass.
- Anomaly: a withdrawn finding (`4adc50`) — compared 162 executor-mapped scripts against 156 in
  `marketplace/bundles/`, called six of them orphans; the 162 actually counts 156 marketplace + 6
  project-local scripts the 156-count never included. Two populations compared as if they were one; cost
  a deferred task (TASK-012) on a hazard that did not exist. Captured as a candidate-lesson (Promoted).

## Routing and Merge Behavior

- Review: CodeRabbit — 7 actionable, 7 fixed, 0 rejected across 2 rounds, including two Majors and a
  Medium found inside this plan's own fix. `cuioss-review-bot` reported clean on both HEADs, but that
  zero is not comparable to CodeRabbit's non-zero: its Guide is an `issue_comment` the counting rule
  scores as meta, and the contentless filter drops a clean Guide before it becomes a finding, so in that
  store a clean pass and silence are indistinguishable. `sourcery-ai` refused throughout on its 7-day
  budget.
- CI/merge: merged via merge queue at `c38342609`. No rebase conflicts or re-verify signals reported — no
  parallelization-consequence correction needed at this landing.
- Two review-apparatus-shaped measurement defects surfaced by the retrospective (status-summary carve-out
  matching the wrong field; a round-2 Medium scored meta for arriving as a comment reply) — forwarded to
  `review-apparatus` as `truthful-signals-057.md`, not owned here.
- Declared coverage gap: `plugin-doctor` ran SCOPED, so its cross-skill rule class was not gated — a
  counterpart skill outside the four changed directories could read green locally and red at whole-tree
  CI. Recorded as a Watch below.

## Candidate-Lesson / Finding Dispositions (Step 5b)

Four `candidate-lesson` messages from `plan-truth-127` plus one cross-epic `finding` transfer from
`review-apparatus` (5 bundled sub-items) were dispositioned:

| Message | Title | Disposition |
|---|---|---|
| `plan-truth-127-001.md` | Name the population beside every count a drift verb publishes | **Promote** — new lesson `2026-09-13-20-002` (`plan-marshall:marshall-steward`) |
| `plan-truth-127-002.md` | Add a self-application pass when the plan's subject is a defect archetype | **Promote** — new lesson `2026-09-13-20-003` (`pm-plugin-development:ext-self-review-plan-marshall`) |
| `plan-truth-127-003.md` | Put the could-not-look discriminator in the payload, never only in a docstring | **Promote** — new lesson `2026-09-13-20-004` (`plan-marshall:plan-retrospective`), covering instances 1 (build_time) and 3 (`UNTOUCHED_PHASE_STATUSES`). Instance 2 (review-body carve-out) forwarded to `review-apparatus` per the plan's own routing note. |
| `plan-truth-127-004.md` | A missing freshness-reconciliation record is reported as un-built source drift | **Stage** — new spec `PLAN-TRUTH-158`, queue row appended |
| `review-apparatus-038.md` item 1–2 | Post-merge empty-diff graded FAIL; `permission-prompt-analysis` empty-list design question | **Fold** into PLAN-TRUTH-152 |
| `review-apparatus-038.md` item 3 | `pre-submission-self-review` has no convergence signal | **Fold** into PLAN-TRUTH-147 |
| `review-apparatus-038.md` item 4 | Finalize never calls the scope-drift detector it already has | **Fold** into PLAN-TRUTH-145 |
| `review-apparatus-038.md` item 5 | Verb-paraphrase argparse rejections remain dominant | **Absorb as Watch** — sender's own medium confidence, self-flagged as needing the rejection population before action |

All four folds are presumed to add no new Expected Surface (existing directory/recursive-glob entries or
already-listed files cover the cited components); none were independently re-verified against the exact
files in this checkout, consistent with the forwarding messages' own "leads, not instructions" framing.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-127 --status shipped`
- [x] row `pr` stamped `1483`
- [x] row `landing` stamped `landings/PLAN-TRUTH-127.md`
- [x] row `plan_marshall_plan_id` already `plan-truth-127` (stamped in an earlier session)
- [x] epic.md queue reconciled from status.json
- [x] Open Defects added: `353313` (re-entry marker reports zero re-entries on a run with four — recurrence
      against shipped PLAN-TRUTH-101); `ac1774` (`manage-lessons consult` unrunnable once a plan directory
      moves into its worktree)
- [x] Watches added: plugin-doctor scoped-gate coverage gap; verb-paraphrase argparse-rejection rate
      (needs population before action)
- [x] Deferred cross-ledger reconciliation cross-referenced to PLAN-TRUTH-146's sequencing
- [x] 3 corpus lessons promoted, 1 new spec staged (PLAN-TRUTH-158), 3 folds (PLAN-TRUTH-152, -147, -145),
      1 finding forwarded to review-apparatus, 1 item absorbed as a Watch
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- PLAN-TRUTH-158 (new, staged): push.md's freshness-reconciliation refusal must report the observation,
  not an inferred cause, when no reconciliation record names the live HEAD.
- PLAN-TRUTH-146 gains no direct edit this landing, but D4's deferred cross-ledger reconciliation is
  sequenced against it (PLAN-TRUTH-124, which PLAN-TRUTH-146 superseded, owns the verdict vocabulary).
- 3 corpus lessons promoted (drift-verb population labeling; self-application pass for defect-archetype
  plans; could-not-look discriminators in payload).
- Open Defects `353313` and `ac1774` stand until a spec is staged for either.
