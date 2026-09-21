envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules
epic=process-compliance
kind=finding
created=2026-09-19T10:25:19Z

# PLAN-180 carve-1 landing note: D5 shipped, 9-deliverable split, lifecycle shortcut disclosed

## Outline-verification verdicts (implementing source, HEAD at run time)

- OBSERVED hoisted base argv (lesson 2026-09-03-07-007): fix PRESENT in
  `test/plan-marshall/build-server/test_build_execute_routing.py:64-81`
  (parser-derived base on `--plan-id` only, derivation modelled by assignment,
  mutual-exclusion documented). Rule prose NOT in inventoried standards
  (`hoisted base argv` search: count 0). Staged as carve-2.
- OBSERVED prune-deletes-session-tmp (lesson 2026-09-03-22-001): fix PRESENT in
  `test/plan-marshall/build-pyproject/test_build_cmd_coverage.py:42-67`
  (single shared capture helper stubs `_prune_basetemp_roots`). Rule prose NOT
  stated in any standard (lesson says so itself). Staged as carve-2.
- HYPOTHESIS (CLI-validated argv + scoped pruning + seam-pinned mirrors hold the
  suite honest): CORROBORATED for the argv and pruning arms (fixes present as
  above); mirrors arm confirmed as rule-gap (`seam-pinned mirrors` search:
  count 0). Staged as carve-3.
- D3 tool-default invalidation (lesson 2026-09-14-05-006): remediated prose
  PRESENT (`pyproject.toml:147-171` states both outcomes; mechanism control
  described). Mechanism TEST (documented behaviour matches configured value)
  absent. Staged as carve-2.
- D7 skills-root patch (lesson 2026-09-03-17-001): fix PRESENT
  (`test_platform_runtime_bootstrap.py:33-55` patches `__globals__`); rule prose
  PRESENT (`testing-pytest.md` patch-the-namespace section). Done, no change.
- D8 single registration (lesson 2026-09-17-15-001): fix PRESENT
  (`test_fetch_findings_cli.py:12`, `test_fetch_findings_vocabulary.py:10`
  import `sonar_mod` from core). Rule prose absent. Staged as carve-3.
- D6 oversized-split carving (lesson 2026-09-18-11-001): process guidance, no
  code. Applied TO THIS PLAN (see below).

## Shipped carve-1 (D5 fixture-yield wording, behaviour cluster)

- Rule prose added: `marketplace/bundles/pm-dev-python/skills/pytest-testing/standards/testing-pytest.md`
  § Fixture docstrings (no citations, present tense).
- Guard test: `test/pm-dev-python/pytest-testing/test_fixture_yield_docstrings.py`
  (AST detector + matched negative/positive controls + whole-tree assertion with
  population guard; no skips, no runtime-derived parametrize).
- 10 live violations fixed across 9 files (return-wording; one-word synonym
  swaps in two rationale sentences, scope documented as whole-docstring per the
  lesson title).
- Verification: `module-tests pm-dev-python` 36/36 green;
  `quality-gate pm-dev-python` green; `module-tests` green for
  tools-file-ops (202), manage-status (825), tools-integration-ci (490),
  script-shared (1445), tools-script-executor (483). No new skips.

## Split-guard issue (filed, not just noted)

PLAN-180 carries 9 deliverables. The orchestrator scope-bloat guard
presumptively splits specs approaching ~6 deliverables. This run applied the
spec's own D6 rule to itself: carve-1 (D5) ships now; carves 2-4 staged:
carve-2 (D1/D2 argv+prune rules with negative controls, D3 mechanism test),
carve-3 (D4 mirror rule, D8 registration rule), carve-4 (D9 basetemp
relocation, separate message). Request: confirm the carve sequence or re-scope.

## Lifecycle-shortcut disclosure

Implementation ran inline on the main checkout, not through phases 2-6 with a
worktree and feature branch. Plan record `test-fidelity-rules` exists at 1-init
(request.md ingested from the staged spec via the file-pointer branch). Phases
2-refine/3-outline/4-plan were performed as inline outline-verification above,
not as dispatched phases; no execution envelope, no worktree materialization.
Rationale: single behaviour-cluster carve sized for one turn with full
verification. The shortcut is disclosed here rather than silently normalized.
Next carves should either run the full lifecycle or record an explicit waiver.
