envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:48:01Z

component=plan-marshall:manage-config
category=anti-pattern

# Two tests asserted less than the contract they were written to pin: a hardcoded population, and a predicate weaker than its own docstring

Both were found by CodeRabbit on PR #1541, neither by the suite or the self-review, and both are the same failure: the assertion permits states the stated contract forbids.

## Instance 1 — a set-guarding population hardcoded instead of derived (`eb7c24`, Major)

`_SEVEN_SEEDED_STEPS` in `test_sync_defaults.py` hardcodes only PART of the population `_config_defaults._seed_finalize_steps()` actually produces. A new lane-less production step can be omitted from both `_fresh_wizard_finalize_steps()` and the sweep **while the test stays green** — the guard silently stops guarding the thing it was added for.

The accepted remedy has two halves, and the second is what makes it robust: derive the lane-less population from the production seed, **and add a non-empty assertion before the sweep**. Without the non-empty guard, a derivation that returns an empty set passes every per-member assertion vacuously.

The file's own sibling helper `_effective_lane_of` already derives correctly — the correct discipline was present one function away.

## Instance 2 — an assertion weaker than its docstring's contract (`472555`, Minor)

The test's stated contract is that a refused write "persists nothing". The assertion was `_persisted_lane(...) != 'off'`, which passes for an error response that nonetheless wrote `minimal` or `full`. The fixture seeds no finalize block at all, so `is None` is both exact and strictly stronger.

## Rule

- **Any test that guards a SET must derive that set from the production source, and must publish the population size.** A guard whose population can silently shrink to zero, or to a stale subset, reports success over the very gap it exists to detect. The non-empty assertion is not optional decoration; it is what makes the zero case distinguishable.
- **Where a docstring states the contract, the assertion must be the exact predicate, not a weaker one that happens to hold.** `!= 'off'` and `is None` are not the same claim; only the second matches "persists nothing".

The common generalisation: an assertion is a claim about the admissible state space. Writing a predicate looser than the contract admits states the contract forbids — and the test then certifies them.

## Note

Both landed as review-bot findings on a plan that had already run ten self-review rounds and a full Q-Gate. This class — assertion strength and population derivation inside test code — is not being caught by the in-run instruments.
