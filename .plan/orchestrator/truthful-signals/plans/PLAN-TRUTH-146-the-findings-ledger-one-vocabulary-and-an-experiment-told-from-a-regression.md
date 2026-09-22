# PLAN-TRUTH-146: The findings ledger: one vocabulary, and an experiment told from a regression

## Objective

The findings ledger is the shared substrate every other surface in this epic reports through, and it speaks
several dialects: the same word means different things in the findings store, the CI providers, the
retrospective and the orchestrator's landing records. On top of that same ledger, the pipeline cannot tell an
INTENDED red — an experiment — from a regression, so a deliberate failing run is filed as a defect. Merged
because the second is unfixable without the first: an expected-red intent needs a vocabulary to be expressed in.

## Deliverables

11 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: derive the SAME-QUESTION subset, probe feasibility, and settle the two-member remedy.** Establish which fields across the adopters genuinely answer the same question — the only ones a shared vocabulary may unify — and whether the two PLAN-TRUTH-133 members share a remedy. ⛔ Publish the swept population and its size. (PLAN-TRUTH-124 D0 + PLAN-TRUTH-133 D0.)
2. **D1 — One shared verdict vocabulary, one home, and a stated migration for every adopter.** ⛔ A vocabulary with no migration for an adopter is a second vocabulary. (PLAN-TRUTH-124 D1.)
3. **D2 — Severity is TWO fields, because criticality is mutable.** (PLAN-TRUTH-124 D2.)
4. **D3 — The requirements-relevance mark, in the same vocabulary and on the same records.** (PLAN-TRUTH-124 D3.)
5. **D4 — The orchestrator's ground-truth corroboration gets a structured home.** (PLAN-TRUTH-124 D4.)
6. **D5 — `landings/PLAN-NN.json`: the machine record, forward-only.** (PLAN-TRUTH-124 D5.)
7. **D6 — `statistics`: one read seam returning the unified data as a standardized TOON model.** (PLAN-TRUTH-124 D6.)
8. **D7 — The build invocation can declare an expected-red intent, and capture honours it.** (PLAN-TRUTH-133 D1.)
9. **D8 — Surface the pending actionable-findings count at each phase boundary.** (PLAN-TRUTH-133 D2.)
10. **D9 — The barrier's refusal enumerates findings by cause and age.** (PLAN-TRUTH-133 D3.)
11. **D10 — The tests, and they are what makes the vocabulary binding rather than aspirational.** Plus the matched controls for both expected-red directions. (PLAN-TRUTH-124 D7 + PLAN-TRUTH-133 D4.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-124 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-124-one-ledger-vocabulary-clean-slate-so-the-same-word-means-the-same-thing-everywhere.md` § `## Claim Labels` (verify-at-outline)
  - verdict: contradicted | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: no | evidence: Pointer at PLAN-TRUTH-124 Claim Labels: 11 verdicts including FOUR contradicted (indices 0,1,3,6) plus 3 unverifiable. Not yet re-scoped.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-133 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-133-the-findings-pipeline-cannot-tell-an-experiment-from-a-regression.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-133 Claim Labels: 8 top-level bullets but only 7 verdicts (one bullet never settled) and 3 unverifiable.

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` — carried from PLAN-TRUTH-124
- `test/plan-marshall/manage-findings/` — carried from PLAN-TRUTH-124
- `test/plan-marshall/workflow-integration-sonar/` — carried from PLAN-TRUTH-124
- `test/plan-marshall/plan-orchestrator/` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/manage-change-ledger/` — carried from PLAN-TRUTH-124
- `marketplace/bundles/pm-requirements/skills/traceability/SKILL.md` — carried from PLAN-TRUTH-124
- `marketplace/bundles/*/skills/ext-triage-*/` — carried from PLAN-TRUTH-124
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/**` — carried from PLAN-TRUTH-133
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier` — carried from PLAN-TRUTH-133
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — carried from PLAN-TRUTH-133
- `test/plan-marshall/manage-findings/**` — carried from PLAN-TRUTH-133
- `test/plan-marshall/script-shared/**` — carried from PLAN-TRUTH-133

## Dependencies and Sequencing

PLAN-TRUTH-152 CONSUMES the vocabulary this plan builds and must land after it. D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-124-one-ledger-vocabulary-clean-slate-so-the-same-word-means-the-same-thing-everywhere.md` (PLAN-TRUTH-124)
- `PLAN-TRUTH-133-the-findings-pipeline-cannot-tell-an-experiment-from-a-regression.md` (PLAN-TRUTH-133)

## ⭐ FOLDED 2026-09-22 — D8/D9's prose-vs-structured divergence, a third instance

Inbox lesson `2026-09-21-08-003` (relayed via `lessons-handling-26-09-22-01`): `automatic-review` recorded
`outcome: done` while `manage-findings list --resolution pending` returned all 5 of its findings still
pending; one (`6f47cd`, hardcoded paths in `analyze.py`) was never actually fixed. Prose and the structured
ledger diverged and nothing cross-checked them — exactly D8's ("surface the pending actionable-findings
count at each phase boundary") and D9's ("the barrier's refusal enumerates findings by cause and age")
shape. No surface change — `manage-findings/**`, `automatic-review/scripts/`,
`phase-6-finalize/standards/pre-merge-barrier` and `phase-6-finalize/scripts/review_commitments.py` already
declared.

⚠ **Precedent hazard, cross-notice owed.** The 2026-09-15 drain already forwarded a narrower instance of
this same step's behaviour to `review-apparatus` (*"`automatic-review` closed `done` with a refused-
structural reviewer un-triaged"* → `truthful-signals-058.md`). Sent a cross-notice there (below) — if that
epic has since staged the done-vs-pending cross-check, this fold is a duplicate and should retire in favour
of it. The finding this lesson says was never fixed (`6f47cd`) is the same file as a separate 2026-09-21
lesson's residue, already forwarded to `code-intelligence-substrate`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-146-the-findings-ledger-one-vocabulary-and-an-experiment-told-from-a-regression.md"
```

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.
