---
name: pm-dev-java-junit-core
description: JUnit 5 core testing patterns with AAA structure, test organization, and coverage standards
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
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
Call the `read` tool with `{ filePath: "standards/testing-junit-core.md" }` before continuing.
```

This provides foundational rules for:
- Test class requirements (at least one per production class, splitting by behaviour cluster above the 400-line budget)
- AAA pattern, with test data chosen by the universal-contract / literal-is-the-contract discriminator, and no phase comments
- Full JUnit 5 assertion API (`assertAll`, `assertInstanceOf`, `assertDoesNotThrow`)
- @Nested for grouping (3+ related tests)
- Corner case testing
- Coverage requirements (80% line/branch minimum)

### Step 2: Load Additional Standards (As Needed)

**Integration Testing** (load for IT work):
```text
Call the `read` tool with `{ filePath: "standards/testing-integration.md" }` before continuing.
```

Use when: Writing or reviewing integration tests (`*IT.java`). Covers naming, separation, and lifecycle.

**Async Testing** (load for async/concurrent code):
```text
Call the `read` tool with `{ filePath: "standards/testing-async-patterns.md" }` before continuing.
```

Use when: Testing asynchronous behavior. Covers Awaitility patterns (never Thread.sleep).

**Coverage Analysis** (load for coverage work):
```text
Call the `read` tool with `{ filePath: "standards/coverage-analysis-pattern.md" }` before continuing.
```

Use when: Analyzing test coverage or improving coverage metrics.

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
Call the `read` tool with `{ filePath: "templates/unit-test-class.java.tmpl" }` before continuing.
```

Replace `${PACKAGE}`, `${CLASS_UNDER_TEST}`, `${METHOD_1}`, and placeholder comments with actual values.

## Standards Reference

| Standard | Purpose |
|----------|---------|
| testing-junit-core.md | Test structure, AAA pattern, assertions, nesting |
| testing-integration.md | Integration test naming, separation, lifecycle |
| testing-async-patterns.md | Awaitility patterns (never Thread.sleep) |
| coverage-analysis-pattern.md | Coverage analysis and gap improvement |
