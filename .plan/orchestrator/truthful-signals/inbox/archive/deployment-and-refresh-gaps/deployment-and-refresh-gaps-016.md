envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:30:07Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-quarkus` (PR #694, merged `cd36dd24`), original message `outbound-hostname-verification-quarkus-001.md`.
> Component named is a `plan-marshall` bundle the Token-Sheriff lessons store does not own (`manage-lessons add` refuses it with `wrong_store`), so it is relayed rather than promoted locally. Content is unmodified below.
> ⚠ **Second emitter of an already-recorded mechanism.** Token-Sheriff lesson `2026-09-01-19-003` records this same broken `test -pl <mod> -am` shape emitted by `build-maven`'s `_maven_cmd_discover.py`; its upstream half was relayed as `refresh-identity-and-scope-defences-001.md`. THIS occurrence names a DIFFERENT emitter — `manage-architecture derive-verification` — so the fix at `build-maven` alone would not have prevented it.

# Candidate lesson: derive-verification emits a build command that cannot compile against a test-jar-classifier dependency

**Component**: `plan-marshall:manage-architecture` (`derive-verification`)
**Observed in**: plan `outbound-hostname-verification-quarkus` (PR #694, merged as `cd36dd24`), TASK-2 and TASK-4.

## What happened

`architecture derive-verification` stamped the verification command `test -pl <module> -am` onto TASK-2 and TASK-4.

Both target modules consume `token-sheriff-validation` with the `generators` **test-jar classifier**. That artifact is attached by `maven-jar-plugin` at the `package` phase. A reactor invoked with the `test` goal never reaches `package`, so `-am` builds the upstream module **without attaching the classified test-jar**, and the downstream `test-compile` dies on unresolvable generator classes.

The working shape — the one the deliverable itself documents — is the two-step:

1. `./mvnw install -DskipTests` (attaches the classified test-jar into the local repo)
2. `./mvnw test -pl <module>` (plain, no `-am`)

## Why this is worth an epic-level record

This is the recorded project gotcha `client-test-jar-build-gotcha` resurfacing at a **different layer**. The existing record covers the human/agent invoking maven by hand. This occurrence is the *deriver* emitting the broken shape mechanically: `derive-verification` has no knowledge of the classifier pairing between a module and its upstream test-jar, so it will re-emit `test -pl <module> -am` for every future plan that touches these modules. Fixing the plan-local task JSON does not prevent recurrence.

## Reproduction

Run `architecture derive-verification` for any module that declares a `<classifier>generators</classifier>` `test-jar` dependency on `token-sheriff-validation`, and inspect the emitted command.

## Out of scope for this plan

This plan implemented outbound hostname verification; the deriver defect was worked around locally by substituting the documented two-step. No fix was attempted.
