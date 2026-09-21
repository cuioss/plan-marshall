# PLAN-01: Scrupulous Test-Suite Analysis

epic: test-suite-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-01-scrupulous-test-suite-analysis.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. See `persona-marshall-orchestrator/standards/orchestration-model.md` for
> the tier and hand-off contract.

## Objective

Produce a rigorous, evidence-backed analysis of the plan-marshall Python test suite (`test/**`) that
maps its quality debt: redundant assertions and near-duplicate test cases, duplicated and divergent
fixtures, inconsistent bootstrapping (multiple `conftest.py`, ad-hoc `*_fixtures.py` /
`*_test_helpers.py` helper modules), and general cleanup opportunities. The output is a prioritized
remediation map that WS-02's plans consume — this plan analyzes and designs, it does not mutate test or
production source.

1. **Measurement baseline (do this first).** Run the coverage suite and the module-test suite on the
   CURRENT toolchain via the architecture-resolved executor; record total wall-clock duration and total
   coverage %. Also capture the slowest-N test hotspots and a per-module coverage-gap map. This is the
   baseline the whole epic optimizes against — the epic's success criterion is measurable gains in BOTH
   duration and coverage relative to it. Hand the recorded numbers back so the orchestrator can seed the
   epic's Baselines & Trend section.
2. A redundancy report: clusters of near-duplicate / overlapping test cases and redundant assertions,
   with representative examples and consolidation candidates.
3. A fixture & bootstrapping inventory: every `conftest.py` and shared-helper module (e.g.
   `_pm_input_validation_fixtures.py`, `_resolve_project_dir_fixtures.py`, `build_test_helpers.py`,
   `discovery_test_helpers.py`), what each provides, and where they diverge or duplicate each other;
   PLUS a unification proposal (single root `conftest.py` vs package-scoped, which helpers to merge),
   consistent with `pm-dev-python:pytest-testing`.
4. A cleanup-dimension scout: flag candidates for the extra remediation dimensions — order-dependent /
   xdist-sensitive or state-leaking tests, wall-clock-/calendar-derived deadlines and retry budgets that
   could become CI time-bombs (unfrozen clock seams; comparisons against hard-coded dates), real event
   loops driving subprocesses, dead/skipped/xfail-without-reason tests, unregistered markers,
   warning/deprecation emitters, and the slowest tests worth speeding up — so the operator can decide
   which become committed remediation goals. (These are the PLAN-03 hardening leads; feed them forward.)
5. A prioritized remediation map partitioning the work into candidate test-package groups, tagged with
   whether each group is a standards-compliance target (PLAN-02) or a hardening-propagation target
   (PLAN-03), noting the baseline/hotspot data per group, and flagging any surface-disjoint package pairs
   that could parallelize.

## Expected Surface

- Read-only across `test/**` (analysis only).
- Writes only an analysis/design artifact under the plan directory (no test or production source edits).

## Dependencies and Sequencing

- Depends on: none (epic anchor).
- Overlaps with: none — analysis-only, surface-disjoint from all mutation. Its OUTPUT gates PLAN-02 and
  PLAN-03.

## Hand-Off Command

```text
/plan-marshall Scrupulous analysis of the plan-marshall Python test suite under test/**. Do NOT mutate any test or production source — this is an analysis/design plan that produces a written remediation map only. Following the pm-dev-python:pytest-testing standard as the quality bar, deliver: (1) a redundancy report clustering near-duplicate/overlapping test cases and redundant assertions with consolidation candidates; (2) a fixture & bootstrapping inventory cataloguing every conftest.py and shared-helper module (_pm_input_validation_fixtures.py, _resolve_project_dir_fixtures.py, build_test_helpers.py, discovery_test_helpers.py, and any others) with where they diverge or duplicate; (3) a unification proposal for shared bootstrapping/fixtures (single root conftest vs package-scoped, which helpers to merge); and (4) a prioritized remediation map partitioning test-package groups, tagging each as a standards-compliance target or a hardening-propagation target, and flagging surface-disjoint package pairs that could be remediated in parallel.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-01.md}
