envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:09:30Z

# Candidate lesson: a type error in TEST code is visible to no routine gate — per-bundle quality-gate types production sources only, and pytest executes tests without type-checking them

**Source plan**: plan-truth-103 (PR #1475)

## ⚠ Provenance caveat — read before weighing

Unlike the four sibling candidates from this plan, this one is **NOT backed by a Q-Gate or PR-comment finding record**. It was reported by the finalize dispatcher as a run observation, and this step did not re-derive it against the gate configurations. Treat the *claim* as unverified and the *question* as the deliverable. Verify before promoting: read the per-bundle `quality-gate` target's type-check scope and the pre-push step's test-compile arm, and confirm the asymmetry actually holds.

## The claimed observation

On this run, the pre-push **test-compile arm** caught a type error in test code that no other gate could see, because:

- the per-bundle `quality-gate` type-checks **production sources only**, so test sources are outside its scope;
- `pytest` **executes** tests without type-checking them, so a type error in a test path that is not exercised (or is exercised only in a branch the run did not take) raises nothing.

If accurate, the consequence is that test-code type errors have exactly one detector in the pipeline, it sits late (pre-push), and its coverage is invisible from either of the two gates a developer would naturally assume covers them.

## Why it belongs to this epic

This is the epic's theme applied to the gate topology rather than to a claim in a document: **a gate whose coverage is narrower than its name implies**. A developer reading "quality-gate passed" reasonably infers the checked surface includes the tests they just wrote. If the scope is production-only, that inference is wrong and nothing in the green signal says so. Same shape as the already-routed `10f565` (`unproven_bots[]` carries a blocking semantic the quorum does not use) — a field or a gate whose name asserts more coverage than it delivers.

## Suggested disposition

Two candidate remedies, neither evaluated here:

1. Extend the per-bundle `quality-gate` type-check scope to test sources, making the late arm redundant rather than load-bearing.
2. Leave the scope as-is but make it **legible** — have the gate report the surface it typed (as the repo already requires of set-guarding detectors: publish the population), so "quality-gate passed" cannot be read as covering a surface it never inspected.

Option 2 is the cheaper and more in-theme move; option 1 is the durable one. The choice depends on type-check cost over the test tree, which this step did not measure.
