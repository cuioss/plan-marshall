# PLAN-010: Test-Authoring Standards and Enforcement

epic: test-quality
workstream: WS-01

> **LANDED — historical spec.** This plan executed in the standalone `doc/plans/` cloud lane before the
> epic was ingested into this ledger. The spec below is reconstructed from the archived brief so the
> queue reconciles both ways; the **authoritative verdict** is [`landings/PLAN-010.md`](../landings/PLAN-010.md),
> and the full original brief is [`archive/010-test-authoring-standards-and-enforcement/plan.md`](../archive/010-test-authoring-standards-and-enforcement/plan.md).
> Nothing here is re-emittable — a re-entry against this plan is a new run report in the archive, not a
> re-run of this spec.

## Objective

The repository's test-authoring standards said the wrong thing and nothing checked the right thing:
`persona-module-tester` carried a `~200 lines` module figure that ~75% of the corpus violated and no
guard ever enforced, and a "prefer generated test data over hardcoded literals" phrasing that reads as a
blanket preference in a corpus where most literals **are** the contract. Retire both, state the house
style **B1**–**B10** in the two skills that own test-authoring guidance, and make the mechanical half of
it enforceable by `plugin-doctor`'s `test-conventions` scope.

## Deliverables

1. Retire the `~200 lines` figure; state the 400-line module budget and the behaviour-cluster split
   taxonomy, derived against the corpus's own median rather than invented.
2. Replace the blanket generated-data preference with the universal-contract / literal-is-the-contract
   discriminator, in both skills.
3. State the docstring content rule — present-tense invariant, no incident, PR number or lesson id.
4. State the six arrange / parametrize / argv / budget rules plus one-layer-per-contract, in both skills.
5. Ship four new `test-conventions` analyzer rules at `severity: warning`, each with tests, a
   `rule-catalog.md` row and a `rule-provenance.md` row.
6. Record the Hypothesis-adoption proposal and the per-rule error-flip proposal **without acting** —
   adding a third-party dependency is a user-approval step.

## Claim Labels

- OBSERVED: the `~200 lines` figure is violated by ~75% of the corpus and enforced by nothing — read at
  `marketplace/bundles/plan-marshall/skills/persona-module-tester/standards/testing-methodology.md`
  - verdict: corroborated | checked_at: 00b92fca | by: test-quality/cleanup | rescoped: n/a | evidence: re-read at HEAD 00b92fca: '### Module Budget: 400 lines' stands at persona-module-tester/standards/testing-methodology.md:75, same line as the prior check. Verified by direct read, not by absence-of-diff - the window touches 173 files including many under marketplace/bundles/plan-marshall/skills/
- OBSERVED: no analyzer rule enforces any part of the house style — confirmed by the absence of the four
  rule ids from `_analyze_test_conventions.py` at authoring time
  - verdict: corroborated | checked_at: 00b92fca | by: test-quality/cleanup | rescoped: n/a | evidence: re-read at HEAD 00b92fca: all four RuleDescriptor entries stand at _analyze_test_conventions.py:61-64 (test-module-line-budget, test-helper-module-misnamed, test-module-preamble-boilerplate, test-docstring-historical-prose). Note for the conformance-drift watch: three of the four carry severity='warning', which is the mechanism by which non-conforming new modules land unremarked

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-dev-python/skills/pytest-testing/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-module-tester/**`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` — the analyzers, the
  catalog and the provenance rows
- OBSERVED: `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule*.py` and
  `fixtures/test_conventions/rule*/` — this plan ships the tests for the rules it adds, and this glob is
  **permanently carved out of every reduction slice**
- OBSERVED: `test/pm-plugin-development/plugin-doctor/test_doctor_marketplace_commands.py` — the
  `cmd_test_conventions` cases only
- OBSERVED: `test/pm-plugin-development/plugin-doctor/_plugin_doctor_fixtures.py`

## Dependencies and Sequencing

- Depends on: none — this and PLAN-020 are the epic's two roots.
- Overlaps with: none. May run concurrently with PLAN-020 only.
- Adjacent to: the rest of `test/pm-plugin-development/**`, which is PLAN-080's slice and excludes this
  plan's glob explicitly.

## Hand-Off Command

Not emittable — this plan has landed. See `## Objective` note above.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
