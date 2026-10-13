envelope_version=1
sender_type=plan
sender_id=lb-28-java-consumer-repos
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T23:23:13Z

component=plan-marshall:build-maven
category=bug
bundle=plan-marshall

# Maven reactor fixture declared a test-jar dependency whose classifier the producer never attached

## Source

Plan lb-28-java-consumer-repos, CodeRabbit inline review finding 7f0d1d on PR #1750 (`test/plan-marshall/build-maven/fixtures/reactor-test-artifact-project/typed-consumer/pom.xml:21`, severity Major). Caught and fixed in-run via TASK-9, commit 18c6495e5.

## What happened

The `reactor-test-artifact-project` fixture models test-artifact dependencies between reactor modules. Its `typed-consumer` module declares a dependency on `probe:producer` with `<type>test-jar</type>` and no classifier. Maven resolves a classifier-less `test-jar` dependency to classifier `tests`, but the `producer` POM attached only a test-jar with classifier `generators`. The fixture was therefore internally inconsistent: `package -pl typed-consumer -am` — a command the discovery logic under test actually emits for this fixture — could never resolve the test artifact.

The fix kept `typed-consumer` as the fixture's type-only test-jar case (its discovery pin is `probe:producer:test-jar`) and added a second `test-jar` execution to `producer/pom.xml` attaching the default `tests` classifier alongside `generators`.

## Why it slipped

The fixture is consumed only by static POM-parsing discovery tests. Those tests assert what discovery emits, not that the emitted command succeeds against the fixture, so a POM pair that Maven would reject passes every test. Nothing in the run executed Maven against the fixture.

## Corrective rule

When authoring a Maven fixture project used to test command derivation, check every inter-module dependency against what the target module actually attaches: a `<type>test-jar</type>` dependency without a `<classifier>` resolves to classifier `tests`, so the producer must attach a `tests`-classified test-jar (the default `maven-jar-plugin` `test-jar` goal) or the consumer must name the attached classifier explicitly. Fixtures whose purpose is to model resolvable builds should be resolvable; where executing Maven in the test suite is too costly, add a static consistency assertion (every consumer's (type, classifier) pair is matched by a producer attachment) to the fixture's tests.
