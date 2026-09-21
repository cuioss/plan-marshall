# PLAN-07: Unit-Test Coverage & Gating Truthfulness

epic: test-suite-quality
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the hand-off contract.

## Objective

Close the epic-native unit-testing residue that shipped as watches rather than fixes: make the suite's
coverage denominator honest, resolve the dead `discover_modules` tier that misled a plan, and give the
finalize gate the same type-check reach as CI so a green local gate means a green CI. Every item is
either a carried epic watch or a verified-open lesson in the epic's own domain.

## Verified-open inputs (checked at head `76c4e39e7`)

| Item | Evidence |
|------|----------|
| Coverage-scope denominator | `pyproject.toml:157` `source = ["marketplace/bundles"]` — `build.py`, `marketplace/targets/**`, `.claude/**` contribute 0 statements though ~342 tests exercise them. The widen-or-document decision was assigned to PLAN-05 but never taken |
| RU-7 dead tier | `test/plan-marshall/integration/discover_modules/{test_gradle_discover_modules_integration,test_maven_discover_modules}.py` exist with **zero `test_*` functions**; resources point at non-repo clones. Lesson `2026-07-21-16-001` |
| `pre-push-quality-gate` CI-parity gap | Lesson `2026-07-24-13-001` — the gate runs bundle `quality-gate` (production `mypy`) + `module-tests` but never `test-compile` (`mypy test`), so test-tree type errors pass locally and fail only at CI |
| RU-4/M4 residue | PLAN-02 deferred M4 (build-backend fixture consolidation) with three out-of-scope fixture families named; no filed lesson — **verify at outline**, then action or formally close |

## Deliverables

1. **Coverage-scope decision — take it, do not defer it again.** Decide widen-vs-document for the
   `[tool.coverage.run] source` denominator. If widening: extend `source` to the untracked-but-tested
   surfaces (`build.py`, `marketplace/targets/**`, and any others the 342-test enumeration names —
   **enumerate them, do not assume the list**), and record that the headline coverage number moves
   (annotate the discontinuity for the epic trend). If documenting: record the rationale in
   `pyproject.toml` and `doc/developer/` so the scope is a stated choice, not an accident. Either way
   the outcome is a *taken decision*, which is the deliverable.
2. **RU-7 dead tier — delete-or-revive (a real decision, per the lesson).** Either delete
   `test/plan-marshall/integration/discover_modules/` outright, or revive it with in-repo fixture
   projects so it is CI-runnable. Leaving it as coverage-that-does-not-exist is explicitly the worst
   option. If revive is chosen and it grows large, split it to a follow-up and delete-for-now.
3. **RU-7 weak assertions — strengthen, do not prune.** The four named unit assertions
   (`test_gradle_stats_file_counts`, `test_gradle_stats_readme_in_paths`,
   `test_gradle_module_has_commands`, `test_gradle_discover_sources`) each drive a structurally
   distinct fixture; assert on concrete discovered values, not non-emptiness. This is a separate call
   from deliverable 2 per the lesson.
4. **`pre-push-quality-gate` gains `mypy test` parity (the unit-testing-in-finalize fold).** Add the
   test-tree type-check (`test-compile` / `mypy test`) to the local gate so it matches CI's `verify`
   chain, closing the false-local-green class (invalid test package names, un-propagated contract
   changes in out-of-footprint test files). Confirm it runs per the architecture-resolved executor and
   does not double-run production `mypy`.
5. **RU-4/M4 residue — verify then resolve.** Confirm at outline whether the deferred M4 build-backend
   fixture consolidation is still open; if so, either land it or record an explicit closure rationale.
   Do not carry it as an indefinite watch again.

## Lessons consumed — retire from the global store on landing

This plan RESOLVES the following lessons; each must be **retired from the lessons-learned store** as
part of this plan's finalize lessons-housekeeping (the fix consumes the lesson — its knowledge now
lives in this plan's record and in the code it changes, not as a standing lesson). Verify each is
still open before acting; if one is already fixed or proves out of scope, record that and do not retire
it blindly.

| Lesson | Resolved by | Retire? |
|--------|-------------|---------|
| `2026-07-21-16-001` (dead discover-modules tier + weak assertions) | D2, D3 | yes, on landing |
| `2026-07-24-13-001` (pre-push-quality-gate lacks `mypy test` CI parity) | D4 | yes, on landing |

The coverage-scope (D1) and RU-4/M4 (D5) items are epic watches / a remediation-map entry, not filed
lessons — nothing to retire for those; their closure is recorded in this plan's landing.

## Expected Surface

Declared in full, including non-test files:

- `pyproject.toml` — `[tool.coverage.run] source` (D1).
- `build.py` — only if D1 widening or D4 parity needs the pytest/coverage argv changed.
- `phase-6-finalize` — the `pre-push-quality-gate` step doc/script (D4).
- `test/plan-marshall/integration/discover_modules/**` — delete or revive (D2), and the four unit
  assertions (D3, in the corresponding unit-tier test module).
- The RU-4/M4 fixture files if D5 lands them.
- **OFF-LIMITS**: the armed gates (`filterwarnings`, `--strict-markers`, `--strict-config`,
  `--durations`), the dependency declarations, and the marker registry. If D4's added `mypy test`
  surfaces a gate interaction, fix the cause — never disarm.

## Dependencies and Sequencing

- Independent of PLAN-09 (retrospective scripts) → parallelizable.
- Shares the `phase-6-finalize` bundle with PLAN-08 (D4 touches `pre-push-quality-gate`; PLAN-08
  touches dispatch machinery) — expected file-disjoint; confirm at outline, else sequence.

## Hand-Off Command

```text
/plan-marshall Close the test-suite-quality epic's unit-testing residue with four-to-five deliverables, verifying each against the code before acting. (1) TAKE the coverage-scope denominator decision that a prior plan deferred: pyproject.toml [tool.coverage.run] source is ["marketplace/bundles"], so build.py, marketplace/targets/** and .claude/** contribute zero statements even though roughly 342 tests exercise them — either widen source to the untracked-but-tested surfaces (ENUMERATE them from the actual tests, do not assume the list, and record that the headline coverage number moves) or document the scope as a deliberate choice in pyproject.toml and doc/developer/; the deliverable is a TAKEN decision, not another deferral. (2) Resolve the dead discover_modules integration tier (lesson 2026-07-21-16-001): test/plan-marshall/integration/discover_modules/test_gradle_discover_modules_integration.py and test_maven_discover_modules.py contain zero test_ functions and point at non-repo clones, so they read as coverage that does not exist — either delete the directory outright or revive it with in-repo fixture projects so it is CI-runnable; leaving it is the worst option. (3) Independently strengthen the four weak but load-bearing unit assertions test_gradle_stats_file_counts, test_gradle_stats_readme_in_paths, test_gradle_module_has_commands and test_gradle_discover_sources to assert concrete discovered values rather than non-emptiness — this is a separate call from (2), do not bundle it into a consolidation refactor. (4) Give phase-6-finalize's pre-push-quality-gate CI parity by adding the test-tree type check (mypy test / test-compile) that CI's verify chain runs but the local gate does not (lesson 2026-07-24-13-001) — two test-tree type errors, an invalid dashed test-package name and an un-propagated dict-to-list contract change in an out-of-footprint test file, passed the local gate and failed only at CI; resolve all build commands through the architecture-resolved executor. (5) Verify whether the deferred RU-4/M4 build-backend fixture consolidation from the standards-compliance plan is still open and either land it or record an explicit closure rationale rather than carrying it as an indefinite watch. Do NOT touch the armed pytest gates (filterwarnings, --strict-markers, --strict-config, --durations), the dependency declarations, or the marker registry; if the added mypy test surfaces a gate interaction, fix the cause, never disarm. Read the TOON status and errors after each build call. This plan RESOLVES lessons 2026-07-21-16-001 (dead discover-modules tier + weak assertions, resolved by deliverables 2 and 3) and 2026-07-24-13-001 (pre-push-quality-gate lacks mypy test CI parity, resolved by deliverable 4) — verify each is still open, then RETIRE both from the lessons-learned store in finalize lessons-housekeeping since the fix consumes them; if either is already fixed or proves out of scope, record that and do not retire it blindly.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-07.md}
