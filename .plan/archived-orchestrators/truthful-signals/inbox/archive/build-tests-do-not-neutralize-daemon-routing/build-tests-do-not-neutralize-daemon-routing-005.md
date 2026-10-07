envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:02:08Z

component=plan-marshall:persona-module-tester
category=improvement

# A population-derivation predicate needed three refinements before it was sound — and its zero is a discipline property, not a structural one

The census predicate for "call sites affected by ambient daemon-routing neutralization" was wrong twice before it was right. Each version looked plausible and each produced a confidently-wrong number.

**v1 — token regex.** Matched the command token textually. Wrong because **a text match is not a call site**: it swept in analyzer fixtures that merely *name* `cmd_run` as data, never invoking it. Over-counted.

**v2 — AST, but module-granular.** Correct about what a call site is, wrong about scope. Because the predicate asked "does this module pin `in_process` anywhere?", **one sibling test's `in_process` pin excused every other test in the same file**, driving `count_affected` to a false **0**. A confident zero produced by a granularity error — the same shape as a vacuous guard.

**v3 — AST, per call site.** Each invocation evaluated on its own `execution_mode` argument. Final: **661 call sites examined, 0 currently affected.**

The v3 zero is real, but it must be reported with its caveat: **it is a property of current stub discipline, not of the structure.** 28 of the 41 relevant call sites sit at `execution_mode='auto'` — they are un-neutralized today only because their surrounding fixtures happen to stub. One un-stubbed sibling makes the count non-zero again.

## Solution

- **Derive the population from the AST, never from a token or filename match.** A textual hit is a candidate, not a call site.
- **Evaluate the predicate at the granularity of the thing being counted.** If you are counting call sites, the predicate must run per call site. A module-granular predicate over per-call-site facts silently lets one member's compliance excuse all the others — and it fails *toward zero*, which reads as success.
- **When a detector returns 0, state which property produced the 0.** "Zero because the structure forbids it" and "zero because current callers happen to be disciplined" are different claims with different durability. Report the second with its exposure count (here: 28 of 41 at `auto`).
- Ship the predicate as a re-runnable script so the number is re-derived, not pinned.

## Impact

Third and fourth data points for the `vacuous guard` / confident-zero archetype, and a granularity axis the existing "every set-guarding detector must be population-derived" rule does not yet name: population-derivation is necessary but **not sufficient** — the derivation must also be at the right granularity, or it produces a population-derived vacuous zero.
