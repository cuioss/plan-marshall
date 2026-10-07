envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T21:28:35Z

component=plan-marshall:script-shared
category=anti-pattern
title=A truthy sentinel makes every `if not x:` guard vacuous

# A truthy sentinel makes every `if not x:` guard vacuous

When an "absent" value is represented by a **truthy sentinel** (a non-empty string such as
`NO_PLAN`) instead of a falsy one (`None`, `""`), every existing guard written as
`if not x:` becomes **vacuous** — it can never fire again — while continuing to read
exactly like a working guard.

## How it arose

In `mandatory-plan-id-build-results-ledger` (`PLAN-TRUTH-026`, PR #1075), narrowing the
`NO_PLAN` sentinel created this class wholesale. Every call site that had been written
against a falsy "no plan id" now received the string `NO_PLAN`, which is truthy, so:

```python
if not plan_id:          # never true once plan_id == "NO_PLAN"
    ...handle absent...
```

The guard body became unreachable at every such site, silently, with no type error and no
test failure — the code still compiles, still runs, and still *looks* correct at review.

## What the plan found

- **One live instance** confirmed broken: `cmd_resolve_test_scope`.
- **8 further guard sites** had to be swept — they were not all broken in the same way, but
  every one of them was reasoning about the real-vs-sentinel distinction independently.
- The 9 sites were then **collapsed into a single `names_real_plan` TypeGuard seam**, so
  the distinction is now decided in exactly one place.

The one-live-instance / nine-sites ratio is the important number: the *defect* was rare,
the *exposure* was not. Sweeping only until the known-broken site was fixed would have left
8 independent re-derivations of the same predicate, each free to drift.

## Do this instead

- **Never introduce a truthy sentinel for an absent value** without first sweeping every
  falsy-test guard over that value. The sweep is not optional cleanup — it is part of the
  change that introduces the sentinel.
- **Collapse the predicate into one named seam** (`names_real_plan`-style TypeGuard) rather
  than fixing each `if not x:` in place. N corrected guards are N future drift sites; one
  seam is one.
- Prefer a **type-level** distinction where the language supports it, so the compiler/type
  checker enumerates the call sites for you instead of leaving it to a grep.
- Treat "the guard still reads correctly but can no longer fire" as its own defect class —
  it is invisible to review, invisible to tests that only exercise the happy path, and
  invisible to coverage (the guard line is *executed*, just never *taken*).

## Related

This is the **vacuous-guard** archetype, now at n=5 in this project, and one prior instance
was introduced *by a fix for the same archetype*. That history is the argument for the seam:
hand-correcting individual guards is how the archetype keeps reproducing itself.
