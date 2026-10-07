# PLAN-02: Test Standards Compliance

epic: test-suite-quality
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-02-test-standards-compliance.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. See `persona-marshall-orchestrator/standards/orchestration-model.md` for
> the tier and hand-off contract.

## Objective

Refactor the plan-marshall test suite to comply with the `pm-dev-python:pytest-testing` profile
standard, package-by-package, driven by PLAN-01's remediation map. This is the "comply to standards"
recipe run: AAA structure, fixture and parametrization discipline, isolation/determinism, consistent
assertion style, and — critically — unified bootstrapping and shared fixtures (consolidating the
divergent `conftest.py` files and ad-hoc helper modules per PLAN-01's unification proposal).

## Deliverables

1. Bootstrapping/fixture unification per PLAN-01's proposal: consolidate divergent `conftest.py` and
   the ad-hoc helper modules into the agreed shared shape.
2. Standards-compliance refactor of the prioritized test packages from PLAN-01's map (AAA, fixtures,
   parametrization, isolation, determinism, assertion style), package-by-package.
3. Redundancy consolidation: merge/prune the near-duplicate test cases and redundant assertions PLAN-01
   identified, preserving coverage.
4. Dead-test + marker hygiene: prune `skip`/`xfail`-without-reason and commented-out tests PLAN-01
   flagged, and register every custom pytest marker (the enforcing `--strict-markers`/`--strict-config`
   flags land in PLAN-04, so registration must precede them).
5. Green quality-gate and full test run after each package group (mypy + ruff + module-tests), with no
   coverage regression.

## Expected Surface

- Broad mutation across `test/**` (scoped per PLAN-01's package groups), including shared `conftest.py`
  and helper modules.
- Possible touch of test-only helper modules; no production-source behavior changes.

## Dependencies and Sequencing

- Depends on: PLAN-01 (consumes its remediation map and unification proposal).
- Overlaps with: PLAN-03 — both mutate `test/**`. Sequence unless PLAN-01's map assigns provably
  disjoint packages (deferred to a `next`-time disjointness decision). The shared bootstrapping/fixture
  unification (deliverable 1) is a suite-wide surface and is a strong reason to sequence PLAN-02 ahead
  of PLAN-03.

## Hand-Off Command

```text
/plan-marshall Refactor the plan-marshall test suite (test/**) to comply with the pm-dev-python:pytest-testing standard, package-by-package, using the remediation map produced by the scrupulous-test-suite-analysis plan as the work list. Deliver: (1) unify bootstrapping and shared fixtures per that analysis's unification proposal — consolidate the divergent conftest.py files and ad-hoc helper modules (_pm_input_validation_fixtures.py, _resolve_project_dir_fixtures.py, build_test_helpers.py, discovery_test_helpers.py) into the agreed shared shape; (2) refactor the prioritized test packages to pytest-testing standards (AAA structure, fixtures, parametrization, isolation, determinism, consistent assertion style); (3) consolidate the near-duplicate test cases and redundant assertions the analysis identified, preserving coverage; (4) prune skip/xfail-without-reason and commented-out tests, and register every custom pytest marker (the enforcing --strict-markers/--strict-config flags are handled by the runtime-dependency-modernization plan, so registration must precede them); and (5) keep the quality-gate green (mypy + ruff + module-tests) with no coverage regression after each package group. Run build commands through the architecture-resolved executor.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-02.md}
