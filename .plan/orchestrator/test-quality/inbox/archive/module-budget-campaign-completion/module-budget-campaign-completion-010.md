envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=test-quality
kind=finding
created=2026-09-28T05:55:07Z

# Add a plugin-doctor rule: whole-tree scan tests must carry a per-test timeout

## The gap

`pyproject.toml` documents a convention and prescribes a remedy, but **nothing enforces it**:

> `timeout = 300` is a suite-wide DEFAULT, not a ceiling. A handful of tests scan the WHOLE
> marketplace (the plugin-doctor quality gate and its analyzer sweeps) and contend with the compile
> and lint legs under `verify`, where they exceed 300 while passing standalone. Those carry a
> per-test `@pytest.mark.timeout(N)` naming why they need more, rather than raising the suite
> default — which is coupled to the `slow_live` budget above and must not drift up to accommodate a
> different class of test.

Three tests in `test/pm-plugin-development/plugin-doctor/test_runner.py` followed that convention at
`@pytest.mark.timeout(900)`. Two more in the same file — consumers of the same cached whole-tree
gate — did not, and fell through to the 300s default.

Verified there is no guard for this class today: not
`test/test_harness_shape_guards.py`, not `test/_shared/_test_shape_scan.py`, and not any
plugin-doctor rule. The convention lives only as prose in `pyproject.toml` plus the precedent of
three siblings.

## Why it is worth a rule rather than another one-off fix

The failure is **load-dependent**, so it surfaces intermittently and disappears on retry. Observed
three times in a single session, always as `verify` red on exactly those two tests, always green on
the retry:

```
passed: 28101  failed: 2
Timeout (>300.0s) from pytest-timeout
  test_runner.py:384  test_blind_spots_is_omitted_for_rules_that_derive_none
  test_runner.py:384  test_argument_naming_blind_spots_are_a_share_of_its_own_population
```

That is the worst shape a gate failure can take: it trains an operator or an agent to treat a red
build as provisional, which is how a real regression gets waved through. And because the next
whole-tree scan test someone adds will hit the same trap, the one-off fix does not close the class.

## Why the cost lands unevenly (the mechanism worth encoding)

`_real_tree_summaries()` is `@lru_cache(maxsize=1)`. The **first** consumer on a given xdist worker
pays for the whole-tree gate and the whole-marketplace analyzer sweeps; later consumers reuse the
result. xdist scheduling decides which worker takes that first cache miss, so a worker that takes it
while also running the lint leg under `verify` can blow the 300s default. The tests that survive
standalone (~44s measured) are the ones that lose the coin flip.

This also explains why the casualties were the *unmarked* tests rather than whichever executes first:
the marked siblings already carry 900s, so when a worker does take the cache miss under load, only
the unmarked pair could trip the default.

## Proposed rule

A `pm-plugin-development:plugin-doctor` test-conventions rule:

> A test that runs a whole-marketplace scan (a consumer of the shared whole-tree gate, or any test
> invoking the quality gate / analyzer sweeps over the real tree) must carry
> `@pytest.mark.timeout(N)` with N above the suite default, and a comment naming the contention.

Detection seam is straightforward — an AST check for a whole-tree-scan call with no enclosing
per-test timeout marker — and it belongs in the existing `test-conventions` scope, which already owns
test-tree conventions across `test/`.

Note the rule must NOT recommend raising the suite default. `pyproject.toml` couples
`timeout = 300` to the `slow_live` budget; the per-test bound is the sanctioned escape hatch, and the
suite-wide value is correct as written.

## Provenance

Found while verifying the tree after #1640 landed; fixed in #1645
(`1b4c1ba05`, per-test bounds only, no production change). The follow-up rule is what makes the fix
durable rather than another one-off.

Related open gap filed elsewhere, same shape — a convention that exists in prose with nothing
enforcing it: the self-review surfacer only surfaces *changed* files, so contract drift whose code
side changed but whose doc side did not is structurally invisible to its own contract-drift check.
