envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:53Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-15-plan-12-residual-fixes-002.md`, sender plan `plan-15-plan-12-residual-fixes`, created 2026-11-24T11:11:00Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: documentation claims about code behaviour were written without tracing every exit path, so review bots caught what the author and two in-house review rounds missed

**Source plan:** plan-15-plan-12-residual-fixes (PR #954, merged as 0545cffd)
**Signal:** signal_automated_review_count=1 (10 pr-comment findings resolved `fixed` in-run)
**Suggested category:** anti-pattern (documentation authoring)
**Suggested component:** documentation authoring for this repository (pm-documents:ref-documentation / pm-dev-java:javadoc are the candidate homes for the rule)

## What happened

The plan was documentation-only (16 files) and existed to correct earlier inaccurate documentation. The new sentences the author wrote were themselves inaccurate in the same way. Sourcery and CodeRabbit raised 10 findings on PR #954. All 10 were fixed in a follow-up commit (74e1f9b3). The plan's own functional-review and code-review rounds, which ran twice before the PR was opened, caught none of them.

The 10 findings fall into two shapes.

### Shape 1: an absolute behavioural claim that leaves out an exit path the code has (7 findings)

- `AccessTokenCache` class Javadoc (2 findings: sourcery 7e5346, coderabbit 6203a1). It said a cached token stays accepted "until expiry or eviction". The code also removes the entry and rejects the hit when the issuer's maximum token age is reached. DPoP proof validation and custom validation rules also run on a cache hit and can reject it.
- ADR-0010 (cf3ac4). The 5xx classification was described without the single DPoP-nonce retry that `TokenEndpointClient` performs first. A 5xx can be followed by a 4xx `invalid_grant`, which ends as credential-rejected.
- ADR-0017 (babffb). It said readiness follows the loader state. `JwksEndpointHealthCheck` actually caches the last response for 30 s (`sheriff.token.health.jwks.cache-seconds`).
- ADR-0031 (f6b391). It said the oversized scope set causes a 500. In fact only a missing-scope response does that: a request without a token gets 401, and a fully authorized request proceeds.
- quarkus-integration.adoc (fa2a1c). It said HTTP-only properties are rejected for a file-backed issuer. `HTTP_ONLY_PROPERTIES` checks only three; the other `jwks.http.*` settings, for example `refresh-interval-seconds`, are silently ignored.
- JFR-Instrumentation.adoc (c6e125). It said the runner overrides fix the `jmh.*` values. `BenchmarkConfiguration.builder()` reads and validates those properties before the overrides apply, so they must still be present and valid.

### Shape 2: a named mechanism or runnable procedure that was never checked against the file that implements it (3 findings)

- test-impl-mapping.adoc (84135c). It named `ownSkipProperty`. The client POM binds `<skipITs>${skipTests}</skipITs>`.
- devui-implementation.adoc (5b45ef). `docker compose up` also started the integration-tests service, whose image copies a native runner that the procedure never builds. Only `keycloak` should start.
- devui-implementation.adoc (010db4). The procedure ran Playwright in the same terminal as `quarkus:dev`, which stays in the foreground.

## Rule

**Do:** before writing a sentence of the form "X happens when / until / only if Y", open the method that implements it and list every return, throw, retry and cache on that path. Name each one, or soften the claim to "can". Before naming a property, element, service or command in a procedure, open the file that defines it (POM, compose file, `*PropertyKeys`) and copy the name from there. For a multi-step procedure, check that each step can run in the state the step before it leaves behind.

**Don't:** write the behaviour from memory or from the ADR or Javadoc being corrected. The source being corrected is exactly what was wrong.

**Review-side gap:** the in-house functional-review and code-review rounds passed text that CodeRabbit's path instructions then caught ("check a guard's predicate against the scenario the guard exists for", "verify that the mechanism exists in the file that would have to implement it"). For documentation footprints, the in-house review rubric could apply those same two checks per behavioural sentence.

## Not duplicated

The 4 declined comments and 3 code follow-ups are already in inbox message `plan-15-plan-12-residual-fixes-001`. This candidate covers only the 10 fixed findings and the authoring rule they share.
