envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:20:38Z

component=plan-marshall:script-shared
category=bug
confidence=high
source_aspects=findings-store,build-integration

# A green build clears test-failure findings even when the command it ran executes no tests

## Context

`_reconcile_pending_build_findings` bulk-resolves every pending finding of all three build types to `fixed` whenever *any* build command returns green:

```python
BUILD_FINDING_TYPES: tuple[str, ...] = ('build-error', 'test-failure', 'lint-issue')

reconcile_result = resolve_findings_by_type(
    plan_id=plan_id,
    finding_types=BUILD_FINDING_TYPES,
    to_resolution='fixed',
    detail=f'auto-resolved by green build: {command_str}',
)
```

Nothing relates the green command to the finding's type. The resolution detail then stamps the clearing command onto the record, which is what makes the mismatch readable after the fact.

Measured on this run. Two `test-failure` findings — each recording a live runtime assertion failure — were resolved `fixed` with:

> `auto-resolved by green build: ./pw test-compile plan-marshall`

- `e24829` — `test_unset_baseline_accepts_production_argv_under_framework_interpreter`, `AssertionError: assert 'refused' == 'queued'`
- `a893a6` — `test_daemon_construction_leaves_baseline_interpreter_unset`, `AssertionError: assert '/Library/Frameworks/.../Python' is None`

`test-compile` is defined in `build-pyproject/standards/pyproject-impl.md` § Quality Commands as **"Type-check the `test/` tree only (mypy)"**. It executes zero tests. A green mypy pass over the test tree cannot establish that either assertion now holds, so the record asserts something its own cited evidence cannot support.

The contrast is in the same store on the same plan: a third `test-failure` finding (`904a14`) was resolved by `./pw module-tests plan-marshall` — a command whose population actually contains the failing test. The mechanism cannot tell the two cases apart.

## Root cause

The reconciler's predicate is "a green build happened", not "a green build whose population would have re-executed this finding's check". `BUILD_FINDING_TYPES` is a fixed tuple applied uniformly to every command, so `compile` (production mypy), `test-compile` (test-tree mypy), `quality-gate` (mypy + ruff, no tests) and `module-tests` all terminalize the same set. The docstring states the belief the code does not check — *"the failure they recorded has been fixed"* — and the stamped detail preserves the false attribution rather than preventing it.

This is a confident-signal-hides-a-caveat instance in the audit trail rather than in the outcome: on this plan `module-tests` did eventually go green (`pre-push-quality-gate`: "test-compile + module-tests green"), so the tests really were fixed. The defect is that the record credits a command that could not have observed it, and a reader has no way to distinguish this run from one where the tests were still red.

## Proposed action

Gate reconciliation on command coverage rather than on greenness alone: map each canonical command to the finding types its execution can actually clear (`module-tests`/`coverage`/`verify` → `test-failure`; `quality-gate` → `lint-issue`; `compile`/`test-compile` → `build-error` for their own tree only), and resolve only the intersection. Findings outside the green command's population must stay pending.

Where a narrower mapping is not wanted, at minimum stop stamping `fixed` on an unobserved finding — a distinct resolution (e.g. `stale_unverified`) preserves the store-hygiene benefit without asserting a verification that did not happen.

Add a population-derived test: for each canonical command, assert the reconciler clears exactly the finding types that command executes, so a new command cannot silently inherit clear-everything semantics.

## Evidence

- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — `BUILD_FINDING_TYPES` (`:262`), `_reconcile_pending_build_findings` (`:425-448`), call site at `:628-632` guarded only by `names_real_plan(plan_id)` and `test_summary.failed == 0`
- `manage-findings list --plan-id daemon-baseline-interpreter-is-unregistrable` — findings `e24829` and `a893a6`, `resolution: fixed`, `resolution_detail: "auto-resolved by green build: ./pw test-compile plan-marshall"`
- same store, finding `904a14` — `resolution_detail: "auto-resolved by green build: ./pw module-tests plan-marshall"`
- `build-pyproject/standards/pyproject-impl.md` § Quality Commands — `test-compile` = "Type-check the `test/` tree only (mypy)"
