# WS-03: Carried-Lead Remediation

epic: test-suite-quality
workstream: WS-03

> Workstream charter. Layout and authority contract: see
> `persona-marshall-orchestrator/standards/orchestration-model.md`.

## Charter

The epic was closed 2026-07-24 while carrying fix-plan-needed leads recorded as "out-of-epic".
Reopened 2026-07-25 (operator decision) because deferring known, verified defects is how they
evaporate. This workstream converts the carried leads — plus the related open lessons a full-corpus
scan surfaced — into shippable fix-plans, biased toward larger coherent plans and grouped by disjoint
surface so the retrospective plan can run in parallel with the others.

Every item below was verified genuinely open against the code at head `76c4e39e7` before being staged;
folded-in lessons not yet code-verified are marked "verify at outline" in each spec, honoring the
epic's own enumerate-and-verify discipline (lesson `2026-07-21-22-001`).

## Plans

- **PLAN-07 unit-test-truthfulness** — the epic-native unit-testing residue: the coverage-scope
  denominator decision (never taken), the dead `discover_modules` integration tier + weak assertions
  (RU-7), the RU-4/M4 fixture-consolidation residue, and the "unit-testing in finalize" fold
  (`pre-push-quality-gate` gaining `mypy test` parity). Surface: `pyproject.toml`,
  `test/plan-marshall/integration/discover_modules/`, `phase-6-finalize/pre-push-quality-gate`.
- **PLAN-08 finalize-dispatch-audit-integrity** — the finalize dispatch machinery that fails to emit
  its `[DISPATCH]` audit and the promoted-to-dispatched steps that cannot fire their own nested
  dispatch. Surface: `phase-6-finalize` dispatch mechanics + `automatic-review`.
- **PLAN-09 retrospective-check-correctness** — the `plan-retrospective` checks that produce false
  verdicts (silent passes, miswarnings, dropped findings, overcounts). Surface: `plan-retrospective`
  scripts. **Disjoint from PLAN-07/08 → parallelizable.**

## Sequencing

- PLAN-09 is surface-disjoint from both others and may run in parallel with either.
- PLAN-07 and PLAN-08 both touch the `phase-6-finalize` bundle (07: `pre-push-quality-gate`;
  08: dispatch machinery). Expected file-disjoint, but same skill dir → sequence unless outline
  proves disjoint.
