# PLAN-09: Plan-store access contracts

epic: process-compliance
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-09-store-access.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Close the remaining plan-store access contradictions after PLAN-03 shipped the sanctioned
spec-body read path (`corpus read`). Six independent runs hit the same wall: three rules
govern one action (AGENTS.md scripts-only `.plan/` access vs the orchestrator read
carve-out vs the Enforcement write boundary) with no script-mediated path to a queued
inbox body and no sanctioned plan-side write path into the epic inbox. This plan adds
the queued-inbox body-read verb, documents the plan-side inbox write path, and records
the AGENTS.md precedence ruling — so rule-following is structural rather than disciplinary.

## Deliverables

1. Queued-inbox body-read verb (`orchestrator.py inbox read-body` or equivalent):
   main-anchored, read-only, bare-filename `--message` with the same traversal refusals
   as `corpus read`, plus canonical SKILL block and tests.
2. Plan-side inbox write path: document the existing sanctioned mechanism a plan uses to
   file into its epic inbox (`orchestrator inbox write`: target derived from slug +
   sender id; no caller-supplied output path), with a negative test proving a plan
   cannot reach any other ledger path.
3. AGENTS.md precedence ruling: record the three-rules-one-action resolution
   (scripts-only vs read carve-out vs write boundary) so the next run has a compliant
   path that covers the use case instead of a forced violation.
4. Regression tests for the new verb (refusal classes, read-only snapshot) and docs.

## Claim Labels

- OBSERVED: three rules govern one spec-body read with no script path before PLAN-03, forcing a direct Read in six independent runs — read at `.plan/orchestrator/process-compliance/inbox/compliant-paths-001.md` § Observation/Forced violation (6th instance; five folded predecessors named)
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite (compliant-paths-001 inbox); multi-run history not checkable at HEAD
- OBSERVED: contradictory `.plan/` access rules forced a violation either way with no spec-body verb exposed — read at `.plan/orchestrator/process-compliance/inbox/phase-gates-003.md` § body
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite (phase-gates-003 inbox body); normative premise needs outline
- OBSERVED: `corpus read --slug --plan` shipped in PLAN-03 (PR #1542) and resolves the spec-body half — read at `.plan/orchestrator/process-compliance/landings/PLAN-03.md` § body
  - verdict: corroborated | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: orchestrator.py cmd_corpus_read present at :2965
- HYPOTHESIS: no compliant read path exists for queued orchestrator inbox bodies from a plan context — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` § `inbox read` subparser (verify-at-outline; forwarded note from `plan-140-slice-060-b0-001.md`)
  - verdict: contradicted | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: yes | evidence: inbox write subparser exists at :5209 and emit-landing writes via orchestrator inbox write; spec re-authored to document-not-build
- OBSERVED: plan-side inbox filing EXISTS via `orchestrator inbox write` (target derived from slug + sender id, no caller-supplied output path) — read at `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` § `inbox write` subparser (re-scoped 2026-09-21: the cleanup re-grounding refuted the no-write-path premise; the remaining gap is discoverability of that path, the read-body verb, and the precedence ruling)
  - verdict: corroborated | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: no read-body subparser in orchestrator.py inbox actions; landing-check at :5410 only
- Verify-first clause: the consuming phase settles both HYPOTHESIS clauses against the implementing source before scoping — refutation loops back to re-scope (e.g. a write path already exists and only needs documenting)

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `cmd_corpus_read` precedent for the new verb
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — canonical invocation block to extend
- OBSERVED: `AGENTS.md` — Hard Rules precedence ruling to record
- OBSERVED: `test/plan-marshall/plan-orchestrator/` — regression tests live here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` § `inbox write` subparser — existing plan-side filing path to document (re-scoped 2026-09-21)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` § `inbox read` subparser — exact seam for the read-body verb (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none (PLAN-03 shipped; this builds on its seam)
- Overlaps with: PLAN-03 surfaces (shipped, no live collision); PLAN-08 (shared orchestrator surface area — sequence, do not parallelize)
- Adjacent to: `manage-files` / `manage-plan-documents` (plan-scoped; stay untouched — this verb is orchestrator-scoped)

## Folded inbox material (same act)

- `phase-gates-003.md` (finding): contradiction report — co-head of this spec
- `compliant-paths-001.md` (finding): precedence gap, 6th instance — co-head of this spec
- `test-fidelity-rules-follow-up-005.md` (finding): inbox write-path verb — folded; expected surface unchanged by this fold beyond the verb this spec already stages (recorded explicitly)
- `plan-140-slice-060-b0-001.md` (finding): queued-body read path — absorbed as cross-ref (foreign epic test-quality owns the original); this spec is the home if test-quality does not stage it

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-09-store-access.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
