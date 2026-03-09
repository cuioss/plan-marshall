# JUnit Core Testing Standards

For general testing principles (AAA pattern, test organization, coverage requirements, test reliability), see `pm-dev-general:dev-testing`. This document covers JUnit 5-specific API and patterns.

## Fundamental Rules

* **Never introduce libraries** without asking the user first. This includes test utilities, assertion libraries, mocking frameworks, and any other dependency.
* Use randomized generators (e.g., `Generators.nonEmptyStrings().next()`, `UUID.randomUUID()`) for test data. See `pm-dev-java-cui:cui-testing` for CUI generator framework.
* **Never use `Thread.sleep`** for waiting in tests. Use Awaitility for all async waiting — it provides readable, timeout-safe polling. See `standards/testing-async-patterns.md` for patterns.
* **Never use reflection** to access private fields or methods in tests — this is always a bug, not a workaround. If code is hard to test, prefer these alternatives in order:
  1. **Refactor for testability** — extract logic into a testable collaborator or method
  2. **Relax visibility** — change `private` to package-private so the test (same package) can access it directly

## Test Class Requirements

* Test class naming: `{ClassName}Test.java` for production class `{ClassName}.java`
* Test classes in same package structure under `src/test/java`
* **Exceptions:** Enums without custom methods (only constants).

## JUnit 5 AAA Pattern

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

## JUnit 5 Assertion Features

Use the full JUnit 5 assertion API — do not reimplement what the framework provides:

```java
// Type checking — use assertInstanceOf, not instanceof + cast
assertInstanceOf(TokenValidationException.class, exception, "Should be validation exception");

// Grouped assertions — verify multiple properties without stopping at first failure
assertAll("User properties",
    () -> assertEquals(expectedName, user.getName(), "Name should match"),
    () -> assertNotNull(user.getEmail(), "Email should be present"),
    () -> assertTrue(user.isActive(), "User should be active")
);

// No-throw verification
assertDoesNotThrow(() -> service.process(validInput), "Valid input should not throw");

// Timeout assertions
assertTimeout(Duration.ofSeconds(2), () -> service.computeResult(), "Should complete within 2s");
```

All assertions include meaningful failure messages (20-60 characters). Messages describe what should have happened:
- `"Token should be valid"` (correct)
- `"Token is invalid"` (wrong — describes failure, not expectation)

### Exception Testing

Use `assertThrows` — move setup code outside the lambda, keep only the throwing statement inside:

```java
@Test
@DisplayName("Should throw exception on invalid input")
void shouldThrowExceptionOnInvalidInput() {
    var input = Generators.nonBlankStrings().next();
    service.validateInput(input);

    var exception = assertThrows(
        TokenValidationException.class,
        () -> service.processInput(input),
        "Invalid token should trigger validation exception"
    );

    assertNotNull(exception.getMessage(), "Exception should have message");
}
```

## Test Organization with @Nested

Use `@Nested` extensively to group related tests. This improves readability and structures test output. Use nesting when **3 or more tests** belong to the same logical group — do not nest single or two tests.

```java
@DisplayName("Token Validator Tests")
class TokenValidatorTest {

    @Nested
    @DisplayName("Valid Token Handling")
    class ValidTokenTests {
        @Test
        void shouldAcceptTokenWithValidSignature() { }

        @Test
        void shouldAcceptTokenWithFutureExpiry() { }

        @Test
        void shouldAcceptTokenWithAllRequiredClaims() { }
    }

    @Nested
    @DisplayName("Invalid Token Handling")
    class InvalidTokenTests {
        @Test
        void shouldRejectExpiredToken() { }

        @Test
        void shouldRejectTokenWithInvalidSignature() { }

        @Test
        void shouldRejectTokenWithMissingClaims() { }
    }

    @Nested
    @DisplayName("Corner Cases")
    class CornerCaseTests {
        @Test
        void shouldHandleNullToken() { }

        @Test
        void shouldHandleEmptyToken() { }

        @Test
        void shouldHandleMalformedBase64() { }
    }
}
```

## Test Types

* Unit test classes named `*Test.java`
* Integration test classes named `*IT.java` or `*ITCase.java`
* See `pm-dev-java:junit-integration` skill for Maven Failsafe/Surefire configuration

## Related Skills

- `pm-dev-general:dev-testing` - Language-agnostic testing principles (AAA, coverage, reliability)
- `pm-dev-java-cui:cui-testing` - CUI-specific test generators and library restrictions
- `pm-dev-java:junit-integration` - Maven Failsafe/Surefire configuration
