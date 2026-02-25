---
name: junit-core
description: JUnit 5 core testing patterns with AAA structure, test organization, and coverage standards
user-invocable: false
allowed-tools: Read, Grep, Glob
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

```
Read: standards/testing-junit-core.md
```

This provides foundational rules for:
- Test class requirements (1:1 mapping, splitting at 200+ lines)
- AAA pattern with generated test data (no literals, no phase comments)
- Full JUnit 5 assertion API (`assertAll`, `assertInstanceOf`, `assertDoesNotThrow`)
- @Nested for grouping (3+ related tests)
- Corner case testing
- Coverage requirements (80% line/branch minimum)

### Step 2: Load Additional Standards (As Needed)

**Integration Testing** (load for IT work):
```
Read: standards/testing-integration.md
```

Use when: Writing or reviewing integration tests (`*IT.java`). Covers naming, separation, and lifecycle.

**Async Testing** (load for async/concurrent code):
```
Read: standards/testing-async-patterns.md
```

Use when: Testing asynchronous behavior. Covers Awaitility patterns (never Thread.sleep).

**Coverage Analysis** (load for coverage work):
```
Read: standards/coverage-analysis-pattern.md
```

Use when: Analyzing test coverage or improving coverage metrics.

## Key Rules Summary

### Test Class Requirements
```java
// CORRECT - One test class per production class
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

- `pm-dev-java:junit-integration` - Maven integration testing
- `pm-dev-java-cui:cui-testing` - CUI test generator framework
- `pm-dev-java:java-core` - Core Java patterns

## Standards Reference

| Standard | Purpose |
|----------|---------|
| testing-junit-core.md | Test structure, AAA pattern, assertions, nesting |
| testing-integration.md | Integration test naming, separation, lifecycle |
| testing-async-patterns.md | Awaitility patterns (never Thread.sleep) |
| coverage-analysis-pattern.md | Coverage analysis and gap improvement |
