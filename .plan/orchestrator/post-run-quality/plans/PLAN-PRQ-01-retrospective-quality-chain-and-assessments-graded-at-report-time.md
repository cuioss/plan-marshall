# PLAN-PRQ-01: The quality chain has no score, and an assessment is graded at report time

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

**TRANSFERRED 2026-09-17 from `truthful-signals` PLAN-TRUTH-152**, which is itself the merge of
PLAN-TRUTH-123 (the quality chain) and PLAN-TRUTH-130 (assessments graded at report time). The source
spec and both of its superseded sources stay on disk in that epic as the audit record and are the
authority for every carried claim:

- `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-152-the-retrospective-quality-chain-and-assessments-graded-at-report-time.md`
- `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-123-the-quality-chain-has-no-score-and-a-disabled-gate-is-indistinguishable-from-a-clean-one.md`
- `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-130-an-assessment-is-read-at-report-time-and-grades-a-correct-action-as-a-violation.md`

The source row is retired in `truthful-signals` with a pointer here. ⛔ It is `parked` rather than
`transferred` because `queue --transition` cannot write that status — see the epic's `## Decisions`.

## Objective

**The post-run quality chain produces a verdict with no score and no stated basis, so a gate that was
DISABLED is indistinguishable from one that ran and found nothing — and an assessment recorded at outline
is graded at report time against a tree that has moved since, so a correct action is reported as a
violation.** Both halves are the same failure at different tiers: a judgement published without the state
it was computed against.

## Deliverables

11 deliverables carried from the source spec, within the epic's operator-set ceiling of 12. **D0 is a
gate: nothing downstream starts until every carried claim is re-grounded at HEAD** — the sources were
authored before PR #1488, #1494 and #1501 landed in this area.

1. **D0 — GATE: re-ground at HEAD; derive the mechanism population, settle the disposition→point mapping
   against the real corpus, and enumerate every surface that grades an assessment.** Publish each
   population and its size.
2. **D1 — The coordinator: ONE script, one entry point, two consumers.**
3. **D2 — The scoring core: signal presence first, yield second, and the two are NEVER folded into one
   number.** Folding them is what makes a disabled gate read like a clean one.
4. **D3 — Consumer 1: the corpus quality report, and the first run's README complement.**
5. **D4 — Consumer 2: augment the per-plan `plan-retrospective` output.**
6. **D5 — An assessment carries an effective-from instant, and the report joins on it.**
7. **D6 — Supersession is recorded, not overwritten.**
8. **D7 — An operator override is distinguishable from drift, at the report.**
9. **D8 — Close the outline write-back gap.**
10. **D9 — The tests, and they are the deliverable that outlives the rest.** Plus matched controls for
    every assessment-grading member.
11. **D10 — CONSUME the unified ledger vocabulary — do not build it.** The source recorded that its
    D8-class vocabulary work MOVED to `truthful-signals` PLAN-TRUTH-146. ⛔ That plan stays in that epic;
    this one consumes its output and must not re-implement it. If PRQ-01 launches first, D10 states the
    dependency rather than filling it.

## Claim Labels

⛔ Every claim below is a POINTER at the source spec that authored it, which is on disk at the path in
`## Provenance`. Re-derive each from the source's own `## Claim Labels` section at HEAD, never from this
restatement — D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-123 still holds at HEAD — confirm/refute at
  that spec's `## Claim Labels` (verify-at-outline)
  - verdict: contradicted | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: yes | evidence: PLAN-TRUTH-123 carries persisted verdicts (checked_at 66320e70d): 18 corroborated/3 contradicted(rescoped:yes)/2 unverifiable -- not every premise holds. D0 corrected to read those verdicts rather than re-derive.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-130 still holds at HEAD — confirm/refute at
  that spec's `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: PLAN-TRUTH-130 carries persisted verdicts: 5 unverifiable (4 from a removed plan dir, evidence base gone), 2 corroborated. Surviving structural claim (add_assessment lacks effective-from field) grounds D5 directly; treat -130's measurements as unrecoverable evidence, not facts to re-check.
- OBSERVED: the transfer changed no deliverable's content. The 11 above are the source's D0–D10 verbatim
  in substance; only the epic, the workstream and this provenance framing differ. Re-read the source to
  confirm before scoping.

## Expected Surface

Carried from the source spec, which derived it through `epic_spec_parser` as the union of its two
superseded sources — not retyped from memory.

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/`
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py`
- `marketplace/bundles/plan-marshall/skills/manage-findings/**`
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/**`
- `marketplace/bundles/plan-marshall/skills/manage-references/**`
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
- `.claude/skills/audit-archived-plan-retrospectives/SKILL.md`
- `.claude/skills/audit-archived-plan-retrospectives/checks/`
- `doc/analyzis-cloud-plan/`
- `test/plan-marshall/plan-retrospective/`
- `test/plan-marshall/plan-retrospective/**`
- `test/plan-marshall/audit-archived-plan-retrospectives/`
- `test/plan-marshall/manage-findings/**`

## Dependencies and Sequencing

- Depends on: none. D10 CONSUMES `truthful-signals` PLAN-TRUTH-146's vocabulary work — a cross-epic
  dependency **no disjointness gate can see**, since the two live in different ledgers.
- ⛔ Never pair with PLAN-PRQ-02 (shared `plan-retrospective/scripts/`). At `parallelization_scope: 1`
  that is automatic.
- ⚠ Shares `.claude/skills/audit-archived-plan-retrospectives/**` with PLAN-PRQ-03 — sequence.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-01-retrospective-quality-chain-and-assessments-graded-at-report-time.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
