envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:29Z

component=plan-marshall:phase-4-plan
category=bug

# Task deriver stamps test-compile verification command that cannot resolve a sibling test-jar

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-07-21-001` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-07-21-001`, created 2026-09-07, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Observed

In plan `carry-refresh-token-through-code-exchange` (TokenSheriff), the derived
TASK-2 (module_testing profile) carried the verification command:

```
test-compile -pl token-sheriff-client -am
```

That command fails. At the `test-compile` goal the reactor has not yet packaged
`token-sheriff-validation`'s **test-jar**, so every `token-sheriff-client` test
importing `de.cuioss.sheriff.token.validation.test.dispatcher` /
`…validation.test` / `…validation.test.generator` fails to compile with
`Package … ist nicht vorhanden`. The failure is broad and unrelated to the plan's
own change — it hits `ClientSecretAuthTest`, `DiscoveryAdversarialTest`,
`DiscoveryResolverTest`, `ClientCredentialsFlowTest` and others.

The orchestrator reproduced this independently while running a scoped test:
`test -pl token-sheriff-client -am -Dtest=…` failed the same way, and the same
invocation at `verify` succeeded.

## Why it matters

The stamped command is the deliverable's declared proof. A verification command
that fails for a reason unrelated to the change forces the executor to
improvise a substitute mid-run, and an executor that instead \"fixed\" the
unrelated compile errors would have laundered unplanned work into the plan.

## Directive

- When deriving a verification command for a module whose tests consume a
  **sibling module's test-jar**, the phase must be `verify` (or at minimum a
  phase at/after `package` for the producing module) — never `test-compile`
  and never `test`.
- Detect the condition structurally: the module's test sources import a package
  belonging to another reactor module's `src/test`, or the module declares a
  `<type>test-jar</type>` dependency.
- This is the same root cause already recorded for this project as the client
  test-jar build gotcha; the gap is that the **task deriver** keeps emitting the
  broken form even where the outline's own deliverable-level command is correct
  (`verify -pl token-sheriff-client -am` here).

## Verification

`verify -pl token-sheriff-client -am` resolves the test-jar and runs the module's
tests; `test-compile` / `test` with the same `-pl/-am` scoping do not.
