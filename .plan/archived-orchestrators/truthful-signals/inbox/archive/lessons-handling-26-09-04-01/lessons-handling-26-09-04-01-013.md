envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T06:10:47Z

component=plan-marshall:build-maven
category=bug

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, PLAN-02
(`inherited-build-config-verification-depth`, merged as PR #714 / `7482cf18`).
bundle=plan-marshall

# Widening a module-scoped test-compile to the whole reactor is invalid when modules depend on a sibling test-jar

## Observation

`pre-push-quality-gate` obtains a whole-tree `test-compile` by taking the
resolver's module-scoped command and **removing the module argument**. In this
reactor that strips `-pl token-sheriff-validation -am`, and the resulting bare
reactor-wide `test-compile` cannot resolve the `token-sheriff-validation`
test-jar that `token-sheriff-client` and `benchmark-core` depend on: 20 compile
errors, every one a missing `de.cuioss.sheriff.token.validation.test` import.

The test-jar is an *installed* artifact. `test-compile` never packages or
installs it, so a reactor-wide `test-compile` has no path to it — while the
module-scoped form works because `-am` builds the upstream module far enough in
the same reactor pass.

## Provenance established before acting

The failure was proven to be a property of the widened command and not of the
branch, before any conclusion was drawn:

- The branch diff was `AGENTS.md` only — no Java, no POM.
- `verify -Ppre-commit` passed whole-reactor on the same tree.
- The resolver's own module-scoped `test-compile` passed in 2 seconds.

It was therefore recorded as **un-gated**, not as a gate red. That distinction is
the point: a red that the command itself manufactured is not evidence about the
change.

## The generalisable rule

"Drop the `-pl <module> -am` argument to widen the scope" is not a
scope-preserving transformation. It is a *different command* with different
dependency-resolution semantics, and it is unsound for any reactor where one
module consumes another's test-jar.

## Suggested corrective action

Do not synthesise a whole-tree command by argument deletion. Either resolve a
whole-tree command through the architecture API as its own canonical command, or
widen by escalating the lifecycle phase (`test-compile` -> `install`/`verify`)
rather than by removing the reactor scoping. When a widened command fails, prove
provenance (as above) before recording a gate verdict.

## Impact

Every multi-module Maven project with an inter-module test-jar dependency gets a
false gate red from this widening — and the red is indistinguishable from a real
one to anyone who does not run the provenance check.
