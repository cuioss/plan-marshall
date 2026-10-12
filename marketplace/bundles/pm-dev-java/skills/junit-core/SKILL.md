---
name: junit-core
description: JUnit 5 core testing patterns with AAA structure, test organization, and coverage standards, plus the Java test-code review rules a code review cites
user-invocable: false
mode: knowledge
---

# JUnit Core Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

JUnit 5 testing standards for general Java projects. This skill covers test structure, naming conventions, coverage requirements, and the AAA (Arrange-Act-Assert) pattern.

## Prerequisites

This skill applies to Java projects using JUnit 5:
- `org.junit.jupiter:junit-jupiter` (JUnit 5)

## Workflow

### Step 1: Load Core Testing Standards

**Important**: Load this standard for any testing work.

```text
Read: standards/testing-junit-core.md
```

This provides foundational rules for:
- Test class requirements (at least one per production class, splitting by behaviour cluster above the 400-line budget)
- AAA pattern, with test data chosen by the universal-contract / literal-is-the-contract discriminator, and no phase comments
- Full JUnit 5 assertion API (`assertAll`, `assertInstanceOf`, `assertDoesNotThrow`)
- @Nested for grouping (3+ related tests)
- Corner case testing
- Coverage requirements (80% line/branch minimum)
- Removing a redundant test (compare assertions before deleting, re-point references)

### Step 2: Load Additional Standards (As Needed)

**Integration Testing** (load for IT work):
```text
Read: standards/testing-integration.md
```

Use when: Writing or reviewing integration tests (`*IT.java`). Covers naming, separation, and lifecycle.

**Async Testing** (load for async/concurrent code):
```text
Read: standards/testing-async-patterns.md
```

Use when: Testing asynchronous behavior, or shortening a test that waits. Covers Awaitility patterns (never Thread.sleep), waits that are the subject of the test, deadlines for signal-based waits, observing a transient state deterministically, and failure-path tests that would otherwise pay production back-off.

**Coverage Analysis** (load for coverage work):
```text
Read: standards/coverage-analysis-pattern.md
```

Use when: Analyzing test coverage or improving coverage metrics, or comparing coverage before and after a change.

**Test Fork Policy** (load when the unit suite is slow or order-dependent):
```text
Read: standards/test-fork-policy.md
```

Use when: Deciding how many JVMs a unit suite starts — reusing one JVM for most classes, declaring isolation by JUnit tag, and guarding the split with a contract test.

## Key Rules Summary

### Test Class Requirements
```java
// CORRECT - At least one test class per production class
// TokenValidator.java → TokenValidatorTest.java
// UserService.java → UserServiceTest.java
```

### AAA Pattern — No Phase Comments
```java
@Test
@DisplayName("Should validate token with correct issuer")
void shouldValidateTokenWithCorrectIssuer() {
    var issuer = Generators.nonBlankStrings().next();
    var token = createTokenWithIssuer(issuer);

    var result = validator.validate(token);

    assertTrue(result.isValid(), "Token should be valid");
    assertEquals(issuer, result.getIssuer(), "Issuer should match");
}
```

### Grouped Assertions with assertAll
```java
@Test
@DisplayName("Should parse all token claims")
void shouldParseAllTokenClaims() {
    var token = createValidToken();

    var claims = parser.parse(token);

    assertAll("Token claims",
        () -> assertNotNull(claims.getSubject(), "Subject should be present"),
        () -> assertInstanceOf(Instant.class, claims.getExpiry(), "Expiry should be Instant"),
        () -> assertFalse(claims.getRoles().isEmpty(), "Roles should not be empty")
    );
}
```

### Coverage Requirements
- Minimum 80% line coverage
- Minimum 80% branch coverage
- Critical/hot paths: near 100% coverage
- All public APIs must be tested

## Related Skills

- `plan-marshall:persona-module-tester` - Language-agnostic testing principles
- `pm-dev-java:junit-integration` - Maven integration testing
- `pm-dev-java-cui:cui-testing` - CUI test generator framework
- `pm-dev-java:java-core` - Core Java patterns

## Templates

**Unit test class** — starting point for new test classes:
```text
Read: templates/unit-test-class.java.tmpl
```

Replace `${PACKAGE}`, `${CLASS_UNDER_TEST}`, `${METHOD_1}`, and placeholder comments with actual values.

## Standards Reference

| Standard | Purpose |
|----------|---------|
| testing-junit-core.md | Test structure, AAA pattern, assertions, nesting, removing a redundant test |
| testing-integration.md | Integration test naming, separation, lifecycle |
| testing-async-patterns.md | Awaitility patterns (never Thread.sleep), the wall-clock exception, deadlines for signal-based waits, transient-state observation, failure-path back-off |
| coverage-analysis-pattern.md | Coverage analysis, gap improvement, before/after comparison and what it cannot show |
| test-fork-policy.md | Surefire fork groups by JUnit tag, isolation criteria, the partition guard |

## Review Rules

The review rules of the java domain for test code — what a code review looks for in a changed JUnit test. The block follows the harvestable block contract — see [`review-rubric.md` § 10 "Harvestable review-rule blocks"](../../../plan-marshall/skills/phase-6-finalize/standards/review-rubric.md) for its rules, which are not restated here.

- A test of an exception path written as `try` / `catch` with no `fail()` after the call under test, so the test passes when no exception is thrown at all.
- A `@Test` method that calls the code under test and asserts nothing about its result, so it passes whatever the code returns.
- A test that depends on state another test left behind (a static field, a shared file, a declared method order), so it passes or fails by execution order instead of by the behaviour under test.
- A test that waits with `Thread.sleep` for an asynchronous result instead of an Awaitility condition, so it fails intermittently whenever the result arrives later than the fixed sleep.
