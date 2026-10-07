envelope_version=1
sender_type=plan
sender_id=exploration-share-is-unmeasured
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T07:27:10Z

component=plan-marshall:plan-retrospective
category=bug
title=check-manifest-consistency rule M3 is a vacuous guard — it tests for the unprefixed 'module-tests' the composer never emits

# Rule M3 (tests-only cross-check) can never fire, and it hid a real violation on the plan that exposed it

## Observation

`check-manifest-consistency.py::evaluate_tests_only` skips unless:

```python
steps != ['module-tests']
```

`manage-execution-manifest` stamps the **prefixed** form. Plan `exploration-share-is-unmeasured`'s `execution.toon` carries:

```
phase_5.verification_steps: ['verify:module-tests']
```

The decision log records the composer routing exactly this way — `routed non-canonical orchestrator-tier verb 'compile' to phase-5 step 'verify:compile'`. So M3's predicate compares against a value the producer stopped emitting when the `verify:` prefix was introduced. **The rule is structurally unable to fire.**

## Why this instance matters

M3 is the ONLY cross-check that guards the tests-only manifest classification, and this plan is exactly the case it exists for:

- The composer logged `Rule tests_only fired`.
- The realized merge footprint (`bef5b29d`, 22 files) contains **6 production Python files**: `manage-metrics.py`, `claude_runtime.py`, `_claude_runtime_impl.py`, `opencode_runtime.py`, `runtime_base.py`, `audit.py`.
- Had M3 fired, it would have emitted `tests_only_diff_violation` naming 5 non-test non-docs culprits.

Instead the aspect reported `tests_only_diff, skip, "rule M3 not applicable"` and the fragment summary read **`passed: 2, failed: 0, findings: 0`** — a confident clean verdict produced by a check that never ran.

Downstream consequence: the tests-only classification also justified dropping `sonar-roundtrip` at the posture cutoff, so **no static-analysis pass ever inspected this plan's production delta**.

## Rule

- A cross-check predicate that compares against a **literal produced by another component** is a contract coupling. When the producer's vocabulary changes (here: a `verify:` namespace prefix), every consumer literal is a silent breakage — the check degrades to permanently-skip, which reads as pass.
- **A skipped check must not aggregate into a clean summary.** `passed: 2, failed: 0` over three skipped rules is the confident-signal-hides-a-caveat shape. Report `evaluated: N of M` so a summary of all-skips is visibly vacuous.
- The structural remedy is population-derived: assert that every rule predicate matches at least one value the producing composer can actually emit — the shape already used by `test/_shared/_dispatch_roster.py`. A hand-written literal is the prohibited form.

## Recurrence

This is occurrence **5+** of the vacuous-guard archetype in this repository, and at least one prior instance was introduced *by a fix for the same archetype*. The count is not decreasing because each instance is fixed individually rather than being detected as a class.

## Residue

The M3 fix is **not done**. Two changes are owed: (a) normalize the comparison to the prefixed vocabulary (or compare on a canonicalized suffix), and (b) add the population-derived predicate-reachability test so the next prefix change fails loudly.
