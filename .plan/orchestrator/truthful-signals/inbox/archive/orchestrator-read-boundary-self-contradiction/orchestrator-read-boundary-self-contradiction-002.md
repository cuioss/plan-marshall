envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:08:59Z

component=plan-marshall:persona-module-tester
category=anti-pattern
created=2026-07-28
bundle=plan-marshall

# A path-classifying predicate must match the repo-RELATIVE path, never the absolute path

## What happened

PR #1040 added `test_orchestrator_read_boundary_contract.py`, a population-derived
regression module whose entire purpose is to prevent vacuous guards. Inside it:

```python
def _is_orchestrator_document(document: Path) -> bool:
    return 'orchestrator' in str(document).lower()
```

`document` is an **absolute** `Path`. This plan's own worktree is checked out at
`.plan/local/worktrees/orchestrator-read-boundary-self-contradiction/`, so the
substring `orchestrator` is present in the absolute path of **every** file in the
repository. The predicate returned `True` for the whole population, silently
defeating the population scoping it existed to perform — and it did so while every
assertion stayed green, because an over-broad classifier widens a set rather than
emptying it.

PR-Agent caught it. `pre-submission-self-review` did not: it reported
`42 candidates examined, 0 findings` on the commit that introduced the defect.

## Solution

**Rule:** any predicate that classifies a file by substring, prefix, or glob on its
path MUST match `path.relative_to(PROJECT_ROOT)` (or the module-root equivalent),
never `str(path)`. The absolute path contains ancestor directory names outside the
repository's control — and under plan-marshall those ancestors are *derived from the
plan slug*, so an absolute-path match is effectively matching against arbitrary
words from the plan title.

**Pin it so a revert cannot pass anywhere.** The fix in `dc78a5a4b` is not just the
`relative_to` call — it is a companion test that monkeypatches `PROJECT_ROOT` to a
directory whose name contains the trigger substring, so reverting the predicate fails
in *any* checkout rather than only in a checkout that happens to be named unluckily.
A relative-path fix without that test is itself unguarded: it passes trivially in a
normally-named checkout.

Every member of the guarded population here is built strictly under `MARKETPLACE_ROOT`,
`PROJECT_ROOT / 'doc'` or `PROJECT_ROOT / 'CLAUDE.md'`, so `relative_to` always
succeeds — no exception handling needed. That closure property is what makes the
relative form safe to use unconditionally.

## Impact

**New pole of a known archetype.** The recorded "vacuous guard" archetype has so far
been the *never-fires* pole (a predicate whose condition cannot be true in the scenario
it guards). This is the **over-broad** pole: a predicate that is *always* true, which
is equally vacuous but presents as a passing test over a *larger* population — it looks
more thorough, not less. Detectors written to catch the never-fires pole (does the
condition ever fire? does the negative fixture get flagged?) do not catch this one.
Both poles need asking:

- Does the predicate ever return `True` on the scenario it guards? (never-fires)
- Does the predicate ever return `False` on something outside that scenario? (over-broad)

**Self-review gap.** `ext-self-review-plan-marshall` surfaces regexes, flag-guard pairs,
and lone-unguarded-boundary calls, but did not surface a path-substring predicate as a
candidate. A `str(Path)`-substring test is a cheap deterministic candidate class worth
adding to that surfacer.

**Meta.** This defect lived inside the very test written to prevent vacuous detectors,
introduced by the plan whose subject was self-contradicting authority. That is the
fourth-plus recorded instance of "a defect of class X introduced by the fix for class X".
