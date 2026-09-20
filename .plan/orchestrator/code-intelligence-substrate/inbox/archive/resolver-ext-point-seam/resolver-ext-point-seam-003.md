envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T11:51:03Z

component=plan-marshall:extension-api
category=anti-pattern
title=A centralizing refactor can silently widen a lazy contract into an eager one

# A centralizing refactor can silently widen a lazy contract into an eager one

Caught by `pre-submission-self-review` on PR #1067 as a `contract_drift` that the plan
**itself introduced**. Fixed in `405b05f069141ccb8367da57d90e958f89668a51`.

## What happened

The plan centralized internal-dependency edge derivation into a single `_derive_edges`
helper — a straightforwardly good refactor that removed a duplicated coordinate join. But
the pre-refactor call graph had *two* distinct entry paths with *different eagerness*, and
collapsing them onto one helper took the union of their work rather than preserving each
path's contract:

- **Maven enrichment became unconditional.** Post-refactor, every invocation ran
  `mvn dependency:tree` once per module. `build-maven`'s documented contract is *lazy,
  per-module* enrichment — enrich a module only when that module's edges are actually
  needed. The centralized helper silently converted that into eager, whole-project
  enrichment on every call.
- **The newly-eager work was then thrown away.** For every module carrying a declared
  `internal_dependencies` override, the declaration wins by precedence — so the
  `mvn dependency:tree` subprocess the refactor had just made unconditional was executed and
  its result discarded. Strictly-added cost, zero added information.

Nothing failed. Tests were green, the derived edges were correct, and the only symptom was
runtime and subprocess count — which is exactly why a self-review structural check caught it
and no functional gate did.

## Solution

Route the precedence decision *before* the expensive derivation, through one helper shared
by both call sites:

- A single `_declared_dependencies` helper answers "does this module have a declared
  override?" and is consulted by **both** entry paths.
- Derivation (and therefore Maven enrichment) runs only on the path where the declaration
  did not answer, restoring the lazy per-module contract.

The general shape: when centralizing N call paths onto one helper, the helper's cost profile
must be the **intersection** of what each path needed, not the union. Any per-path guard that
previously gated expensive work must move *above* the centralized helper, not into it.

## How to catch this class

1. **Before centralizing, enumerate each call path's laziness/eagerness contract** — not
   just its return value. Two paths returning the same value can have legitimately different
   cost contracts, and the refactor must preserve both.
2. **Any refactor that touches a call site guarded by a cheap precedence check is suspect.**
   If a declaration/override/cache check used to short-circuit an expensive call, verify the
   check still short-circuits after centralization.
3. **The "computed then discarded" signature is the tell.** If a refactor produces a value
   that some branch unconditionally overwrites, the expensive computation feeding it has
   escaped its guard.
4. **Functional gates will not catch it.** Green tests plus correct output plus a widened
   cost contract is the whole signature. This class needs a structural / contract-level
   review pass, which is where it was in fact caught.

## Impact

Applies to any centralize-the-duplication refactor in this codebase where one of the merged
paths invokes a subprocess, network call, or documented-lazy enrichment API. The
`build-maven` lazy per-module enrichment contract in particular is a documented contract
that a downstream refactor can violate without touching `build-maven` at all.
