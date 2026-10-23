envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:32Z

component=plan-marshall:persona-module-tester
category=anti-pattern
created=2026-10-21
bundle=plan-marshall

# A refusal-path assertion that compares a pre-attempt snapshot cannot see the mutation

`PlanInstanceStoreTest` asserted that a refused recording left version 1 unchanged by
comparing a snapshot taken BEFORE `recordComposed` with the prepared replacement string.
Both sides of the comparison are fixed before the call under test runs, so a regression
that writes into version 1 during the refusal still passes — the assertion is vacuous
exactly where it claims to guard.

## Solution

Read the artifact AFTER the call under test returns and compare it with the expected
unchanged content:

    assertEquals(corrupted,
            Files.readString(scope.resolve(PlanInstanceStore.versionPath(1)), UTF_8),
            "the recorded text changed")

and the same shape for the headerless case. The general rule: a negative-path assertion
must re-read the state it claims is preserved at the moment after the operation, never
compare two values that were both fixed before it.

## Impact

Refusal, rollback, and "no side effect" tests generally. The anti-pattern is invisible in
review because the assertion looks like it compares before-and-after; only the read AFTER
the call makes it an observation.
