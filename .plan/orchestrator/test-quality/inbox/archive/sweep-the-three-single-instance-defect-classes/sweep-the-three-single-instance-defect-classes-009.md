envelope_version=1
sender_type=plan
sender_id=sweep-the-three-single-instance-defect-classes
epic=test-quality
kind=candidate-lesson
created=2026-09-14T03:26:55Z

component=test-shape-scan
category=bug

# A guard is credited with a property its predicate does not entail, or entails about the wrong subject

Four review-bot findings on PR #1486 are one defect: a guard was written, named, and
commented as if it proved a property, while its predicate proved something strictly
weaker — or proved the right thing about a *different* subject. Every one of them
passes vacuously in exactly the scenario the guard exists for.

The four instances:

| Finding | Site | Credited with proving | What the predicate actually entails |
|---------|------|-----------------------|-------------------------------------|
| `1ae43f` | `_test_shape_scan.py:375` (also 399-405, 420, 473-479) | the derived population is non-empty | nothing about cardinality — `assert isinstance(cases, list)` and `assert len(cases) >= 0` are both true over `[]`. The scanner accepted *assertion syntax* as the proof |
| `04bc46` | `test_branch_cleanup_merge_queue_routing.py:760` | every provider contributed merge-shaped keys | `all(_MERGE_SHAPED.values())` is `True` over an empty mapping. The comment directly above it names it a vacuity guard — **the vacuity guard is itself vacuous** |
| `f9fc66` | `_test_shape_scan.py:486` | the *returned* population is non-empty | `_guards_its_result` collects every name read by any return expression, so `assert candidates` followed by `return [c for c in candidates if c.enabled]` passes while returning `[]`. Right property, wrong subject |
| `ad1bfe` | `test_freshness_exempt_vs_verified_discrimination.py:413` | *this* positive control reads `matched_notation` / `matched_entry_index` / `worktree_sha` | whole-file containment — any unrelated test, comment, or string elsewhere in the module satisfies it. A token-only control passes. Right property, wrong subject |

`f9fc66` is the sharpest: TASK-010 had just made `_positive_cardinality_names` correct
about what an assertion *proves*, and `f9fc66` is the next layer down — which population
the proof *attaches to*. Fixing the first did not surface the second.

`ad1bfe` is the one with teeth: that test's own docstring states the rule that a
token-only control must not survive — and the test enforcing it was written with a
whole-file containment check, i.e. the defect survived inside the very plan whose job
was to remove it.

## Impact

A vacuous guard is worse than an absent one. An absent guard is visible; a vacuous guard
reports green and is cited as evidence. Three of these four sit in repository-wide gates
armed at zero, so each one converts "the sweep found nothing" from a measurement into an
assumption — the precise clean-zero failure this project's store-state discriminators
exist to abolish, reproduced at the assertion level.

## Solution

Before crediting a guard with a property, state the property and the scenario separately,
then check the predicate against the scenario:

1. **Name the scenario the guard exists for, then instantiate it.** For a non-vacuity
   guard the scenario is the empty population — write the empty case and confirm the
   guard *fails*. A guard with no failing input is not a guard.
2. **Check the subject, not just the property.** An assertion about an input is not an
   assertion about a transformed output (`f9fc66`); a containment test over a module is
   not a containment test over a unit (`ad1bfe`). Bind the evidence to the smallest
   scope that carries the claim — the function or assertion that holds the predicate.
3. **Beware the universally-quantified idiom over a possibly-empty collection.**
   `all(...)`, `every(...)`, `not any(...)` are all true over the empty set. Require the
   collection non-empty *first*: `assert _MERGE_SHAPED and all(_MERGE_SHAPED.values())`.
4. **Do not accept syntax as semantics.** `assert <anything>` is not a cardinality
   proof; route every such check through one shared predicate that accepts only forms
   implying positive cardinality, and apply that predicate at every guard site.

## Impact — where else to look

The four sites are test infrastructure, but the rule is domain-independent: any
`assert` / `all()` / containment check whose failure mode is "passes over the empty or
narrowed case" is in scope. Worth a targeted sweep of the repository's other
repo-wide gates for the `all(mapping.values())` and whole-file-containment idioms.

## Provenance

Plan `sweep-the-three-single-instance-defect-classes`, PR #1486 (merged). Findings
`1ae43f`, `ad1bfe`, `04bc46`, `f9fc66` — all `pr-comment`, all `resolution=fixed`
in-run. Reviewer: coderabbitai, citing its own path instruction "Check a guard's
predicate against the scenario the guard exists for." Remediated by TASK-010, TASK-011,
TASK-014.
